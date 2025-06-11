from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.obsidian import ObsidianReader
from fastapi import FastAPI, HTTPException
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from llama_index.core import Document
from llm.indexer import VectorIndexer
from llm.watcher import VaultWatcher
import threading
import uvicorn


app = FastAPI()
vault_path = "/Users/cole/Desktop/Obsidian Vaults/Computer Science"
indexer = VectorIndexer(vault_path=vault_path)  
watcher_thread = None # Required to run file watcher independently from FastAPI

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
    

if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=False  # Disable reload as we have our own file watcher
    )