"""Parsers for the CMS reference files.

File layouts were verified against the FY2027 downloads on 2026-10-04 and are
documented in `data/SOURCES.md`. These are pure functions so they can be
tested on small fixture files.
"""

import csv
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# Matches ICD-10-CM code references inside note text, e.g. "E11.22",
# "N18.1-N18.6" (two matches), "E10.-" (matches the "E10" prefix), "B95".
CODE_REF_RE = re.compile(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?")

# Note types copied down from ancestor categories to every code below them
# (ICD-10-CM tabular convention; see ADR 0004). Inclusion terms stay at the
# level they were written on — they describe that code, not its children.
INHERITED_NOTE_KEYS = ("excludes1", "excludes2", "code_first", "use_additional")

XML_NOTE_ELEMENTS = {
    "inclusionTerm": "inclusion_terms",
    "excludes1": "excludes1",
    "excludes2": "excludes2",
    "codeFirst": "code_first",
    "useAdditionalCode": "use_additional",
}


@dataclass(frozen=True)
class OrderFileRow:
    code: str  # dotless, e.g. "E1122"
    is_billable: bool
    short_desc: str
    long_desc: str


def parse_order_file(path: Path) -> list[OrderFileRow]:
    """Parse the fixed-width CMS order file.

    1-indexed columns: 1-5 order number, 7-13 code (left-justified), 15
    validity flag ("0" header / "1" billable), 17-76 short description,
    78+ long description.
    """
    rows: list[OrderFileRow] = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            code = line[6:13].strip()
            flag = line[14]
            if not code or flag not in "01":
                raise ValueError(f"Unexpected order file layout at line {line_number}")
            rows.append(
                OrderFileRow(
                    code=code,
                    is_billable=flag == "1",
                    short_desc=line[16:76].strip(),
                    long_desc=line[77:].strip(),
                )
            )
    return rows


def extract_code_refs(texts: list[str]) -> list[str]:
    """Pull referenced code patterns out of note text, deduplicated in order.

    "code to identify stage of chronic kidney disease (N18.1-N18.6)" yields
    ["N18.1", "N18.6"]; a category reference like "E10.-" yields "E10".
    """
    seen: dict[str, None] = {}
    for text in texts:
        for match in CODE_REF_RE.findall(text):
            seen.setdefault(match)
    return list(seen)


def _merge_notes(parent: dict[str, list[str]], own: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for key in INHERITED_NOTE_KEYS:
        combined = parent.get(key, []) + own.get(key, [])
        if combined:
            merged[key] = list(dict.fromkeys(combined))
    if own.get("inclusion_terms"):
        merged["inclusion_terms"] = own["inclusion_terms"]
    return merged


def _own_notes(diag: ET.Element) -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {}
    for element_name, key in XML_NOTE_ELEMENTS.items():
        texts = [
            note.text.strip()
            for container in diag.findall(element_name)
            for note in container.findall("note")
            if note.text and note.text.strip()
        ]
        if texts:
            notes[key] = texts
    return notes


def parse_tabular_xml(path: Path) -> dict[str, dict[str, list[str]]]:
    """Parse the tabular XML into {dotless code: notes dict}.

    Notes include everything inherited from ancestor <diag> categories
    (excludes1/2, code first, use additional code), plus this code's own
    inclusion terms, plus `<type>_codes` lists of referenced code patterns.
    Chapter- and section-level notes are intentionally not inherited
    (ADR 0004).
    """
    tree = ET.parse(path)
    results: dict[str, dict[str, list[str]]] = {}

    def walk(diag: ET.Element, parent_notes: dict[str, list[str]]) -> None:
        name = diag.findtext("name")
        if not name:
            return
        effective = _merge_notes(parent_notes, _own_notes(diag))
        stored = dict(effective)
        for key in INHERITED_NOTE_KEYS:
            if stored.get(key):
                refs = extract_code_refs(stored[key])
                if refs:
                    stored[f"{key}_codes"] = refs
        results[name.replace(".", "")] = stored
        for child in diag.findall("diag"):
            walk(child, effective)

    for diag in tree.getroot().iter("diag"):
        # iter() yields nested diags too; only start walks from top-level ones
        # (those whose parent is a section), which we detect by checking the
        # code is not already collected.
        name = diag.findtext("name")
        if name and name.replace(".", "") not in results:
            walk(diag, {})

    return results


def parse_hcc_labels(path: Path) -> dict[int, str]:
    """Parse the SAS LABEL macro (e.g. V28115L3.TXT) into {number: label}."""
    labels: dict[int, str] = {}
    pattern = re.compile(r'HCC(\d+)\s*=\s*"(.+?)\s*"')
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            labels[int(match.group(1))] = match.group(2)
    return labels


def parse_hcc_mappings_csv(path: Path, version: str) -> list[tuple[str, int]]:
    """Parse the CMS mappings CSV into [(dotless code, hcc number), ...].

    The file lists several models side by side; `version` picks the column
    (e.g. "V28"). A code may appear on multiple rows, so pairs are
    deduplicated. Verified layout: data starts after the header row whose
    first cell begins with "Diagnosis".
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    header_index, column_index = None, None
    for i, row in enumerate(rows):
        if row and row[0].strip().startswith("Diagnosis"):
            header_index = i
            for j, header in enumerate(row):
                normalized = header.replace("\n", " ")
                if (
                    version in normalized
                    and "CMS-HCC" in normalized
                    and "Payment Year" not in normalized
                ):
                    column_index = j
                    break
            break
    if header_index is None or column_index is None:
        raise ValueError(f"Could not find a CMS-HCC {version} column in {path.name}")

    pairs: dict[tuple[str, int], None] = {}
    for row in rows[header_index + 1 :]:
        if len(row) <= column_index or not row[0].strip():
            continue
        value = row[column_index].strip()
        if value.isdigit():
            pairs.setdefault((row[0].strip(), int(value)))
    return list(pairs)


def compute_parent_codes(codes: set[str]) -> dict[str, str]:
    """For each dotless code, the longest shorter prefix that is also a code."""
    parents: dict[str, str] = {}
    for code in codes:
        parent = ""
        for length in range(len(code) - 1, 2, -1):
            if code[:length] in codes:
                parent = code[:length]
                break
        parents[code] = parent
    return parents
