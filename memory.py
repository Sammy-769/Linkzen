import json
import math
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from usage import record_response_usage


MEMORY_FILE = Path("memory.json")

CATEGORIES = {
    "preference",
    "goal",
    "learning",
    "project",
    "work",
    "technical",
    "communication",
    "other",
}

DEFAULT_IMPORTANCE = {
    "preference": 0.80,
    "goal": 0.90,
    "learning": 0.78,
    "project": 0.75,
    "work": 0.80,
    "technical": 0.72,
    "communication": 0.85,
    "other": 0.60,
}

# Similarity is the admission gate. Importance and lifecycle only affect the
# ordering of memories that have already passed this relevance check.
SEMANTIC_THRESHOLD = 0.36
CANDIDATE_THRESHOLD = 0.42
KEYWORD_FALLBACK_THRESHOLD = 0.30

# This remains a cheap local first pass. It only determines whether the small
# memory-extraction call is worthwhile; DeepSeek remains the final filter.
PERSONAL_CONTEXT_PATTERN = re.compile(
    r"\b(?:i|i'm|i am|i've|i have|my|me|we|we're|we are|our)\b",
    re.IGNORECASE,
)

DURABLE_TOPIC_PATTERN = re.compile(
    r"\b(?:"
    r"learn(?:ing|ed)?|study(?:ing|ied)?|training|upskill(?:ing)?|"
    r"prefer(?:ence)?|like|love|dislike|avoid|rather|"
    r"goal|career|become|focus(?:ing)?|aim|plan(?:ning)?|hope|aspir(?:e|ing)|decided|"
    r"project|projects|building|developing|working\s+on|assistant|"
    r"ubuntu|windows|macos|linux|tool|tools|environment|editor|vscode|"
    r"aws|terraform|docker|kubernetes|cloud|linkedin|professional\s+profile|"
    r"online\s+presence|personal\s+brand|audience|following|"
    r"work\s+as|job|role|background|experience|based\s+in|live\s+in|"
    r"british\s+english|american\s+english|language|spelling"
    r")\b",
    re.IGNORECASE,
)

QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:what|why|how|when|where|who|which|can|could|should|would|"
    r"do|does|did|is|are|will|may|any)\b",
    re.IGNORECASE,
)

DECLARATIVE_PERSONAL_PATTERN = re.compile(
    r"\b(?:"
    r"i(?:'m| am)?\s+(?:currently\s+)?(?:learning|studying|using|building|working\s+on)|"
    r"i(?:'ve| have)\s+(?:recently\s+)?(?:started\s+)?(?:learning|studying)|"
    r"i(?:'ve| have)\s+decided\s+to\s+(?:become|use|focus|learn|study)|"
    r"i\s+(?:really\s+)?(?:prefer|like|love|dislike|avoid)|"
    r"i\s+(?:want\s+to|plan\s+to|hope\s+to|aim\s+to|decided\s+to)\s+"
    r"(?:become|use|focus|learn|study)|"
    r"my\s+(?:goal|plan|preference|career|role|project)\s+(?:is|are)|"
    r"for\s+my\s+(?:project|projects|work)\b|"
    r"(?:british|american)\s+english\b.*?\bi\s+(?:want|prefer|use)"
    r")",
    re.IGNORECASE,
)

EXPLICIT_MEMORY_PATTERN = re.compile(
    r"^\s*(?:(?:please|just|also)\s+)*(?:"
    r"remember(?:\s+(?:this|that))?|"
    r"keep\s+(?:this|that|it)?\s*in\s+mind"
    r")\s*(?:(?::|,|-)\s*|that\s+)?(?P<memory>.+?)\s*$",
    re.IGNORECASE,
)

TRAILING_EXPLICIT_MEMORY_PATTERN = re.compile(
    r"^\s*(?P<memory>.+?)\s*[.!?]?\s+(?:please\s+)?"
    r"remember\s+(?:this|that)\s*[.!?]*\s*$",
    re.IGNORECASE,
)

FORGET_PATTERN = re.compile(
    r"^\s*(?:(?:please|just)\s+)?forget(?:\s+(?P<target>.+?))?\s*[.!?]*\s*$",
    re.IGNORECASE,
)

