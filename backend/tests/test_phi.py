from apps.notes.phi import find_phi


class TestPhiTripwireMatches:
    def test_ssn(self) -> None:
        assert "ssn" in find_phi("SSN 123-45-6789 on file")

    def test_phone_formats(self) -> None:
        assert "phone" in find_phi("call (555) 867-5309")
        assert "phone" in find_phi("cell 555-867-5309")
        assert "phone" in find_phi("fax 555.867.5309")

    def test_email(self) -> None:
        assert "email" in find_phi("contact jane.doe+notes@example.org")

    def test_mrn_labels(self) -> None:
        assert "mrn" in find_phi("MRN: 00123456")
        assert "mrn" in find_phi("Medical Record # A99")
        assert "mrn" in find_phi("chart number 123")

    def test_dob(self) -> None:
        assert "dob" in find_phi("DOB: 01/02/1950")
        assert "dob" in find_phi("date of birth 1950-01-02")


class TestPhiTripwireNonMatches:
    def test_clinical_numbers_pass(self) -> None:
        note = (
            "BP 128/76. A1c 7.4%. eGFR 52. Metformin 500 mg BID.\n"
            "Follow up 10/03/2026. Glucose readings 110-160. Phone triage done."
        )
        assert find_phi(note) == []

    def test_sample_notes_pass(self) -> None:
        from pathlib import Path

        samples = Path(__file__).resolve().parents[2] / "data" / "samples"
        for sample in samples.glob("*.txt"):
            assert find_phi(sample.read_text()) == [], sample.name
