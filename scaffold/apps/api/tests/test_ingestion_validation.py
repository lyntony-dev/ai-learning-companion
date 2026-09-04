from pathlib import Path

from app.ingestion.service import validate_materials


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "course_materials"


def test_validate_materials_returns_counts() -> None:
    report = validate_materials(FIXTURES_DIR)

    assert report.valid is True
    assert report.course_count == 1
    assert report.document_count == 1
    assert report.chunk_count == 1
    assert report.issues == []


def test_validate_materials_reports_missing_directory(tmp_path: Path) -> None:
    report = validate_materials(tmp_path / "missing")

    assert report.valid is False
    assert report.issues[0].level == "error"
