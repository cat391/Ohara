from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.obsidian import ObsidianReader
from fastapi import FastAPI
# Remember to encrypt certain things for security purposes

# Define LlamaIndex settings to use local llm and not OpenAI
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")

# this disables all llms (including local), delete later
Settings.llm = None 

# Connect to Qdrant and create a database
client = QdrantClient(":memory:") # change memory, it is just for testing now
vector_store = QdrantVectorStore(client=client, collection_name="user_notes")

# Load documents using llama index 
documents = ObsidianReader("/Users/cole/Desktop/Obsidian Vaults/Computer Science").load_data()

# Builds the vector store index 
index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

# Configure FastAPI to enable search of the database
app = FastAPI()

@app.get("/search")

# Use indexer to find top three chunks of the query
async def search(q:str):
    retriever = index.as_retriever(similarity_top_k=3)
    top_nodes = retriever.retrieve(q)

    if top_nodes:
        return top_nodes
    
    return {"Data": "Not Found"}

