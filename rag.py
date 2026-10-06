from pathlib import Path
import hashlib
import json
import re
import sys

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from retrieval import legacy_index_metadata


# ============================================================
# Configuration
# ============================================================

KNOWLEDGE_DIR = Path("knowledge")
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "knowledge"
MANIFEST_FILE = Path("rag_manifest.json")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


# ============================================================
# Load embedding model
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(MODEL_NAME)


# ============================================================
# Connect to ChromaDB
# ============================================================

print("Opening ChromaDB...")

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

try:
    collection = chroma_client.get_collection(
        COLLECTION_NAME
    )
except Exception:
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME
    )


# ============================================================
# Load manifest
# ============================================================

if MANIFEST_FILE.exists():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
else:
    manifest = {}


# ============================================================
# File helpers
# ============================================================

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
}

force_file = None
if len(sys.argv) == 3 and sys.argv[1] == "--force":
    force_file = sys.argv[2]


def get_file_hash(path):
    """
    Create a SHA-256 hash of a file.

    This lets us detect whether a file has changed.
    """

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            sha256.update(data)

    return sha256.hexdigest()


def clean_text(text):
    """
    Clean unnecessary whitespace while preserving paragraphs.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# Read files
# ============================================================

def read_file(path):
    """
    Read TXT, Markdown and PDF files.
    """

    extension = path.suffix.lower()

    if extension in {".txt", ".md"}:

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    if extension == ".pdf":

        reader = PdfReader(str(path))

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n\n".join(pages)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )


# ============================================================
# Determine document category
# ============================================================

def get_category(path):
    """
    Determine what kind of knowledge this is.
    """

    relative = path.relative_to(KNOWLEDGE_DIR)

    first_folder = relative.parts[0]

    if first_folder == "linkedin":
        return "linkedin"

    if first_folder == "aws":
        return "aws"

    if first_folder == "documents":
        return "document"

    return "other"


# ============================================================
# Create readable source name
# ============================================================

def get_source_name(path):
    """
    Convert a filename into a human-readable title.
    """

    name = path.stem

    name = name.replace("_", " ")
    name = name.replace("-", " ")

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    return name.title()


# ============================================================
# Better chunking
# ============================================================

def chunk_text(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):
    """
    Split text primarily by paragraphs rather than
    blindly cutting every N characters.
    """

    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if p.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:

        # If the paragraph fits, add it to the current chunk.
        if len(current) + len(paragraph) + 2 <= chunk_size:

            if current:
                current += "\n\n"

            current += paragraph

        else:

            if current:
                chunks.append(current)

            # Very large paragraphs need to be split.
            if len(paragraph) > chunk_size:

                start = 0

                while start < len(paragraph):

                    end = start + chunk_size

                    piece = paragraph[start:end].strip()

                    if piece:
                        chunks.append(piece)

                    start += chunk_size - overlap

                current = ""

            else:
                current = paragraph

    if current:
        chunks.append(current)

    return chunks


# ============================================================
# Find all knowledge files
# ============================================================

files = sorted(
    [
        path
        for path in KNOWLEDGE_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
)

print(f"Found {len(files)} knowledge files.")


# ============================================================
# Track current files
# ============================================================

current_files = set()

for path in files:

    relative_path = str(
        path.relative_to(KNOWLEDGE_DIR)
    )

    current_files.add(relative_path)


# ============================================================
# Remove deleted files from ChromaDB
# ============================================================

indexed_records = collection.get(include=["metadatas"])
indexed_metadata = indexed_records["metadatas"] or []
indexed_files = {
    metadata["file"]
    for metadata in indexed_metadata
    if metadata and metadata.get("file")
}
legacy_sources_by_file, stale_legacy_sources = legacy_index_metadata(
    indexed_metadata,
    manifest,
    current_files,
)

legacy_sources_to_remove = stale_legacy_sources | {
    source
    for sources in legacy_sources_by_file.values()
    for source in sources
}
for source in legacy_sources_to_remove:
    collection.delete(where={"source": source})

deleted_files = (set(manifest.keys()) | indexed_files) - current_files

for relative_path in deleted_files:

    print(f"Removing deleted file: {relative_path}")

    collection.delete(
        where={
            "file": relative_path
        }
        )

    manifest.pop(relative_path, None)


# ============================================================
# Process files
# ============================================================

total_new_chunks = 0
total_updated = 0
total_skipped = 0


for path in files:

    relative_path = str(
        path.relative_to(KNOWLEDGE_DIR)
    )

    file_hash = get_file_hash(path)

    category = get_category(path)

    source_name = get_source_name(path)


    # --------------------------------------------------------
    # Skip unchanged files
    # --------------------------------------------------------

    if (
        relative_path in manifest
        and manifest[relative_path]["hash"] == file_hash
        and relative_path != force_file
        and relative_path not in legacy_sources_by_file
    ):

        print(
            f"Skipping unchanged: {relative_path}"
        )

        total_skipped += 1

        continue


    # --------------------------------------------------------
    # File is new or changed
    # --------------------------------------------------------

    if relative_path in manifest:

        print(
            f"Updating: {relative_path}"
        )

        try:
            collection.delete(
                where={
                    "file": relative_path
                }
            )
        except Exception:
            pass
        total_updated += 1

    else:

        print(
            f"Adding: {relative_path}"
        )

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    try:

        text = read_file(path)

    except Exception as e:

        print(
            f"ERROR reading {relative_path}: {e}"
        )

        continue


    text = clean_text(text)


    if not text:

        print(
            f"Skipping empty file: {relative_path}"
        )

        continue


    # --------------------------------------------------------
    # Create chunks
    # --------------------------------------------------------

    chunks = chunk_text(text)


    documents = []
    embeddings = []
    metadatas = []
    ids = []


    for index, chunk in enumerate(chunks):

        chunk_id = (
            f"{relative_path}"
            f"::{file_hash[:12]}"
            f"::{index}"
        )

        documents.append(chunk)

        metadatas.append(
            {
                "file": relative_path,
                "source": source_name,
                "category": category,
                "chunk": index,
            }
        )

        ids.append(chunk_id)


    # --------------------------------------------------------
    # Create embeddings
    # --------------------------------------------------------

    print(
        f"Creating {len(chunks)} chunks "
        f"for {source_name}..."
    )

    embeddings = embedding_model.encode(
        documents,
        show_progress_bar=False
    ).tolist()


    # --------------------------------------------------------
    # Store in ChromaDB
    # --------------------------------------------------------

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )


    # --------------------------------------------------------
    # Save file information
    # --------------------------------------------------------

    manifest[relative_path] = {
        "hash": file_hash,
        "category": category,
        "source": source_name,
        "chunks": len(chunks),
    }

    total_new_chunks += len(chunks)


# ============================================================
# Save manifest
# ============================================================

with open(
    MANIFEST_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# Summary
# ============================================================

print()
print("=" * 50)
print("RAG indexing complete")
print("=" * 50)

print(f"Knowledge files: {len(files)}")
print(f"New chunks: {total_new_chunks}")
print(f"Updated files: {total_updated}")
print(f"Unchanged files: {total_skipped}")

print()
print("Your knowledge base is ready.")