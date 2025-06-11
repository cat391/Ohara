from llama_index.core import VectorStoreIndex, Settings
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.obsidian import ObsidianReader


class VectorIndexer:
    def __init__(self, vault_path):
        self.vault_path = vault_path
        self.index = None
    
    def initialize_index(self):
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

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
        
        file_path = event.src_path # Define file_path which is the path of the file that was modified
        
        if type_of_change == "deleted":
            self.index.delete_ref_doc(file_path)
            print(f"Deleted document: {file_path}")
        elif type_of_change == "created":
            new_content = open(file_path, 'r').read()

            self.index.insert(Document(
                text=new_content,
                doc_id = file_path,
            ))
            print(f"Created document: {file_path}")
        else:
            # Watchdog events can trigger on directories, we want to ignore those
            if event.is_directory:
                return
            
            try:
                file_path = event.src_path
                new_content = open(file_path, 'r').read()

                self.index.update_ref_doc(Document(
                    text=new_content,
                    doc_id = file_path,
                ))
                print(f"Updated document: {file_path}")
            except FileNotFoundError:
                print(f"File not found: {file_path}")
            except IsADirectoryError:
                pass

    
    