SENSITIVE_PATTERN = re.compile(
    r"\b(?:api[ _-]?key|password|passcode|secret|access[ _-]?token|"
    r"auth(?:entication)?[ _-]?token|credential|private[ _-]?key)\b",
    re.IGNORECASE,
)

STOP_WORDS = {
    "a", "an", "and", "am", "are", "as", "at", "be", "because", "for",
    "about", "do", "i", "in", "is", "it", "me", "my", "of", "on", "the",
    "know", "to", "user", "want", "what", "with", "would", "you",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _safe_importance(value, category):
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return DEFAULT_IMPORTANCE[category]


def _infer_category(text):
    lowered = text.casefold()
    if re.search(r"\b(?:british|american) english\b|\b(?:explanation|answer|response)s?\b", lowered):
        return "communication"
    if re.search(r"\b(?:prefer(?:ence)?|likes?|loves?|dislikes?|avoid)\b", lowered):
        return "preference"
    if re.search(r"\b(?:goal|want(?:s)? to|become|career|aim(?:s)? to|hope(?:s)? to|focus on|grow)\b", lowered):
        return "goal"
    if re.search(r"\b(?:learn(?:ing|ed)?|study(?:ing|ied)?|training|terraform|aws)\b", lowered):
        return "learning"
    if re.search(r"\b(?:project|building|developing|assistant)\b", lowered):
        return "project"
    if re.search(r"\b(?:work as|job|role|employer|career background)\b", lowered):
        return "work"
    if re.search(r"\b(?:ubuntu|windows|macos|linux|docker|kubernetes|tool|vscode)\b", lowered):
        return "technical"
    return "other"


def _infer_memory_type(category, text):
    if category == "project" and re.search(r"\b(?:currently|building|working on)\b", text, re.IGNORECASE):
        return "short-term"
    if re.search(r"\b(?:name|birthday)\b", text, re.IGNORECASE):
        return "long-term"
    if category == "other":
        return "short-term"
    return "long-term"


def _valid_embedding(value):
    return (
        isinstance(value, list)
        and len(value) > 1
        and all(isinstance(number, (int, float)) for number in value)
    )


def _normalise_record(item):
    """Convert old strings and incomplete dictionaries to a safe record."""
    changed = False
    if isinstance(item, str):
        raw = {"memory": item}
        changed = True
    elif isinstance(item, dict):
        raw = item
    else:
        return None, True

    text = raw.get("memory", "")
    if not isinstance(text, str) or not text.strip():
        return None, True
    text = text.strip()[:300]

    category = raw.get("category")
    if category not in CATEGORIES:
        category = _infer_category(text)
        changed = True

    memory_type = raw.get("memory_type")
    if memory_type not in {"long-term", "short-term"}:
        memory_type = _infer_memory_type(category, text)
        changed = True

    timestamp = _now()
    record = {
        "id": raw.get("id") if isinstance(raw.get("id"), str) else str(uuid.uuid4()),
        "memory": text,
        "category": category,
        "importance": _safe_importance(raw.get("importance"), category),
        "memory_type": memory_type,
        "created_at": raw.get("created_at") if isinstance(raw.get("created_at"), str) else timestamp,
        "updated_at": raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else timestamp,
        "last_used": raw.get("last_used") if isinstance(raw.get("last_used"), str) else None,
    }
    if _valid_embedding(raw.get("embedding")):
        record["embedding"] = [float(value) for value in raw["embedding"]]
    elif "embedding" in raw:
        changed = True

    if record != raw:
        changed = True
    return record, changed


def load_memory():
    """Load records and transparently migrate the prior list-of-strings file."""
    if not MEMORY_FILE.exists():
        return []

    try:
        raw_memory = json.loads(MEMORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(raw_memory, list):
        return []

    memory = []
    changed = False
    for item in raw_memory:
        record, item_changed = _normalise_record(item)
        changed = changed or item_changed
        if record:
            memory.append(record)

    if changed:
        save_memory(memory)
    return memory


def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False))


def is_potential_memory(text):
    """Use cheap local rules before making a memory-extraction API call."""
    if not text or not text.strip() or SENSITIVE_PATTERN.search(text):
        return False
    if not PERSONAL_CONTEXT_PATTERN.search(text):
        return False
    if not DURABLE_TOPIC_PATTERN.search(text):
        return False

    # Questions can include durable information. Reject only question-led
    # messages that contain no declarative personal statement after the query.
    if QUESTION_START_PATTERN.search(text):
        question_parts = re.split(r"[?!.]", text, maxsplit=1)
        statement_after_question = question_parts[1] if len(question_parts) == 2 else ""
        return bool(
            statement_after_question
            and DECLARATIVE_PERSONAL_PATTERN.search(statement_after_question)
        )
    return True


