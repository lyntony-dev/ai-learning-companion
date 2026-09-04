import json
from pathlib import Path

from app.ingestion.models import CourseManifest, MaterialDocument, ValidationIssue

SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}


class MaterialParseError(ValueError):
    """Raised when a course material file cannot be parsed."""


def load_manifest(course_dir: Path) -> CourseManifest:
    manifest_path = course_dir / "course.json"
    if not manifest_path.exists():
        raise MaterialParseError(f"Missing course manifest: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return CourseManifest.model_validate(data)


def discover_material_files(course_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in course_dir.rglob("*")
        if path.is_file() and path.name != "course.json" and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def infer_content_type(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "slides" in parts:
        return "slide"
    if "notes" in parts:
        return "note"
    return path.suffix.lower().removeprefix(".") or "text"


def infer_slide_no(path: Path) -> int | None:
    stem = path.stem.lower()
    digits = "".join(char for char in stem if char.isdigit())
    if not digits:
        return None
    return int(digits)


def infer_section(path: Path) -> str:
    if path.parent.name in {"slides", "notes"}:
        return path.stem.replace("_", " ").replace("-", " ").strip() or path.stem
    return path.parent.name.replace("_", " ").replace("-", " ").strip() or path.stem


def parse_document(course_dir: Path, file_path: Path, manifest: CourseManifest) -> MaterialDocument:
    text = file_path.read_text(encoding="utf-8").strip()
    relative_path = file_path.relative_to(course_dir.parent).as_posix()
    return MaterialDocument(
        course_id=manifest.course_id,
        course_name=manifest.course_name,
        version=manifest.version,
        tags=manifest.tags,
        source_path=relative_path,
        section=infer_section(file_path),
        content_type=infer_content_type(file_path),
        text=text,
        slide_no=infer_slide_no(file_path),
    )


def validate_course_dir(course_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    manifest_path = course_dir / "course.json"
    if not manifest_path.exists():
        issues.append(
            ValidationIssue(
                level="error",
                path=str(manifest_path),
                message="course.json is required for each course directory.",
            )
        )
        return issues

    try:
        manifest = load_manifest(course_dir)
    except Exception as exc:
        issues.append(ValidationIssue(level="error", path=str(manifest_path), message=str(exc)))
        return issues

    material_files = discover_material_files(course_dir)
    if not material_files:
        issues.append(
            ValidationIssue(
                level="warning",
                path=str(course_dir),
                message=f"No supported material files found for course {manifest.course_id}.",
            )
        )

    for file_path in material_files:
        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError as exc:
            issues.append(ValidationIssue(level="error", path=str(file_path), message=str(exc)))
            continue

        if not text:
            issues.append(
                ValidationIssue(level="warning", path=str(file_path), message="Material file is empty.")
            )

    return issues
