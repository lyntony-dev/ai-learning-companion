import hashlib

from app.ingestion.models import CourseChunkDraft, MaterialDocument

MAX_PREVIEW_CHARS = 500


def stable_chunk_id(document: MaterialDocument, ordinal: int) -> str:
    raw = f"{document.course_id}:{document.source_path}:{ordinal}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"chunk_{digest}"


def chunk_document(document: MaterialDocument) -> list[CourseChunkDraft]:
    """Create one lightweight chunk per document for PR 3.

    Real token-aware chunking is deferred to later RAG implementation. PR 3 keeps
    deterministic IDs and metadata shape stable for downstream work.
    """

    text_preview = document.text[:MAX_PREVIEW_CHARS]
    return [
        CourseChunkDraft(
            chunk_id=stable_chunk_id(document, 0),
            course_id=document.course_id,
            course_name=document.course_name,
            section=document.section,
            content_type=document.content_type,
            text_preview=text_preview,
            source_path=document.source_path,
            slide_no=document.slide_no,
            metadata={
                "course_version": document.version,
                "source_length": len(document.text),
                "chunk_ordinal": 0,
            },
        )
    ]
