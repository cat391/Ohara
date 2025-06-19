from fastapi import FastAPI, HTTPException
from llm.indexer import VectorIndexer
from llm.watcher import VaultWatcher
import threading
import uvicorn
from contextlib import asynccontextmanager
from llm.local_llm import LocalLLM

app = FastAPI()
vault_path = "/Users/cole/Desktop/Obsidian Vaults/Computer Science"
indexer = VectorIndexer(vault_path=vault_path)  
watcher_thread = None # Required to run file watcher independently from FastAPI
llm = LocalLLM()  # Initialize the local LLM

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



if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=False  # Disable reload as we have our own file watcher
    )