def get_explicit_memory(text):
    """Return the fact paired with a direct remember/keep-in-mind request."""
    if not text or SENSITIVE_PATTERN.search(text):
        return None
    match = EXPLICIT_MEMORY_PATTERN.match(text)
    if match:
        memory = match.group("memory").strip()
    else:
        match = TRAILING_EXPLICIT_MEMORY_PATTERN.match(text)
        if not match:
            return None
        memory = match.group("memory").strip().rstrip(".!?")
    return memory[:300] if memory else None


def get_forget_request(text):
    """Return a forget target, using an empty target for contextual references."""
    if not text:
        return None
    match = FORGET_PATTERN.match(text)
    if not match:
        return None
    target = (match.group("target") or "").strip().rstrip(".!?")
    if target.casefold() in {"it", "this", "that", "that fact", "what i said"}:
        return ""
    return target


def extract_memories(text, client):
    """Return one structured durable memory, or [] when DeepSeek returns NONE."""
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract one durable user fact only when it is likely to "
                    "remain useful across conversations: stable preferences, "
                    "ongoing learning or career goals, or lasting project facts. "
                    "Do not save one-off tasks, temporary plans/events, passing "
                    "opinions, details from assistant-generated text, or "
                    "uncertain inferences. Return NONE when nothing durable is "
                    "present. Return JSON only: "
                    '{"memory":"...","category":"preference|goal|learning|project|work|technical|communication|other",'
                    '"importance":0.0,"memory_type":"long-term|short-term"}, or NONE. '
                    "Ignore temporary talk and credentials."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=60,
    )

    record_response_usage(response)

    content = response.choices[0].message.content
    if not content:
        return []
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if content.upper().rstrip(".") == "NONE":
        return []

    try:
        extracted = json.loads(content)
    except json.JSONDecodeError:
        # Preserve compatibility with the prior plain-text extractor response.
        # Partial JSON is rejected; a concise text line is safely categorized
        # locally instead.
        if content.startswith("{") or content.startswith("["):
            return []
        if SENSITIVE_PATTERN.search(content):
            return []
        record, _ = _normalise_record({"memory": content})
        return [record] if record else []

    if not isinstance(extracted, dict):
        return []
    memory_text = extracted.get("memory")
    if not isinstance(memory_text, str) or not memory_text.strip():
        return []
    if SENSITIVE_PATTERN.search(memory_text):
        return []

    record, _ = _normalise_record(extracted)
    return [record] if record else []


def _tokens(text):
    aliases = {
        "uses": "use", "prefers": "prefer", "likes": "like",
        "dislikes": "dislike", "learns": "learn", "studies": "study",
        "works": "work", "goals": "goal",
    }
    normalized_text = re.sub(r"\blinked\s+in\b", "linkedin", text.casefold())
    tokens = set()
    for token in re.findall(r"[a-z0-9+#.-]+", normalized_text):
        token = token.rstrip(".")
        if len(token) > 1 and token not in STOP_WORDS:
            tokens.add(aliases.get(token, token))
    return tokens


def _embed(text, embedding_model):
    if embedding_model is None:
        return None
    values = embedding_model.encode(text)
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [float(value) for value in values]


def _cosine_similarity(first, second):
    if not _valid_embedding(first) or not _valid_embedding(second) or len(first) != len(second):
        return 0.0
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return 0.0
    return sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)


def _keyword_score(question, memory_text):
    question_tokens = _tokens(question)
    memory_tokens = _tokens(memory_text)
    if not question_tokens or not memory_tokens:
        return 0.0
    return len(question_tokens & memory_tokens) / len(question_tokens)


def _lifecycle_bonus(record):
    if record["memory_type"] == "long-term":
        return 0.02
    reference = record.get("last_used") or record.get("updated_at")
    try:
        age_days = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(reference)).days)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, 0.05 * (1 - age_days / 60))


def _ensure_embedding(record, embedding_model):
    if _valid_embedding(record.get("embedding")):
        return False
    embedding = _embed(record["memory"], embedding_model)
    if embedding is None:
        return False
    record["embedding"] = embedding
    return True


