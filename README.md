# Ohara

Ohara is a lightweight, local-first notes chatbot. It is an on-device LLM plus vector database that lets you ask about your notes and get fast, cited answers.
 
## Highlights

- Chat with your notes for fast, cited answers
- Completely local and offline; no cloud needed
- Native desktop UI with Tauri
- Continous file watching, so RAG is in sync with your notes

## Problem Solved 🚀

As online notes expand across folders and formats, locating a specific fact becomes time-consuming and confusing. Conventional keyword search provides limited context in large note directories, such as Obsidian vaults. Ohara is designed to eliminate that wasted time and provide a way to chat with your notes. Ohara is optimized for Obsidian vaults, but can also work with text/markdown files. 

## Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Run

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd Ohara
   ```

2. Add your Obsidian vault:
   ```bash
   # Option A: Copy your vault into the project
   cp -r /path/to/your/obsidian/vault ./vault

   # Option B: Symlink it
   ln -s /path/to/your/obsidian/vault ./vault
   ```

3. Start Ohara:
   ```bash
   docker compose up --build
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

The first startup takes a few minutes while the backend indexes your vault and loads the LLM model. Subsequent starts are much faster since the index is persisted.

### Stopping

```bash
docker compose down
```

To also remove the vector index (forces re-indexing on next start):
```bash
docker compose down -v
```

