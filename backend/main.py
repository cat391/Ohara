from fastapi import FastAPI, HTTPException
from llm.indexer import VectorIndexer
from llm.watcher import VaultWatcher
import threading
import uvicorn
from contextlib import asynccontextmanager
from llm.local_llm import LocalLLM
from fastapi.middleware.cors import CORSMiddleware 
from pathlib import Path
import argparse, os

# Create correct file path to model 
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "phi-2.Q4_K_M.gguf"

app = FastAPI()

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

# passes in vault path argument from front end
p = argparse.ArgumentParser()
p.add_argument("--vault")
args = p.parse_args()

# vault_path = args.vault or os.environ.get("OHARA_VAULT")
# # fall back if vault not provided
# if not vault_path:
#     raise SystemExit("Vault path not provided")
vault_path = "/Users/cole/Desktop/Obsidian Vaults/Computer Science"

print("Using vault: ", vault_path)

indexer = VectorIndexer(vault_path=vault_path)  
watcher_thread = None # Required to run file watcher independently from FastAPI
llm = LocalLLM(MODEL_DIR)  # Initialize the local LLM

# TODO: Convert to lifespan function
@app.on_event("startup")
async def startup_event():
    global watcher_thread

    try:
        indexer.initialize_index()

        watcher = VaultWatcher(indexer=indexer, vault_path=vault_path)
        watcher_thread = threading.Thread(target=watcher.start, daemon=True) # Daemon thread allows it to run in the background
        watcher_thread.start()
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Initialization failed: {str(e)}"
        )

@app.get("/search")

async def search(q:str):
    if not indexer:
        return {"Error": "Indexer not initialized."}

    # Retrieve top nodes based on the query
    nodes = indexer.search(q)

    if not nodes:
        return {"Data": "Not Found"}

    # Return response from the local LLM
    return llm.answer_question(nodes, q)

@app.get("/status")

def status():
    return {"status": "running"}



if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=False  # Disable reload as we have our own file watcher
    )

