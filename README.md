# LovChat

LovChat is a lightweight retrieval-augmented chatbot for exploring the Lovdata public law datasets.
It builds a TF-IDF search index over the published HTML/XML documents and can optionally call the
OpenAI API to generate summarised answers from the retrieved context.

## Project structure

```
LovChat/
├── lovchat/            # Source package
│   ├── bot.py          # Retrieval + generation logic
│   ├── cli.py          # Command-line interface (`lovchat`)
│   ├── ingest.py       # Archive extraction and chunking helpers
│   ├── index.py        # Vector store construction utilities
│   └── settings.py     # Simple configuration / environment handling
├── pyproject.toml      # Project metadata and dependencies
├── README.md           # This file
└── (data/)             # Place archives and generated index here (ignored by git)
```

## Prerequisites

- Python 3.11 or newer (tested with 3.12)
- The Lovdata public archives (e.g. `gjeldende-lover.tar.bz2`, `gjeldende-sentrale-forskrifter.tar.bz2`).
  Copy the files into `data/raw/` inside this repository.
- An OpenAI API key if you want model-generated answers (set the environment variable `OPENAI_API_KEY`).
  Without a key, LovChat will fall back to returning the best matching excerpts.

Optional environment variables:

| Variable | Purpose |
| --- | --- |
| `LOVCHAT_RAW_DATA_DIR` | Custom location of the downloaded archives (`data/raw` by default). |
| `LOVCHAT_WORKSPACE_DIR` | Directory to hold extracted files and the TF-IDF index (`data/workspace` by default). |
| `LOVCHAT_OPENAI_MODEL` | Overrides the chat completion model (default `gpt-4o-mini`). |
| `OPENAI_BASE_URL` | Point to a custom OpenAI-compatible endpoint. |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Create the expected directories and copy the archives:

```bash
mkdir -p data/raw
cp ../lovdata-public-data/*.tar.bz2 data/raw/
```

## Build the index

```bash
lovchat build-index \
  --raw-dir data/raw \
  --workspace data/workspace
```

The command extracts the archives, chunks the HTML/XML documents, and saves a TF-IDF index at
`data/workspace/vector_store.pkl`.

## Chat with LovChat

Interactive mode:

```bash
lovchat chat --workspace data/workspace
```

Single question:

```bash
lovchat chat --workspace data/workspace --question "Hva er hjemmelen for forskrift X?"
```

LovChat displays the generated answer (or the best matching excerpts) alongside the top sources used.

## License

This project mirrors and interacts with content licensed under the Norwegian Licence for Open Data (NLOD 2.0).
Please review the Lovdata terms at https://api.lovdata.no/ before redistribution.
