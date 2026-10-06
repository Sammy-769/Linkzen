# Linkzen

Linkzen is a personal AI assistant for LinkedIn workflows, built with Python, FastAPI, RAG, ChromaDB, and the DeepSeek API.

It combines **retrieval-augmented generation (RAG)** with a persistent **memory system**, allowing the assistant to use both a private knowledge base and information it has learned about the user.

The project is designed as a local application rather than a hosted service.

## Features

### LinkedIn workspace

Linkzen provides separate tools for different LinkedIn tasks:

- **Analyse Profile** — analyse information supplied about a LinkedIn profile and separate observations from recommendations.
- **Create Post** — generate LinkedIn posts using retrieved knowledge, user preferences, and relevant memory.
- **Analyse Post** — analyse an existing LinkedIn post. Audience, intent, and performance metrics can optionally be supplied and are considered separately from the post itself.
- **Post Ideas** — generate ideas using the user's context and retrieved knowledge.
- **Make a Comment** — generate several short, natural comment options rather than generic praise.
- **Reply to a Message** — help formulate replies to LinkedIn messages.
- **Ask Knowledge** — answer questions using the project's knowledge base when relevant.

### RAG knowledge system

The RAG pipeline can work with:

- Markdown files
- Text files
- PDF documents

Documents are cleaned, split into chunks, embedded using `sentence-transformers/all-MiniLM-L6-v2`, and stored in ChromaDB.

The indexing system tracks document hashes so that changed or new documents can be re-indexed without unnecessarily processing everything again.

The public repository contains only the **knowledge directory structure**. The actual knowledge documents are private and are intentionally excluded from Git.

### Memory

Linkzen has a separate memory system for information about the user.

Memory can include:

- User preferences
- Relevant personal context
- Importance
- Timestamps
- Retrieved relevant memories

This allows the assistant to use information about the user without putting all of that information into every prompt manually.

### Usage tracking

The application also tracks API usage and token information so that DeepSeek usage and costs can be monitored.

## Architecture

```text
                         ┌──────────────────┐
                         │   Web Interface   │
                         │  HTML / CSS / JS  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │     FastAPI      │
                         │    server.py     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │     Assistant    │
                         │    assistant.py  │
                         └──────┬─────┬─────┘
                                │     │
                 ┌──────────────┘     └──────────────┐
                 ▼                                   ▼
        ┌─────────────────┐                 ┌─────────────────┐
        │       RAG       │                 │     Memory      │
        │ ChromaDB +      │                 │  User context   │
        │ embeddings      │                 │  & preferences  │
        └────────┬────────┘                 └────────┬────────┘
                 │                                   │
                 └────────────────┬──────────────────┘
                                  ▼
                         ┌──────────────────┐
                         │   DeepSeek API   │
                         └──────────────────┘
```

## Project structure

```text
Linkzen/
├── assistant.py          # AI tool routing and DeepSeek integration
├── chat_images.py        # Image handling for conversations
├── knowledge.py          # Knowledge file discovery and management
├── memory.py             # Persistent user memory
├── rag.py                # RAG indexing and document processing
├── retrieval.py          # Knowledge retrieval
├── server.py             # FastAPI application
├── settings.py           # Application settings
├── usage.py              # API usage tracking
├── web_reader.py         # Web content retrieval
│
├── knowledge/            # Private knowledge base structure
│   ├── aws/
│   ├── linkedin/
│   ├── documents/
│   └── other/
│
├── static/                # Web interface
│
├── tests/                 # Automated tests
│
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
└── start-linkzen.sh      # Portable launcher
```

## Requirements

- Python 3.12+
- A DeepSeek API key
- Internet access for the DeepSeek API
- Sufficient disk space for the embedding model and ChromaDB

The embedding model runs locally. The language model is accessed through the DeepSeek API.

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/Sammy-769/Linkzen.git
cd Linkzen
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Then add your DeepSeek API key to `.env`:

```text
DEEPSEEK_API_KEY=your_api_key_here
```

Do not commit `.env` to Git. It is intentionally ignored by `.gitignore`.

## Running Linkzen

The project includes a launcher:

```bash
./start-linkzen.sh
```

The launcher uses paths relative to the project directory, so it does not depend on the original developer's machine path.

## Knowledge base

The repository intentionally does not contain the actual knowledge documents used by the developer.

To use your own knowledge base, place supported files inside the appropriate directories under:

```text
knowledge/
```

For example:

```text
knowledge/
├── aws/
├── linkedin/
├── documents/
└── other/
```

The actual files are ignored by Git so that private notes, source material, and personal documents are not published accidentally.

## Testing

The project includes automated tests covering the main components.

Run the full test suite with:

```bash
python -m unittest discover -s tests
```

The current test suite contains **59 tests** covering areas including:

- Knowledge handling
- RAG retrieval
- Memory
- LinkedIn tools
- Usage tracking
- Settings
- Web reading
- Image handling

## Design principles

Linkzen is intentionally built around a few principles:

**Personal context matters.**
The assistant should understand the user's preferences and context rather than treating every request as completely independent.

**Retrieved information should support generation.**
The assistant uses RAG to retrieve relevant information instead of putting an entire knowledge base into every prompt.

**Private data stays local.**
Personal memory, usage information, API keys, the ChromaDB database, and the actual knowledge files are excluded from the public repository.

**Tools should have different responsibilities.**
Profile analysis, post creation, post analysis, commenting, messaging, and knowledge questions have different requirements and therefore use separate tool behaviours.

## Current limitations

Linkzen is currently a personal development project rather than a production service.

Some limitations include:

- The language model depends on the DeepSeek API.
- The knowledge base is maintained locally.
- The application has not been designed for multiple users.
- The current web interface is intentionally lightweight.
- Production authentication and deployment infrastructure are not included.

## Roadmap

Possible future improvements include:

- Better memory management and user-controlled memory
- More sophisticated retrieval and ranking
- Additional LinkedIn workflows
- Improved web research capabilities
- Better UI and conversation management
- More comprehensive evaluation of generated content
- Deployment and multi-user support

## Why I built it

I built Linkzen as a way to explore how an AI assistant can combine **RAG, persistent memory, external LLMs, local embeddings, and application-specific tools** into one practical system.

The project is also part of my learning journey towards building real-world AI and cloud applications.
