import json
import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from memory import (
    add_memory,
    forget_memory,
    get_forget_request,
    get_explicit_memory,
    get_memories,
    get_relevant_memory_text,
    is_potential_memory,
    extract_memories,
)
from settings import DEFAULT_LINKEDIN_PROMPTS, get_settings
from retrieval import memory_retrieval_query, retrieval_query, retrieve_knowledge
from usage import record_response_usage
from web_reader import read_requested_pages


# ============================================================
# Setup
# ============================================================

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("DEEPSEEK_API_KEY was not found in .env")


client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_MESSAGE_CHARS = 1200
MAX_HISTORY_TOTAL_CHARS = 6000
print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

print("Opening ChromaDB...")
db = chromadb.PersistentClient(
    path="chroma_db"
)

collection = db.get_or_create_collection("knowledge")

print("AI backend ready.")


# ============================================================
# Chat function
# ============================================================

def _bounded_history(history):
    """Keep only recent, valid conversation turns within a small text budget."""
    if not isinstance(history, list):
        return []

    recent = []
    total_chars = 0
    for message in reversed(history[-MAX_HISTORY_MESSAGES:]):
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_HISTORY_MESSAGE_CHARS]
        if not content:
            continue
        remaining = MAX_HISTORY_TOTAL_CHARS - total_chars
        if remaining <= 0:
            break
        content = content[:remaining]
        recent.append({"role": role, "content": content})
        total_chars += len(content)

    return list(reversed(recent))


def _retrieve_knowledge(query, limit=3, enabled=True):
    return retrieve_knowledge(collection, model, query, limit=limit, enabled=enabled)


def _retrieval_diagnostics(memory_records, knowledge_diagnostics, history_count, saved_memory_count):
    return {
        "memory": {
            "ran": True,
            "store_count": saved_memory_count,
            "selected": [
                {
                    "id": item["id"],
                    "category": item["category"],
                    "similarity": item["similarity"],
                    "keyword_score": item["keyword_score"],
                }
                for item in memory_records
            ],
        },
        "knowledge": knowledge_diagnostics,
        "context": {
            "memory_count": len(memory_records),
            "memory_store_count": saved_memory_count,
            "knowledge_source_count": len(knowledge_diagnostics.get("sources", [])),
            "history_message_count": history_count,
        },
    }


def _log_retrieval_diagnostics(settings, diagnostics):
    if settings["memory_debug"]:
        print("Linkzen retrieval diagnostics: " + json.dumps(diagnostics, sort_keys=True))


