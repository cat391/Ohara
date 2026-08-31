# Ohara

Ohara is a lightweight, local-first notes chatbot. It runs an on-device LLM and vector database so you can ask questions about your notes and get fast, cited answers. Everything happens on your machine, and after a one-time model download it works fully offline.

## Features

- Chat with your notes and get answers with citations
- Citations open the source note directly in Obsidian
- Fully local inference, no cloud and no API keys
- GPU-accelerated on Apple Silicon via Metal
- Continuous file watching keeps the index in sync as you edit your notes
- Optimized for Obsidian vaults, but works with any folder of markdown or text files

## Why Ohara

As notes grow across folders and formats, finding a specific fact gets slow and frustrating. Keyword search gives limited context in large vaults. Ohara lets you ask questions in plain language and points you back to the exact notes the answer came from.

## Installation

1. Download the latest `.dmg` from the [Releases](../../releases) page.
2. Open the `.dmg` and drag **Ohara** into your Applications folder.
3. The app is not yet notarized, so the first time you open it, right-click the app and choose **Open**, then click **Open** again. This is only needed once.

## Usage

1. Launch Ohara and select your Obsidian vault (or any notes folder) when prompted.
2. On first launch, Ohara downloads its AI models (about 830 MB, one time) and indexes your vault. A progress bar shows the status.
3. Ask questions in the chat. Answers include citations that open the source note in Obsidian.
4. Type `!vault` to switch to a different vault.

Models and the search index are stored in `~/Library/Application Support/dev.cole.ohara/`.

## How It Works

- **Frontend**: A Tauri desktop app with a React UI.
- **Backend**: A Python FastAPI server bundled into the app as a self-contained sidecar binary, so no Python installation is required.
- **LLM**: LiquidAI LFM2-1.2B-RAG running on llama.cpp with Metal GPU acceleration.
- **Retrieval**: Notes are embedded with bge-small-en and stored in a local Qdrant vector database. A file watcher re-indexes notes as they change.

## Development

Requirements: Python 3.11, Node.js, and Rust.

```bash
# backend environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# desktop app (spawns the backend automatically in dev mode)
cd frontend
npm install
npm run tauri:dev
```

To run the backend and frontend separately:

```bash
# terminal 1
source .venv/bin/activate
python backend/main.py --vault "/path/to/your/vault"

# terminal 2
cd frontend
npm run dev
```

## Building a Release

```bash
cd frontend
npm run tauri:build
```

This freezes the backend into a single binary with PyInstaller (`scripts/build-backend.sh`) and produces a `.dmg` in `frontend/src-tauri/target/release/bundle/dmg/`.

Pushing a `v*` tag builds the release automatically through GitHub Actions and attaches the `.dmg` to a GitHub Release.
