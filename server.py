import json
import queue
import subprocess
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from assistant import chat, linkedin_tool, model
from chat_images import InvalidChatImage, validate_chat_image
from knowledge import (
    _relative_path,
    create_knowledge_folder,
    delete_knowledge_item,
    is_indexed,
    list_knowledge_files,
    list_knowledge_directories,
    move_knowledge_item,
    read_manifest,
    rename_knowledge_item,
    run_indexer,
    safe_knowledge_path,
    safe_knowledge_file_path,
    upload_destination,
)
from memory import add_memory, delete_memory, get_memories
from settings import DEFAULT_LINKEDIN_PROMPTS, get_settings, update_settings
from usage import summarize_usage
from web_reader import WebpageReadError, requested_urls


app = FastAPI(title="Linkzen")


class ConversationMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ConversationMessage] = Field(default_factory=list)
    image: str | None = None


class ChatResponse(BaseModel):
    answer: str


class MemoryRequest(BaseModel):
    memory: str



class SettingsRequest(BaseModel):
    automatic_memory: bool | None = None
    rag_enabled: bool | None = None
    memory_debug: bool | None = None
    global_prompt: str | None = Field(default=None, max_length=8000)
    linkedin_prompts: dict[str, str] | None = None


class KnowledgeReindexRequest(BaseModel):
    path: str


class KnowledgeFolderRequest(BaseModel):
    parent: str = ""
    name: str


class KnowledgeRenameRequest(BaseModel):
    path: str
    name: str


class KnowledgeMoveRequest(BaseModel):
    path: str
    destination_folder: str = ""


class LinkedInToolRequest(BaseModel):
    action: str
    text: str = ""
    instructions: str = ""
    performance_data: str = ""
    history: list[ConversationMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list, max_length=4)
    prior_work: list[dict[str, str]] = Field(default_factory=list, max_length=8)


