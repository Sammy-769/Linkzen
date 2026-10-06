# Linkzen

Linkzen is a local Python assistant that uses the DeepSeek API and can retrieve
relevant information from its saved Knowledge and Memory.

The LinkedIn workspace includes separate tools for creating posts and analysing
existing posts. To analyse a post, paste it into **Analyse Post** and optionally
add audience or intent context and performance metrics. Metrics are not required
and are considered separately from the post itself.

## Run the API test

```bash
source .venv/bin/activate
python app.py
```

## Knowledge folders

- `knowledge/linkein/` will eventually hold LinkedIn post examples or
  drafts that the assistant can use as reference.
- `knowledge/aws/` will eventually hold AWS notes and reference material.
- `knowledge/documents/` will eventually hold other documents you want the
  assistant to reference.