def _rank_memories(question, memory, embedding_model, limit, threshold):
    question_embedding = _embed(question, embedding_model)
    changed = False
    ranked = []
    for record in memory:
        changed = _ensure_embedding(record, embedding_model) or changed
        semantic_score = _cosine_similarity(question_embedding, record.get("embedding"))
        keyword_score = _keyword_score(question, record["memory"])
        if semantic_score < threshold and keyword_score < KEYWORD_FALLBACK_THRESHOLD:
            continue
        combined_score = (
            0.75 * semantic_score
            + 0.20 * keyword_score
            + 0.05 * record["importance"]
            + _lifecycle_bonus(record)
        )
        ranked.append({
            "record": record,
            "semantic_score": semantic_score,
            "keyword_score": keyword_score,
            "score": combined_score,
        })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit], changed


def get_relevant_memory_text(
    question,
    limit=3,
    embedding_model=None,
    return_ids=False,
    return_details=False,
):
    """Return relevant Memory context and optional per-record retrieval metadata."""
    memory = load_memory()
    if not memory:
        result = "No relevant saved memories."
        if return_details:
            return "", []
        return (result, []) if return_ids else result

    name_question = re.search(
        r"\b(?:what(?:\s+is|'s)\s+my\s+name|who\s+am\s+i)\b",
        question,
        re.IGNORECASE,
    )
    ranked_records = (
        [record for record in memory if _memory_slot(record) == "name"]
        if name_question
        else memory
    )
    ranked, changed = _rank_memories(
        question, ranked_records, embedding_model, limit, SEMANTIC_THRESHOLD
    )
    if changed:
        save_memory(memory)
    if not ranked:
        result = "No relevant saved memories."
        if return_details:
            return "", []
        return (result, []) if return_ids else result

    result = "\n".join(f"- {item['record']['memory']}" for item in ranked)
    memory_ids = [item["record"]["id"] for item in ranked]
    details = [
        {
            "id": item["record"]["id"],
            "memory": item["record"]["memory"],
            "category": item["record"]["category"],
            "similarity": round(item["semantic_score"], 3),
            "keyword_score": round(item["keyword_score"], 3),
        }
        for item in ranked
    ]
    if return_details:
        return result, details
    return (result, memory_ids) if return_ids else result


def mark_memories_used(memory_ids):
    """Mark memories only after the normal answer was generated successfully."""
    if not memory_ids:
        return
    memory = load_memory()
    timestamp = _now()
    changed = False
    for record in memory:
        if record["id"] in memory_ids:
            record["last_used"] = timestamp
            changed = True
    if changed:
        save_memory(memory)


def _memory_slot(record):
    text = record["memory"].casefold()
    if re.search(r"\b(?:my|the user's|user's) name\s*(?:is|:)", text):
        return "name"
    if "english" in text:
        return "language"
    if re.search(r"\b(?:ubuntu|windows|macos|mac os|linux)\b", text):
        return "operating-system"
    if re.search(r"\b(?:explanation|answer|response)s?\b", text):
        return "response-style"
    if re.search(r"\b(?:live in|based in)\b", text):
        return "location"
    return None


def _has_change_marker(text):
    return bool(re.search(
        r"\b(?:now|instead|rather than|changed|switch(?:ed|ing)?|"
        r"no longer|used to|from now on|anymore)\b",
        text,
        re.IGNORECASE,
    ))


def _same_memory(first, second, semantic_score):
    first_text = first["memory"].casefold()
    second_text = second["memory"].casefold()
    if first_text == second_text:
        return True
    first_tokens = _tokens(first_text)
    second_tokens = _tokens(second_text)
    union = len(first_tokens | second_tokens)
    overlap = len(first_tokens & second_tokens)
    smaller_set = min(len(first_tokens), len(second_tokens))
    return (
        (union and overlap / union >= 0.85)
        or SequenceMatcher(None, first_text, second_text).ratio() >= 0.93
        # Semantic similarity confirms a near rewording, but never replaces
        # lexical confirmation for learning or communication preferences.
        or (
            semantic_score >= 0.96
            and first["category"] == second["category"]
            and first["category"] not in {"learning", "preference", "communication"}
            and smaller_set
            and overlap / smaller_set >= 0.75
        )
    )


