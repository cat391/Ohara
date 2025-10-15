from llama_index.core import VectorStoreIndex, Settings
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.obsidian import ObsidianReader
from llama_index.core import Document
from pathlib import Path
import os
import time



class VectorIndexer:
    def __init__(self, vault_path):
        self.vault_path = vault_path
        self.index = None
        base = Path(__file__).resolve().parents[1] 
        self.embed_dir = base / "models" / "bge-small-en"
    
    def initialize_index(self):
        if not self.embed_dir.exists():
            raise RuntimeError(f"Embedding model folder not found: {self.embed_dir}")

        Settings.embed_model = HuggingFaceEmbedding(
            model_name=str(self.embed_dir),
            cache_folder=str(self.embed_dir),
            local_files_only=True,      
        )

        # this disables all llms (including local), delete later
        Settings.llm = None 

        # Connect to Qdrant and create a database
        client = QdrantClient(":memory:") # change memory, it is just for testing now
        vector_store = QdrantVectorStore(client=client, collection_name="user_notes")

        # Load documents using llama index 
        documents = ObsidianReader(self.vault_path).load_data()

        # Builds the vector store index 
        self.index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

        print("Index initialized successfully.")

    
    # Handles updating the index based on file system events.
    def _update_index(self, event, type_of_change = "modified"):
        if self.index is None:
            return

        # Ignore directory updates early, we only want to update files
        if getattr(event, "is_directory", False):
            return
        
        file_path = os.path.abspath(event.src_path) # path of the file that was modified
        
        if type_of_change == "deleted":
            self.index.delete_ref_doc(file_path)
            print(f"Deleted document: {file_path}")
            return
        
        # tiny delay to avoid reading half-written files
        time.sleep(0.1)

        # designed to read changed file safely without crashing watcher
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                new_content = f.read()
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            return

        # Build a doc with a stable id (so it can be referenced easily later) with metadata
        p = Path(file_path)
        doc = Document(
            text=new_content,
            doc_id=str(p),  
            metadata={
            "file_name": p.name,
            "folder_path": str(p.parent),
            "file_path": str(p),
            },
        )

        if type_of_change == "created":
            self.index.insert(doc)
            print(f"Created document: {file_path}")

        else: # else, it is a modification
            self.index.update_ref_doc(doc)
            print(f"Updated document: {file_path}")

    # Searches the index for the top three chunks of the query.
    def search(self, query):
        if self.index is None:
            return {"Error": "Index not initialized."}
        
        retriever = self.index.as_retriever(similarity_top_k=3)
        top_nodes = retriever.retrieve(query)

        if top_nodes:
            return top_nodes
        
        # Returns the top nodes or a "Not Found" message if no results are found.
        return {"Data": "Not Found"}