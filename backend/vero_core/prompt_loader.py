"""Load and render versioned prompt templates from `vero_core/prompts/`.

Template file format (``{id}_{version}.md``): front matter between ``---``
lines (``key: value``), then a ``SYSTEM:`` section and a ``USER:`` section.
Variables appear as ``{{ name }}``. Rendering is deliberately dumb — no
conditionals or loops — so a template is exactly what gets sent. Anything a
loop would build (like the per-condition blocks) is pre-rendered in Python
and passed in as one variable.
"""

import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

_VARIABLE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    description: str
    system: str
    user: str


def load_prompt(prompt_id: str, version: str) -> PromptTemplate:
    filename = f"{prompt_id}_{version}.md"
    raw = (resources.files("vero_core") / "prompts" / filename).read_text(encoding="utf-8")

    parts = raw.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"{filename}: missing front matter")
    front_matter: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        key, _, value = line.partition(":")
        front_matter[key.strip()] = value.strip()

    body = parts[2]
    system_marker, user_marker = "SYSTEM:", "USER:"
    system_index = body.index(system_marker)
    user_index = body.index(user_marker)
    system = body[system_index + len(system_marker) : user_index].strip()
    user = body[user_index + len(user_marker) :].strip()

    if front_matter.get("id") != prompt_id or front_matter.get("version") != version:
        raise ValueError(f"{filename}: front matter does not match filename")
    return PromptTemplate(
        id=prompt_id,
        version=version,
        description=front_matter.get("description", ""),
        system=system,
        user=user,
    )


def render(template_text: str, variables: dict[str, Any]) -> str:
    """Substitute ``{{ name }}`` placeholders; unknown or unused names fail loudly."""

    used: set[str] = set()

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise KeyError(f"Prompt variable {{{{ {name} }}}} has no value")
        used.add(name)
        return str(variables[name])

    rendered = _VARIABLE_RE.sub(substitute, template_text)
    unused = set(variables) - used
    if unused:
        raise KeyError(f"Variables not used by the template: {sorted(unused)}")
    return rendered
