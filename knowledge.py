import json
import shutil
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath


PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
MANIFEST_FILE = PROJECT_DIR / "rag_manifest.json"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}
CATEGORY_FOLDERS = {
    "aws": "aws",
    "linkedin": "linkedin",
    "documents": "documents",
    "other": "other",
}


def _relative_path(path):
    return path.relative_to(KNOWLEDGE_DIR).as_posix()


def _category_from_relative(relative_path):
    folder = Path(relative_path).parts[0] if Path(relative_path).parts else ""
    for category, category_folder in CATEGORY_FOLDERS.items():
        if folder == category_folder:
            return category
    return "other"


def safe_knowledge_path(relative_path="", allow_root=True):
    """Resolve a relative Knowledge path and reject traversal and external paths."""
    if not isinstance(relative_path, str):
        raise ValueError("A Knowledge-relative path is required.")
    if "\x00" in relative_path or "\\" in relative_path or PurePosixPath(relative_path).is_absolute() or PureWindowsPath(relative_path).drive:
        raise ValueError("Absolute paths are not allowed in Knowledge.")
    parts = PurePosixPath(relative_path).parts
    if any(part in {".", ".."} for part in parts):
        raise ValueError("Path traversal is not allowed in Knowledge.")
    if (not relative_path or not parts) and not allow_root:
        raise ValueError("The Knowledge root cannot be modified.")

    root = KNOWLEDGE_DIR.resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("Path must remain inside Knowledge.") from error
    return path


def _safe_name(name):
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ValueError("A filename is required.")
    if name != Path(name).name or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError("Names cannot contain path separators.")
    if name.strip() != name:
        raise ValueError("Names cannot start or end with whitespace.")
    return name


def safe_knowledge_file_path(relative_path, allow_missing=False):
    path = safe_knowledge_path(relative_path, allow_root=False)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .md, .txt, and .pdf files are supported.")
    if not allow_missing and not path.is_file():
        raise FileNotFoundError("Knowledge file not found.")
    return path


def safe_knowledge_directory(relative_path="", allow_missing=False):
    path = safe_knowledge_path(relative_path)
    if not allow_missing and not path.is_dir():
        raise NotADirectoryError("Knowledge folder not found.")
    return path


def _ensure_default_folders():
    root = safe_knowledge_directory("")
    for folder in CATEGORY_FOLDERS.values():
        if (root / folder).is_symlink():
            raise ValueError("Default Knowledge folders cannot be symlinks.")
        path = safe_knowledge_path(folder, allow_root=False)
        path.mkdir(exist_ok=True)


def upload_destination(folder, filename):
    destination_folder = safe_knowledge_directory(folder)
    safe_name = _safe_name(filename)
    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .txt, .md, and .pdf files are supported.")
    destination = destination_folder / safe_name
    if destination.exists():
        raise FileExistsError("A file with that name already exists in this category.")
    return destination


def list_knowledge_files(folder=""):
    _ensure_default_folders()
    directory = safe_knowledge_directory(folder)
    entries = []
    manifest = read_manifest()
    for path in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold())):
        if path.is_symlink():
            continue
        relative_path = _relative_path(path)
        is_directory = path.is_dir()
        if not is_directory and path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        entries.append({
            "path": relative_path,
            "name": path.name,
            "category": _category_from_relative(relative_path),
            "type": "folder" if is_directory else "file",
            "extension": "" if is_directory else path.suffix.lower(),
            "size": 0 if is_directory else path.stat().st_size,
            "indexed": False if is_directory else relative_path in manifest,
        })
    return entries


def list_knowledge_directories():
    _ensure_default_folders()
    root = safe_knowledge_directory("")
    folders = [""]
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_dir():
            continue
        safe_knowledge_path(_relative_path(path), allow_root=False)
        folders.append(_relative_path(path))
    return sorted(folders, key=str.casefold)


def create_knowledge_folder(parent, name):
    safe_knowledge_directory(parent)
    folder_name = _safe_name(name)
    destination = safe_knowledge_path(
        (PurePosixPath(parent) / folder_name).as_posix() if parent else folder_name,
        allow_root=False,
    )
    if destination.exists():
        raise FileExistsError("A Knowledge item with that name already exists.")
    destination.mkdir()
    return _relative_path(destination)


def rename_knowledge_item(relative_path, name):
    source = safe_knowledge_path(relative_path, allow_root=False)
    if not source.exists():
        raise FileNotFoundError("Knowledge item not found.")
    if source.is_file() and source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .md, .txt, and .pdf files can be renamed.")
    new_name = _safe_name(name)
    if source.is_file() and Path(new_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .md, .txt, and .pdf files are supported.")
    destination = safe_knowledge_path(
        (PurePosixPath(relative_path).parent / new_name).as_posix(),
        allow_root=False,
    )
    if destination.exists():
        raise FileExistsError("A Knowledge item with that name already exists.")
    source.rename(destination)
    return _relative_path(destination)


def move_knowledge_item(relative_path, destination_folder):
    source = safe_knowledge_path(relative_path, allow_root=False)
    if not source.exists():
        raise FileNotFoundError("Knowledge item not found.")
    if source.is_file() and source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .md, .txt, and .pdf files can be moved.")
    target_folder = safe_knowledge_directory(destination_folder)
    if source.is_dir() and (target_folder == source or source in target_folder.parents):
        raise ValueError("A folder cannot be moved into itself or one of its subfolders.")
    destination = safe_knowledge_path(
        (PurePosixPath(destination_folder) / source.name).as_posix()
        if destination_folder else source.name,
        allow_root=False,
    )
    if destination == source:
        return _relative_path(source)
    if destination.exists():
        raise FileExistsError("A Knowledge item with that name already exists in the destination.")
    source.rename(destination)
    return _relative_path(destination)


def delete_knowledge_item(relative_path):
    path = safe_knowledge_path(relative_path, allow_root=False)
    if not path.exists():
        raise FileNotFoundError("Knowledge item not found.")
    if path.is_file() and path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .md, .txt, and .pdf files can be deleted through Knowledge.")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return relative_path


def read_manifest():
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def run_indexer(force_file=None):
    command = [sys.executable, str(PROJECT_DIR / "rag.py")]
    if force_file:
        command.extend(["--force", force_file])

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "The RAG indexer failed.")
    return result.stdout


def is_indexed(relative_path):
    return relative_path in read_manifest()

