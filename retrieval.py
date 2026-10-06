import re
from pathlib import PurePosixPath


# Chroma's default HNSW space is squared L2 distance; lower is closer.
RAG_MAX_SQUARED_L2_DISTANCE = 1.25

_GREETING_PATTERN = re.compile(
    r"^\s*(?:hi|hello|hey|hiya|howdy|good\s+(?:morning|afternoon|evening))"
    r"(?:\s+(?:there|linkzen))?[.!?,\s]*$",
    re.IGNORECASE,
)
_PERSONAL_MEMORY_PATTERN = re.compile(
    r"^\s*(?:what do you know about me|what do you remember about me|"
    r"tell me about myself|so you know about me|what(?: is|'s) my name|who am i|"
    r"what are my (?:career )?goals|my (?:career )?goals|my background|my name)"
    r"\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_PROFILE_PATTERN = re.compile(
    r"\b(?:what do you know about me|what do you remember about me|"
    r"tell me about myself|so you know about me|my background)\b",
    re.IGNORECASE,
)
_NAME_PATTERN = re.compile(r"\b(?:my name|who am i)\b", re.IGNORECASE)
_GOAL_PATTERN = re.compile(r"\b(?:career goals?|goals?|aspirations?|become)\b", re.IGNORECASE)
_FOLLOWUP_PATTERN = re.compile(
    r"^\s*(?:and\s+)?(?:why|how so|what about (?:it|that|those|them)|"
    r"what about|tell me more|explain that|elaborate|what do you mean)\b",
    re.IGNORECASE,
)


def is_simple_greeting(text):
    return bool(_GREETING_PATTERN.fullmatch(text or ""))


def is_personal_memory_question(text):
    return bool(_PERSONAL_MEMORY_PATTERN.search(text or ""))


def retrieval_query(question, history=None):
    """Use the current request; add only user-authored history for clear follow-ups."""
    question = (question or "").strip()
    if not question or is_simple_greeting(question) or not _FOLLOWUP_PATTERN.search(question):
        return question[:800]

    previous_user_messages = [
        message.get("content", "")[:600]
        for message in (history or [])[-8:]
        if isinstance(message, dict)
        and message.get("role") == "user"
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]
    return "\n".join([*previous_user_messages[-2:], question])[-2400:]


def memory_retrieval_query(question, history=None):
    query = retrieval_query(question, history)
    if _PROFILE_PATTERN.search(question or ""):
        return f"{query} personal profile name background career goals"
    if _NAME_PATTERN.search(question or ""):
        return f"{query} user name identity"
    if _GOAL_PATTERN.search(question or ""):
        return f"{query} my goal what I am working towards becoming"
    return query


def legacy_index_metadata(indexed_metadata, manifest, current_files):
    """Map old chunks without file metadata to current files or stale sources."""
    manifest_sources = {}
    for relative_path, entry in manifest.items():
        source = entry.get("source") if isinstance(entry, dict) else None
        if source:
            manifest_sources.setdefault(source, set()).add(relative_path)

    sources_by_file = {}
    stale_sources = set()
    for metadata in indexed_metadata:
        if not isinstance(metadata, dict) or metadata.get("file"):
            continue
        source = metadata.get("source")
        if not isinstance(source, str) or not source:
            continue
        if source.startswith("knowledge/"):
            candidates = {source[len("knowledge/"): ]}
        else:
            candidates = manifest_sources.get(source, set())
        existing = candidates & current_files
        if existing:
            for path in existing:
                sources_by_file.setdefault(path, set()).add(source)
        else:
            stale_sources.add(source)
    return sources_by_file, stale_sources