def _deepseek_answer(messages, max_tokens, on_delta=None, disable_thinking=False):
    request_options = {
        "model": "deepseek-flash",
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if disable_thinking:
        request_options["extra_body"] = {"thinking": {"type": "disabled"}}

    if on_delta is None:
        response = client.chat.completions.create(
            **request_options,
        )
        record_response_usage(response)
        return response.choices[0].message.content or ""

    stream = client.chat.completions.create(
        **request_options,
        stream=True,
        stream_options={"include_usage": True},
    )
    answer_parts = []
    for chunk in stream:
        if chunk.usage is not None:
            record_response_usage(chunk)
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if isinstance(content, str) and content:
            answer_parts.append(content)
            on_delta(content)
    return "".join(answer_parts)


def chat(question: str, history=None, on_delta=None, image=None) -> dict:

    question = question.strip()

    if not question and not image:
        return "Please enter a question."
    if image and not question:
        question = "(The user attached an image without additional text.)"

    request_context, _ = read_requested_pages(question)

    history = _bounded_history(history)


    # ========================================================
    # Explicit memory commands
    # ========================================================

    forget_target = get_forget_request(question)
    if forget_target is not None:
        context = "\n".join(message["content"] for message in history[-4:])
        removed = forget_memory(
            forget_target,
            context=context,
            embedding_model=model,
        )
        return "I'll forget that." if removed else "I couldn't find a matching memory to forget."


    # ========================================================
    # Explicit memory
    # ========================================================

    explicit_memory = get_explicit_memory(question)

    if explicit_memory:

        add_memory(
            explicit_memory,
            embedding_model=model,
            return_result=True,
        )

        return "I'll remember that."


    # ========================================================
    # Automatic memory
    # ========================================================

    settings = get_settings()
    knowledge_query = retrieval_query(question, history)
    memory_query = memory_retrieval_query(question, history)
    memory_candidate = is_potential_memory(question)

    if settings["memory_debug"]:
        print(
            "Memory debug: automatic candidate "
            f"{'yes' if memory_candidate else 'no'}"
        )

    if settings["automatic_memory"] and memory_candidate:

        try:

            extracted_memories = extract_memories(
                question,
                client
            )

            if extracted_memories:

                memory_result = add_memory(
                    extracted_memories[0],
                    embedding_model=model,
                    client=client,
                    return_result=True,
                )

                if settings["memory_debug"]:
                    print(f"Memory debug: automatic action {memory_result['action']}")

            elif settings["memory_debug"]:
                print("Memory extracted: NONE")

        except Exception as error:

            print(
                f"Memory extraction failed: "
                f"{type(error).__name__}: {error}"
            )


    context, knowledge_sources, knowledge_diagnostics = _retrieve_knowledge(
        knowledge_query,
        enabled=settings["rag_enabled"],
    )


    # ========================================================
    # Relevant memories
    # ========================================================

    memories, memory_context = get_relevant_memory_text(
        memory_query,
        limit=3,
        embedding_model=model,
        return_details=True,
    )
    saved_memory_count = len(get_memories())
    if not memories:
        memories = (
            f"The Memory store contains {saved_memory_count} saved record(s), "
            "but none passed relevance for this request. Do not say the Memory "
            "store is empty."
            if saved_memory_count
            else "The Memory store currently contains no saved records."
        )

    diagnostics = _retrieval_diagnostics(
        memory_context,
        knowledge_diagnostics,
        len(history),
        saved_memory_count,
    )
    _log_retrieval_diagnostics(settings, diagnostics)


    # ========================================================
    # Prompt
    # ========================================================

    prompt = f"""
Relevant knowledge:
{context}

Relevant saved Memory records:
{memories}

Current request:
{request_context}

Context origins are distinct: saved Memory records are persistent facts about the
user; Knowledge is reference material from indexed files; recent conversation
history is only this chat. Do not describe Knowledge or chat history as Memory,
or claim that Memory is empty unless the Memory store is reported as empty below.
Use supplied Memory records for personal questions when relevant. For questions
about the user's name, background, or goals, use matching supplied Memory records
and do not contradict them with earlier assistant guesses. If no record supports
an answer, say the information is not available rather than inventing it.
Use recent conversation history only to resolve follow-ups. Answer briefly and naturally.
"""

    current_request_content = prompt
    if image:
        current_request_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image, "detail": "high"}},
        ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are the user's personal AI assistant. Use the supplied "
                "conversation history only to understand follow-ups. Treat saved "
                "Memory, Knowledge files, and conversation history as distinct "
                "sources. Use supplied Memory records for personal questions; "
                "never claim no memories are saved merely because no relevant "
                "record was supplied. Do not invent facts."
            ),
        },
        *(
            [{"role": "system", "content": settings["global_prompt"]}]
            if settings["global_prompt"].strip()
            else []
        ),
        *history,
        {"role": "user", "content": current_request_content},
    ]


    # ========================================================
    # DeepSeek
    # ========================================================

    answer = _deepseek_answer(messages, 800, on_delta)


    # ========================================================
    # Memory lifecycle
    # ========================================================

    return {
        "answer": answer,
        "sources": knowledge_sources,
        "memory_context": memory_context,
        "memory_store_count": saved_memory_count,
        "retrieval_diagnostics": diagnostics,
    }


