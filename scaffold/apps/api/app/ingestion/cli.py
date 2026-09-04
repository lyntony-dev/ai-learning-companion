import argparse
from pathlib import Path

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.sqlite import connect
from app.ingestion.service import import_materials, validate_materials
from app.repositories.course_repository import CourseRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Course materials ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate course material files")
    validate_parser.add_argument("--materials-dir", default="data/course_materials")

    import_parser = subparsers.add_parser("import", help="Import course material metadata into SQLite")
    import_parser.add_argument("--materials-dir", default="data/course_materials")
    import_parser.add_argument("--database-url", default="sqlite:///data/app.sqlite")
    import_parser.add_argument("--rebuild", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        report = validate_materials(Path(args.materials_dir))
        print(report.model_dump_json(indent=2))
        return 0 if report.valid else 1

    if args.command == "import":
        settings = Settings(DATABASE_URL=args.database_url)
        with connect(settings) as connection:
            apply_migrations(connection)
            report = import_materials(
                Path(args.materials_dir),
                CourseRepository(connection),
                rebuild=bool(args.rebuild),
            )
        print(report.model_dump_json(indent=2))
        return 0 if report.status == "ok" else 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