def _same_fact_identity(first, second):
    """Match the same statement when only its numeric value has changed."""
    first_tokens = {
        token for token in _tokens(first["memory"])
        if not re.fullmatch(r"\d+(?:\.\d+)?(?:k|m|b)?%?", token, re.IGNORECASE)
    }
    second_tokens = {
        token for token in _tokens(second["memory"])
        if not re.fullmatch(r"\d+(?:\.\d+)?(?:k|m|b)?%?", token, re.IGNORECASE)
    }
    if len(first_tokens) < 2 or len(second_tokens) < 2:
        return False
    overlap = len(first_tokens & second_tokens)
    union = len(first_tokens | second_tokens)
    smaller = min(len(first_tokens), len(second_tokens))
    return overlap / smaller >= 0.9 and overlap / union >= 0.8


def _clear_update_target(incoming, candidates):
    if not _has_change_marker(incoming["memory"]):
        return None
    incoming_slot = _memory_slot(incoming)
    for candidate in candidates:
        existing = candidate["record"]
        if incoming_slot and incoming_slot == _memory_slot(existing):
            return existing
        if incoming["category"] == existing["category"] and candidate["semantic_score"] >= 0.45:
            return existing
    return None


def _decide_with_deepseek(incoming, candidates, client):
    """Ask only for ambiguous, already-related memories; failure safely adds."""
    if client is None:
        return None
    compact_candidates = [
        {"index": index, "memory": item["record"]["memory"], "category": item["record"]["category"]}
        for index, item in enumerate(candidates[:3])
    ]
    try:
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Choose ADD, UPDATE, KEEP, or IGNORE for one user memory. "
                        "UPDATE only when the new fact clearly replaces a candidate; prefer ADD when uncertain. "
                        'Return JSON only: {"action":"ADD|UPDATE|KEEP|IGNORE","target":0}. '
                    ),
                },
                {"role": "user", "content": json.dumps({
                    "new": incoming["memory"], "candidates": compact_candidates
                })},
            ],
            max_tokens=60,
        )
        record_response_usage(response)
        content = response.choices[0].message.content or ""
        decision = json.loads(content.strip().strip("`"))
        action = decision.get("action")
        target = decision.get("target")
        if action not in {"ADD", "UPDATE", "KEEP", "IGNORE"}:
            return None
        if action in {"UPDATE", "KEEP"} and (
            not isinstance(target, int) or target not in range(len(compact_candidates))
        ):
            return None
        return action, target
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _prepare_incoming(memory, category=None, importance=None, memory_type=None):
    if isinstance(memory, dict):
        raw = dict(memory)
    else:
        raw = {"memory": memory}
    if category is not None:
        raw["category"] = category
    if importance is not None:
        raw["importance"] = importance
    if memory_type is not None:
        raw["memory_type"] = memory_type
    record, _ = _normalise_record(raw)
    return record


