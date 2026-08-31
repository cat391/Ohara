# Keep Hugging Face libraries quiet; downloads are handled explicitly in model_fetch
import os
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from fastapi import FastAPI
from llm.indexer import VectorIndexer
from llm.watcher import VaultWatcher
from llm import model_fetch
import threading
import uvicorn
from contextlib import asynccontextmanager
from llm.local_llm import LocalLLM
from fastapi.middleware.cors import CORSMiddleware
import argparse

# passes in vault path argument from front end
p = argparse.ArgumentParser()
p.add_argument("--vault")
args = p.parse_args()

vault_path = args.vault or os.environ.get("OHARA_VAULT")
# fall back if vault not provided
if not vault_path:
    raise SystemExit("Vault path not provided")

print("Using vault: ", vault_path)

# Startup state reported by /status so the frontend can show download/index progress.
# Phases: starting -> downloading -> loading -> indexing -> running (or error)
app_state = {"phase": "starting", "progress": 0.0, "detail": ""}

llm = None
indexer = None


def _initialize():
    """Download models if missing, then load the LLM and build the index.

    Runs in a background thread so the server can answer /status immediately —
    the first-run model download takes minutes and the frontend polls for it.
    """
    global llm, indexer
    try:
        app_state["phase"] = "downloading"

        def on_progress(fraction, filename):
            app_state["progress"] = round(fraction, 4)
            app_state["detail"] = filename

        llm_path, embed_dir = model_fetch.ensure_models(progress_cb=on_progress)

        app_state["phase"] = "loading"
        app_state["progress"] = 1.0
        llm = LocalLLM(llm_path)

        app_state["phase"] = "indexing"
        indexer = VectorIndexer(
            vault_path=vault_path,
            embed_dir=embed_dir,
            db_path=model_fetch.app_data_dir() / "qdrant_db",
        )
        indexer.initialize_index()

        watcher = VaultWatcher(indexer=indexer, vault_path=vault_path)
        # Daemon thread allows the watcher to run in the background
        threading.Thread(target=watcher.start, daemon=True).start()

        app_state["phase"] = "running"
    except Exception as e:
        app_state["phase"] = "error"
        app_state["detail"] = str(e)
        print(f"Initialization failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_initialize, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)

# CORS Settings
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "http://tauri.localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/search")
async def search(q: str):
    if app_state["phase"] != "running":
        return {"answer": None, "sources": None, "error": f"Backend is {app_state['phase']}"}

    # Retrieve top nodes based on the query
    nodes = indexer.search(q)

    if not nodes:
        return {"Data": "Not Found"}

    # Return response from the local LLM
    return llm.answer_question(nodes, q)


@app.get("/status")
def status():
    return {
        "status": app_state["phase"],
        "progress": app_state["progress"],
        "detail": app_state["detail"],
    }


if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",  # local app: never expose the API beyond this machine
        port=8000,
        reload=False,  # Disable reload as we have our own file watcher
    )
