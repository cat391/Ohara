from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.obsidian import ObsidianReader
from fastapi import FastAPI
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from llama_index.core import Document
# Remember to encrypt certain things for security purposes

app = FastAPI()

index = None

def main(vault_path):
    global index
    global vector_store

    # Define LlamaIndex settings to use local llm and not OpenAI
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

    # this disables all llms (including local), delete later
    Settings.llm = None 

    # Connect to Qdrant and create a database
    client = QdrantClient(":memory:") # change memory, it is just for testing now
    vector_store = QdrantVectorStore(client=client, collection_name="user_notes")

    # Load documents using llama index 
    documents = ObsidianReader(vault_path).load_data()

    # Builds the vector store index 
    index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

    print("index created!")

# Configure FastAPI to enable search of the database

@app.get("/search")

# Use indexer to find top three chunks of the query
async def search(q:str):
    if not index:
        return {"Error": "Index not initialized."}

    retriever = index.as_retriever(similarity_top_k=3)
    top_nodes = retriever.retrieve(q)

    if top_nodes:
        return top_nodes
    
    return {"Data": "Not Found"}

# A handler class for monitoring changes in the Obsidian vault directory.
class VaultHandler(FileSystemEventHandler):
    def on_modified(self,event):
        # Watchdog events can trigger on directories, we want to ignore those
        if event.is_directory or index is None:  
            return

        try:
            file_path = event.src_path
            new_content = open(file_path, 'r').read()

            index.update_ref_doc(Document(
                text=new_content,
                doc_id = file_path,
            ))
            print(f"Updated document: {file_path}")
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except IsADirectoryError:
            pass
    
    def on_deleted(self,event):
        if index is None:
            return

        file_path = event.src_path
        index.delete_ref_doc(file_path)
        print(f"Deleted document: {file_path}")
    
    def on_created(self,event):
        if index is None:
            return

        file_path = event.src_path
        new_content = open(file_path, 'r').read()

        index.insert(Document(
            text=new_content,
            doc_id = file_path,
        ))
        print(f"Created document: {file_path}")

if __name__ == "__main__":
    vault_path = "/Users/cole/Desktop/Obsidian Vaults/Computer Science"
    main(vault_path)

    observer = Observer()
    observer.schedule(VaultHandler(), path=vault_path, recursive=True)
    observer.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


    # Start fast api in this code