def _store_memory(incoming, embedding_model=None, client=None):
    if not incoming or SENSITIVE_PATTERN.search(incoming["memory"]):
        return {"action": "IGNORE", "memory": None, "existing": None, "memories": load_memory()}

    memory = load_memory()
    new_embedding = _embed(incoming["memory"], embedding_model)
    if new_embedding is not None:
        incoming["embedding"] = new_embedding

    candidates, embeddings_changed = _rank_memories(
        incoming["memory"], memory, embedding_model, 3, CANDIDATE_THRESHOLD
    )

    identity_matches = [
        record for record in memory
        if _same_fact_identity(incoming, record)
    ]
    if identity_matches:
        target = identity_matches[0]
        duplicate_ids = {record["id"] for record in identity_matches[1:]}
        unchanged = target["memory"].casefold() == incoming["memory"].casefold()
        if unchanged and not duplicate_ids:
            if embeddings_changed:
                save_memory(memory)
            return {
                "action": "KEEP", "memory": target,
                "existing": target, "memories": memory,
            }

        replacement = dict(incoming)
        replacement["id"] = target["id"]
        replacement["created_at"] = target["created_at"]
        replacement["last_used"] = target.get("last_used")
        replacement["updated_at"] = _now()
        memory = [record for record in memory if record["id"] not in duplicate_ids]
        memory[memory.index(target)] = replacement
        save_memory(memory)
        return {
            "action": "UPDATE", "memory": replacement,
            "existing": target, "memories": memory,
        }

    clear_target = _clear_update_target(incoming, candidates)
    if clear_target:
        replacement = dict(incoming)
        replacement["id"] = clear_target["id"]
        replacement["created_at"] = clear_target["created_at"]
        replacement["last_used"] = clear_target.get("last_used")
        replacement["updated_at"] = _now()
        index = memory.index(clear_target)
        memory[index] = replacement
        save_memory(memory)
        return {
            "action": "UPDATE", "memory": replacement,
            "existing": clear_target, "memories": memory,
        }

    for candidate in candidates:
        if _same_memory(incoming, candidate["record"], candidate["semantic_score"]):
            if embeddings_changed:
                save_memory(memory)
            return {
                "action": "KEEP", "memory": candidate["record"],
                "existing": candidate["record"], "memories": memory,
            }

    # Learning and conditional communication preferences are intentionally
    # preserved as independent memories unless a clear replacement was found.
    ambiguous = [
        item for item in candidates
        if item["record"]["category"] == incoming["category"]
        and item["semantic_score"] >= 0.72
    ]
    if incoming["category"] not in {"learning", "preference", "communication"} and ambiguous:
        decision = _decide_with_deepseek(incoming, ambiguous, client)
        if decision:
            action, target = decision
            if action == "KEEP":
                if embeddings_changed:
                    save_memory(memory)
                return {
                    "action": "KEEP", "memory": ambiguous[target]["record"],
                    "existing": ambiguous[target]["record"], "memories": memory,
                }
            if action == "IGNORE":
                if embeddings_changed:
                    save_memory(memory)
                return {"action": "IGNORE", "memory": None, "existing": None, "memories": memory}
            if action == "UPDATE":
                existing = ambiguous[target]["record"]
                replacement = dict(incoming)
                replacement["id"] = existing["id"]
                replacement["created_at"] = existing["created_at"]
                replacement["last_used"] = existing.get("last_used")
                replacement["updated_at"] = _now()
                memory[memory.index(existing)] = replacement
                save_memory(memory)
                return {
                    "action": "UPDATE", "memory": replacement,
                    "existing": existing, "memories": memory,
                }

    memory.append(incoming)
    save_memory(memory)
    return {"action": "ADD", "memory": incoming, "existing": None, "memories": memory}


def add_memory(
    memory,
    embedding_model=None,
    category=None,
    importance=None,
    memory_type=None,
    client=None,
    return_result=False,
):
    """Add, update, keep, or ignore memory while preserving the old API by default."""
    incoming = _prepare_incoming(memory, category, importance, memory_type)
    result = _store_memory(incoming, embedding_model, client)
    return result if return_result else result["memories"]


def remove_memory(search_text):
    memory = load_memory()
    kept_memory = [
        item for item in memory
        if search_text.casefold() not in item["memory"].casefold()
    ]
    removed = len(memory) - len(kept_memory)
    if removed:
        save_memory(kept_memory)
    return removed


def forget_memory(search_text, context=None, embedding_model=None):
    """Forget a direct match, or the single memory clearly referenced by context."""
    if search_text:
        removed = remove_memory(search_text)
        if removed:
            return removed
        query = f"{search_text}\n{context or ''}".strip()
    else:
        query = (context or "").strip()
    if not query:
        return 0

    memory = load_memory()
    ranked, changed = _rank_memories(query, memory, embedding_model, 1, SEMANTIC_THRESHOLD)
    if changed:
        save_memory(memory)
    if not ranked:
        return 0
    candidate = ranked[0]
    if (
        candidate["semantic_score"] < CANDIDATE_THRESHOLD
        and candidate["keyword_score"] < KEYWORD_FALLBACK_THRESHOLD
    ):
        return 0
    return 1 if delete_memory(candidate["record"]["id"]) else 0


def delete_memory(memory_id):
    """Delete one memory by its exact ID, returning the deleted record or None."""
    memory = load_memory()
    for index, record in enumerate(memory):
        if record["id"] == memory_id:
            deleted = memory.pop(index)
            save_memory(memory)
            return deleted
    return None


def get_memory_text():
    memory = load_memory()
    if not memory:
        return "No saved memories."
    return "\n".join(f"- {item['memory']}" for item in memory)

def get_memories():
    """Return all saved memories as structured records."""
    return load_memory()