def _relative_source_path(metadata):
    path = metadata.get("file") or metadata.get("path")
    if not path:
        source = metadata.get("source")
        if isinstance(source, str) and source.startswith("knowledge/"):
            path = source[len("knowledge/"):]
    if not isinstance(path, str) or not path:
        return None
    relative = PurePosixPath(path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return relative.as_posix()


def _creator_paths(query, metadata_records):
    folded_query = " ".join(re.findall(r"[a-z0-9]+", query.casefold()))
    paths = set()
    for metadata in metadata_records:
        if not isinstance(metadata, dict):
            continue
        path = _relative_source_path(metadata)
        parts = PurePosixPath(path).parts if path else ()
        if len(parts) < 3 or parts[0].casefold() != "linkedin":
            continue
        creator = " ".join(re.findall(r"[a-z0-9]+", parts[1].casefold()))
        if creator and re.search(rf"\b{re.escape(creator)}\b", folded_query):
            paths.add(path)
    return sorted(paths)


def _result_rows(result):
    documents = (result.get("documents") or [[]])[0] or []
    metadata = (result.get("metadatas") or [[]])[0] or []
    distances = (result.get("distances") or [[]])[0] or []
    return zip(documents, metadata, distances)


def _source_record(document, metadata, distance, reason):
    path = _relative_source_path(metadata)
    if not path or not document:
        return None
    filename = PurePosixPath(path).name
    return {
        "path": path,
        "filename": filename,
        "excerpt": document.strip()[:360],
        "distance": round(float(distance), 3),
        "match_reason": reason,
    }


def retrieve_knowledge(collection, embedding_model, query, limit=3, enabled=True):
    """Return only relevant indexed excerpts and metadata for those excerpts."""
    if not enabled:
        return "", [], {"ran": False, "reason": "disabled", "candidate_count": 0}
    if is_simple_greeting(query):
        return "", [], {"ran": False, "reason": "greeting", "candidate_count": 0}
    if is_personal_memory_question(query):
        return "", [], {"ran": False, "reason": "personal-memory-question", "candidate_count": 0}

    collection_size = collection.count()
    if not collection_size:
        return "", [], {"ran": False, "reason": "empty-index", "candidate_count": 0}

    encoded_query = embedding_model.encode(query)
    if hasattr(encoded_query, "tolist"):
        encoded_query = encoded_query.tolist()
    metadata_records = collection.get(include=["metadatas"]).get("metadatas") or []
    creator_paths = _creator_paths(query, metadata_records)
    selected = {}

    if creator_paths:
        for path in creator_paths:
            result = collection.query(
                query_embeddings=[encoded_query],
                n_results=min(3, collection_size),
                where={"file": path},
                include=["documents", "metadatas", "distances"],
            )
            candidates = [
                (document, metadata or {}, distance)
                for document, metadata, distance in _result_rows(result)
                if document and _relative_source_path(metadata or {}) == path
            ]
            if candidates:
                document, metadata, distance = min(candidates, key=lambda item: item[2])
                selected[path] = (document, metadata, distance, "creator-path")
    else:
        result = collection.query(
            query_embeddings=[encoded_query],
            n_results=min(max(limit * 4, limit), collection_size),
            include=["documents", "metadatas", "distances"],
        )
        for document, metadata, distance in _result_rows(result):
            metadata = metadata or {}
            path = _relative_source_path(metadata)
            if not document or not path or not isinstance(distance, (int, float)):
                continue
            if distance > RAG_MAX_SQUARED_L2_DISTANCE:
                continue
            if path not in selected:
                selected[path] = (document, metadata, distance, "distance-threshold")

    excerpts = []
    sources = []
    ordered_selected = sorted(selected.values(), key=lambda item: item[2])[:limit]
    for document, metadata, distance, reason in ordered_selected:
        source = _source_record(document, metadata, distance, reason)
        if source:
            sources.append(source)
            excerpts.append(f"[{source['path']}]\n{source['excerpt']}")

    diagnostics = {
        "ran": True,
        "reason": "creator-path-match" if creator_paths else "vector-search",
        "candidate_count": len(selected),
        "sources": [
            {"path": source["path"], "distance": source["distance"], "match_reason": source["match_reason"]}
            for source in sources
        ],
    }
    return "\n\n".join(excerpts), sources, diagnostics