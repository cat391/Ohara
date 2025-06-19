from llama_cpp import Llama
# Model is mistral-7b-instruct-v0.1.Q4_K_M.gguf/phi-2.Q4_K_M.gguf

class LocalLLM:
    """
    LocalLLM class to handle local LLM operations using LlamaCpp.
    """

    def __init__(self):
      self.llm = Llama(
        model_path="phi-2.Q4_K_M.gguf",
        n_gpu_layers=25,      # Balanced GPU offload
        n_threads=5,          # Reserve cores for system
        n_ctx=2048,           # Phi-2's max context
        verbose=False
        )
    
      print("LocalLLM initialized successfully.")


    # Function to just strip the node text
    def _retrieve_node_text(self, node_obj):
       # If the node_obj is a NodeWithScore object, extract the text
        if hasattr(node_obj, "get_content"):
            return node_obj.get_content()

        # Handle both cases where the node_obj is a dict 
        if isinstance(node_obj, dict):
            # (a) full dict with "node" & "score"
            if "node" in node_obj and "text" in node_obj["node"]:
                return node_obj["node"]["text"]
            # (b) already the inner "node" part
            if "text" in node_obj:
                return node_obj["text"]

        raise ValueError("Unrecognised node object type")
    
    def answer_question(self, nodes, query):

        chunk_texts = []
        # Retrieve text from top three nodes
        for n in nodes:
            try:
                print(f"Processing node: {n}")
                chunk_texts.append(self._retrieve_node_text(n))
            except ValueError:
                # Skip nodes we can’t decode instead of crashing the whole call
                continue
        


        context = "\n".join(chunk_texts[:3])
        prompt = f"""### Instruction:
        Answer the following question concisely using ONLY the provided context.

        ### Context:
        {context}

        ### Question:
        {query}

        ### Rules:
        - Do not explain unless asked.
        - Do not generate examples unless asked.
        - Answer in 1-2 sentences maximum.

        ### Answer:"""  
    
        resp = self.llm.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=0.3,
            stop = ["\n\n", "###", "[2.", "## ", "<|endoftext|>"]
        )
    
        # Changed this line:
        return resp["choices"][0]["text"].strip()  # Now accesses "text" instead of "message"