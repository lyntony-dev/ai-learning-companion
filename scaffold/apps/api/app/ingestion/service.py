from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.models import (
    CourseManifest,
    ImportReport,
    MaterialDocument,
    ValidationIssue,
    ValidationReport,
)
from app.ingestion.parsers import discover_material_files, load_manifest, parse_document, validate_course_dir
from app.repositories.course_repository import CourseRepository


def discover_course_dirs(materials_dir: Path) -> list[Path]:
    if not materials_dir.exists():
        return []
    return sorted(path for path in materials_dir.iterdir() if path.is_dir())


def load_documents(materials_dir: Path) -> tuple[list[CourseManifest], list[MaterialDocument]]:
    manifests: list[CourseManifest] = []
    documents: list[MaterialDocument] = []

    for course_dir in discover_course_dirs(materials_dir):
        manifest = load_manifest(course_dir)
        manifests.append(manifest)
        for file_path in discover_material_files(course_dir):
            documents.append(parse_document(course_dir, file_path, manifest))

    return manifests, documents


def validate_materials(materials_dir: Path) -> ValidationReport:
    issues = []
    chunk_count = 0
    document_count = 0
    course_dirs = discover_course_dirs(materials_dir)

    if not materials_dir.exists():
        return ValidationReport(
            valid=False,
            course_count=0,
            document_count=0,
            chunk_count=0,
            issues=[
                ValidationIssue(
                    level="error",
                    path=str(materials_dir),
                    message="Course materials directory does not exist.",
                )
            ],
        )

    for course_dir in course_dirs:
        issues.extend(validate_course_dir(course_dir))
        try:
            manifest = load_manifest(course_dir)
        except Exception:
            continue
        for file_path in discover_material_files(course_dir):
            document_count += 1
            document = parse_document(course_dir, file_path, manifest)
            chunk_count += len(chunk_document(document))

    valid = not any(issue.level == "error" for issue in issues)
    return ValidationReport(
        valid=valid,
        course_count=len(course_dirs),
        document_count=document_count,
        chunk_count=chunk_count,
        issues=issues,
    )


def import_materials(materials_dir: Path, repository: CourseRepository, rebuild: bool = False) -> ImportReport:
    validation_report = validate_materials(materials_dir)
    if not validation_report.valid:
        return ImportReport(
            status="failed",
            rebuild=rebuild,
            courses_imported=0,
            chunks_imported=0,
            issues=validation_report.issues,
        )

    manifests, documents = load_documents(materials_dir)
    if rebuild:
        repository.clear_all()

    chunks_imported = 0
    for manifest in manifests:
        repository.upsert_course(manifest)
    for document in documents:
        for chunk in chunk_document(document):
            repository.upsert_chunk(chunk)
            chunks_imported += 1

    return ImportReport(
        status="ok",
        rebuild=rebuild,
        courses_imported=len(manifests),
        chunks_imported=chunks_imported,
        issues=validation_report.issues,
    )
