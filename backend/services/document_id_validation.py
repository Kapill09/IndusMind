from __future__ import annotations

INVALID_DOCUMENT_ID_PLACEHOLDERS = {"string", "null", "undefined"}


def sanitize_document_ids(document_ids: list[str] | str | None) -> list[str] | None:
    """Normalize client-supplied document IDs for safe metadata filtering.

    The API treats empty, whitespace-only, placeholder, and duplicate values as
    invalid and refuses to apply a document filter when no usable IDs remain.
    """

    if document_ids is None:
        return None

    if isinstance(document_ids, str):
        raw_ids: list[str] = [document_ids]
    elif isinstance(document_ids, list):
        raw_ids = document_ids
    else:
        return None

    cleaned_ids: list[str] = []
    seen_ids: set[str] = set()

    for raw_id in raw_ids:
        if not isinstance(raw_id, str):
            continue

        candidate = raw_id.strip()
        if not candidate:
            continue

        normalized_candidate = candidate.casefold()
        if normalized_candidate in INVALID_DOCUMENT_ID_PLACEHOLDERS:
            continue

        if normalized_candidate in seen_ids:
            continue

        cleaned_ids.append(candidate)
        seen_ids.add(normalized_candidate)

    return cleaned_ids or None