def linkedin_tool(
    action: str,
    user_input: str = "",
    history=None,
    on_delta=None,
    images=None,
    prior_work=None,
    instructions="",
    performance_data="",
) -> dict:
    """Run a LinkedIn workspace task with relevant knowledge and memories."""
    if action not in DEFAULT_LINKEDIN_PROMPTS:
        raise ValueError("Unknown LinkedIn tool.")

    user_input = user_input.strip()
    instructions = instructions.strip()
    performance_data = performance_data.strip()
    images = images or []
    if action == "analyze_post" and not user_input and not images:
        raise ValueError("Paste or attach the LinkedIn post you want to analyse.")
    if action != "post_ideas" and not user_input and not images:
        raise ValueError("This tool needs some text to work with.")

    request_text = "\n\n".join(part for part in (user_input, instructions) if part)
    request_context, _ = read_requested_pages(request_text) if request_text else ("", False)

    task_context = {
        "analyze_profile": "LinkedIn profile headline About experience skills featured photo banner optimization",
        "create_post": "LinkedIn post writing style hooks calls to action draft critique",
        "analyze_post": (
            "LinkedIn post analysis content quality writing improvement feed distribution "
            "audience behaviour content structure hooks storytelling topic relevance "
            "post formats research datasets creator examples"
        ),
        "post_ideas": "AWS cloud learning LinkedIn post ideas",
        "make_comment": "LinkedIn post context natural comment responses",
        "reply_to_message": "private LinkedIn direct message reply tone concise professional networking recruiting",
        "ask_knowledge": "AWS LinkedIn and document knowledge",
    }[action]
    history = _bounded_history(history)
    retrieval_input = request_text if action == "reply_to_message" else request_text or task_context
    contextual_input = retrieval_query(retrieval_input, history)
    context_query = (
        contextual_input
        if action == "reply_to_message"
        else f"{task_context}\n{contextual_input}".strip()
    )

    settings = get_settings()
    prior_work_text = "No relevant prior work supplied."
    if action == "post_ideas" and prior_work:
        prior_work_text = "\n\n".join(
            f"Previous request: {item.get('request', '')[:1000]}\n"
            f"Previous output: {item.get('result', '')[:2500]}"
            for item in prior_work[-5:]
            if isinstance(item, dict)
        ) or prior_work_text

    knowledge_context, knowledge_sources, knowledge_diagnostics = _retrieve_knowledge(
        context_query,
        limit=4,
        enabled=settings["rag_enabled"],
    )

    memory_query = memory_retrieval_query(retrieval_input, history)
    if memory_query:
        memories, memory_context = get_relevant_memory_text(
            memory_query,
            limit=4,
            embedding_model=model,
            return_details=True,
        )
    else:
        memories, memory_context = "", []
    saved_memory_count = len(get_memories())
    if not memories:
        memories = (
            f"The Memory store contains {saved_memory_count} saved record(s), "
            "but none passed relevance for this request. Do not say the Memory "
            "store is empty."
            if saved_memory_count
            else "The Memory store currently contains no saved records."
        )

    diagnostics = _retrieval_diagnostics(
        memory_context,
        knowledge_diagnostics,
        len(history),
        saved_memory_count,
    )
    diagnostics["linkedin_action"] = action
    _log_retrieval_diagnostics(settings, diagnostics)

    if action == "reply_to_message":
        original_request = (
            f"Incoming private LinkedIn message:\n{user_input or 'The message is supplied in the attached screenshot.'}\n\n"
            f"User instructions or context:\n{instructions or 'No additional instructions were provided.'}\n\n"
            f"Relevant webpage context:\n{request_context if request_context != request_text else 'No webpage was requested.'}"
        )
    elif action == "analyze_post":
        post_to_analyze = (
            request_context
            if request_context != request_text
            else user_input or "The post is shown in the attached screenshot."
        )
        original_request = (
            "LinkedIn post to analyse:\n"
            f"{post_to_analyze}\n\n"
            f"Additional user context (optional):\n"
            f"{instructions or 'No additional context was provided.'}\n\n"
            f"Performance data (optional; analyse separately from the post content):\n"
            f"{performance_data or 'No performance data was provided.'}"
        )
    else:
        empty_request = (
            "Analyze the LinkedIn profile shown in the attached screenshot."
            if action == "analyze_profile"
            else "Generate ideas from the saved knowledge."
        )
        original_request = (
            f"User's original request:\n"
            f"{request_context or user_input or empty_request}"
        )

    user_content = (
        f"Relevant saved Knowledge:\n{knowledge_context}\n\n"
        f"Relevant saved Memory:\n{memories}\n\n"
        f"Relevant previous LinkedIn work:\n{prior_work_text}\n\n"
        f"{original_request}"
    )
    if images:
        user_content = [
            {"type": "text", "text": user_content},
            *[
                {"type": "image_url", "image_url": {"url": image, "detail": "high"}}
                for image in images
            ],
        ]

    answer = _deepseek_answer(
        [
            {
                "role": "system",
                "content": (
                    "You are the user's LinkedIn writing and analysis assistant. "
                    "Follow the task instructions. Use conversation history and "
                    "saved context only when relevant, respect the user's style "
                    "preferences, and never fabricate facts or personal experience."
                ),
            },
            {
                "role": "system",
                "content": settings["linkedin_prompts"].get(
                    action, DEFAULT_LINKEDIN_PROMPTS[action]
                ),
            },
            *history,
            {
                "role": "user",
                "content": user_content,
            },
        ],
        1200,
        on_delta,
        disable_thinking=action in {"analyze_profile", "analyze_post", "post_ideas","create_post"},
    )
    return {
        "answer": answer or "I couldn't generate a result. Please try again.",
        "sources": knowledge_sources,
        "memory_context": memory_context,
        "memory_store_count": saved_memory_count,
        "retrieval_diagnostics": diagnostics,
    }