def _memory_for_api(memory):
    """Keep embedding vectors in local storage, never in browser responses."""
    return {
        key: value
        for key, value in memory.items()
        if key != "embedding"
    }

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    try:
        image = validate_chat_image(request.image) if request.image else None
    except InvalidChatImage as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    history = []
    for message in request.history[-10:]:
        history.append({"role": message.role, "content": message.content})
    return StreamingResponse(
        _assistant_event_stream(
            chat,
            request.message,
            request.message,
            history,
            kwargs={"image": image},
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/usage")
def usage_endpoint(timezone: str = "UTC"):
    return summarize_usage(timezone)


@app.post("/api/linkedin")
def linkedin_tool_endpoint(request: LinkedInToolRequest):
    history = [
        {"role": message.role, "content": message.content}
        for message in request.history[-10:]
    ]
    return StreamingResponse(
        _assistant_event_stream(
            linkedin_tool,
            request.text,
            request.action,
            request.text,
            history,
            kwargs={
                "images": _validate_linkedin_images(request.images),
                "prior_work": request.prior_work,
                "instructions": request.instructions,
                "performance_data": request.performance_data,
            },
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _validate_linkedin_images(images):
    allowed_prefixes = (
        "data:image/jpeg;base64,",
        "data:image/png;base64,",
        "data:image/gif;base64,",
        "data:image/webp;base64,",
    )
    total_length = 0
    for image in images:
        if not image.startswith(allowed_prefixes):
            raise HTTPException(status_code=400, detail="Images must be JPEG, PNG, GIF, or WebP data URLs.")
        total_length += len(image)
    if total_length > 12_000_000:
        raise HTTPException(status_code=413, detail="Selected images exceed the upload limit.")
    return images


def _assistant_event_stream(function, request_text, *args, kwargs=None):
    """Stream status and answer tokens from one shared assistant operation."""
    if requested_urls(request_text):
        yield f"data: {json.dumps({'type': 'status', 'message': '🔗 Reading webpage...'})}\n\n"

    events = queue.Queue()

    def on_delta(text):
        events.put({"type": "token", "text": text})

    def run_assistant():
        try:
            result = function(*args, on_delta=on_delta, **(kwargs or {}))
            if isinstance(result, dict):
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                memory_context = result.get("memory_context", [])
                memory_store_count = result.get("memory_store_count")
            else:
                answer = result
                sources = []
                memory_context = []
                memory_store_count = None
            events.put({
                "type": "done",
                "answer": answer,
                "sources": sources,
                "memory_context": memory_context,
                "memory_store_count": memory_store_count,
            })
        except WebpageReadError as error:
            events.put({"type": "error", "message": str(error)})
        except ValueError as error:
            events.put({"type": "error", "message": str(error)})
        except Exception:
            events.put({
                "type": "error",
                "message": "The assistant could not complete the request.",
            })

    threading.Thread(target=run_assistant, daemon=True).start()
    while True:
        event = events.get()
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        if event["type"] in {"done", "error"}:
            break


# ============================================================
# Memories
# ============================================================

@app.get("/api/memories")
def memories_endpoint():

    return {
        "memories": [
            _memory_for_api(memory)
            for memory in get_memories()
        ]
    }


@app.post("/api/memories")
def add_memory_endpoint(request: MemoryRequest):

    memory_text = request.memory.strip()

    if not memory_text:
        raise HTTPException(
            status_code=400,
            detail="Memory cannot be empty."
        )

    result = add_memory(
        memory_text,
        embedding_model=model,
        return_result=True,
    )

    return {
        "action": result["action"],
        "memory": (
            _memory_for_api(result["memory"])
            if result["memory"] else None
        ),
    }


@app.delete("/api/memories/{memory_id}")
def delete_memory_endpoint(memory_id: str):

    deleted = delete_memory(memory_id)

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found."
        )

    return {
        "success": True,
        "deleted": _memory_for_api(deleted)
    }


# ============================================================
# Settings
# ============================================================

@app.get("/api/settings")
def settings_endpoint():
    return {
        **get_settings(),
        "linkedin_prompt_defaults": DEFAULT_LINKEDIN_PROMPTS,
    }


@app.patch("/api/settings")
def update_settings_endpoint(request: SettingsRequest):
    changes = request.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No setting was supplied.")
    return update_settings(**changes)
# ============================================================
# Knowledge
# ============================================================

@app.get("/api/knowledge")
def knowledge_endpoint(path: str = ""):
    try:
        return {"path": path, "entries": list_knowledge_files(path)}
    except (ValueError, NotADirectoryError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/knowledge/folders")
def knowledge_folders_endpoint():
    return {"folders": list_knowledge_directories()}


@app.post("/api/knowledge/reindex-all")
def reindex_all_knowledge_endpoint():
    try:
        output = run_indexer()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=500, detail="Could not re-index Knowledge files.") from error

    manifest = read_manifest()
    return {
        "success": True,
        "indexed_files": len(manifest),
        "message": "All supported Knowledge files were re-indexed.",
        "output": output[-2000:],
    }


@app.post("/api/knowledge/upload")
async def upload_knowledge_endpoint(request: Request, folder: str = "", filename: str = ""):
    try:
        destination = upload_destination(folder, filename)
    except (ValueError, FileExistsError, NotADirectoryError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")

    destination.write_bytes(content)
    relative_path = _relative_path(destination)

    try:
        run_indexer()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not index the uploaded file.") from error

    if not is_indexed(relative_path):
        destination.unlink(missing_ok=True)
        run_indexer()
        raise HTTPException(status_code=400, detail="The file could not be read and indexed.")

    return {
        "success": True,
        "file": {
            "path": relative_path,
            "name": destination.name,
            "category": relative_path.split("/", 1)[0],
        },
    }


@app.post("/api/knowledge/folders")
def create_knowledge_folder_endpoint(request: KnowledgeFolderRequest):
    try:
        path = create_knowledge_folder(request.parent, request.name)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValueError, NotADirectoryError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"success": True, "path": path}


@app.patch("/api/knowledge/rename")
def rename_knowledge_item_endpoint(request: KnowledgeRenameRequest):
    try:
        source = safe_knowledge_path(request.path, allow_root=False)
        new_path = rename_knowledge_item(request.path, request.name)
        run_indexer()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        if "new_path" in locals():
            try:
                safe_knowledge_path(new_path, allow_root=False).rename(source)
                run_indexer()
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"success": True, "path": new_path}


@app.patch("/api/knowledge/move")
def move_knowledge_item_endpoint(request: KnowledgeMoveRequest):
    try:
        source = safe_knowledge_path(request.path, allow_root=False)
        new_path = move_knowledge_item(request.path, request.destination_folder)
        if new_path != request.path:
            run_indexer()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValueError, NotADirectoryError, RuntimeError, subprocess.TimeoutExpired) as error:
        if "new_path" in locals():
            try:
                safe_knowledge_path(new_path, allow_root=False).rename(source)
                run_indexer()
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"success": True, "path": new_path}


@app.post("/api/knowledge/reindex")
def reindex_knowledge_endpoint(request: KnowledgeReindexRequest):
    try:
        path = safe_knowledge_file_path(request.path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    relative_path = _relative_path(path)
    try:
        run_indexer(force_file=relative_path)
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=500, detail="Could not re-index the file.") from error

    if not is_indexed(relative_path):
        raise HTTPException(status_code=400, detail="The file could not be indexed.")

    return {"success": True, "path": relative_path}


@app.delete("/api/knowledge/{file_path:path}")
def delete_knowledge_endpoint(file_path: str):
    try:
        delete_knowledge_item(file_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, NotADirectoryError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        run_indexer()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=500, detail="The item was deleted, but the RAG index cleanup failed.") from error

    manifest = read_manifest()
    if any(path == file_path or path.startswith(f"{file_path}/") for path in manifest):
        raise HTTPException(status_code=500, detail="The RAG index still contains the deleted file.")

    return {"success": True, "deleted": file_path}




app.mount(
    "/",
    StaticFiles(
        directory="static",
        html=True
    ),

    name="static",
)