from llama_cpp import Llama
from pathlib import Path
# Model is phi-2.Q4_K_M.gguf

class LocalLLM:
    """
    LocalLLM class to handle local LLM operations using LlamaCpp.
    """

    def __init__(self, model_dir):
      self.llm = Llama(
        model_path=str(model_dir),
        n_gpu_layers=30,      # Balanced GPU offload
        n_threads=5,          # Reserve cores for system
        n_ctx=2048,           # Phi-2's max context
        verbose=False,
        use_mmap=True,       # mmap model file into memory
        use_mlock=True,
    )
    
      print("LocalLLM initialized successfully.")


    

    def _inner_node(self, node_obj):
        """Return the inner 'node' whether input is NodeWithScore or a dict or already a node."""
        if hasattr(node_obj, "node"):
            return node_obj.node
        if isinstance(node_obj, dict) and "node" in node_obj:
            return node_obj["node"]
        return node_obj

    def _get_metadata(self, obj):
        """Extract a metadata dict from various shapes."""
        if hasattr(obj, "metadata"):
            md = getattr(obj, "metadata", None) or {}
            if isinstance(md, dict):
                return md

        if isinstance(obj, dict):
            md = obj.get("metadata") or {}
            if isinstance(md, dict):
                return md

        return {}

    def _extract_source_info(self, node_obj):
        """
        Get just the file_name and path from a node object.
        Tries node.metadata first, then falls back to SOURCE relationship metadata.
        """
        node = self._inner_node(node_obj)
        md = self._get_metadata(node)

        file_name = md.get("file_name") or md.get("note_name")
        folder_path = md.get("folder_path") or md.get("path")

        # Fallback: try relationship SOURCE metadata if missing
        if (not file_name or not folder_path):
            rels = getattr(node, "relationships", None)
            if rels is None and isinstance(node, dict):
                rels = node.get("relationships")

            if isinstance(rels, dict):
                for _, rinfo in rels.items():
                    rmd = None
                    if hasattr(rinfo, "metadata"):
                        rmd = getattr(rinfo, "metadata")
                    elif isinstance(rinfo, dict):
                        rmd = rinfo.get("metadata")
                    if isinstance(rmd, dict):
                        file_name = file_name or rmd.get("file_name") or rmd.get("note_name")
                        folder_path = folder_path or rmd.get("folder_path") or rmd.get("path")
                        if file_name and folder_path:
                            break

        # If note_name is present but no extension, add .md (optional)
        if file_name and "." not in file_name and md.get("file_name") is None:
            file_name = f"{file_name}.md"

        full_path = None
        if folder_path and file_name:
            try:
                full_path = str(Path(folder_path) / file_name)
            except Exception:
                # keep None if something odd happens with paths
                full_path = None

        if not file_name and not full_path:
            return None

        return {"file_name": file_name, "path": full_path}

    # helper to get score of node
    def _get_score(self, node_obj):
        if hasattr(node_obj, "score"):
            return float(getattr(node_obj, "score") or 0.0)
        if isinstance(node_obj, dict):
            return float(node_obj.get("score") or node_obj.get("similarity") or 0.0)
        return 0.0

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
            temperature=0.4,
            stop = ["\n\n", "###", "[2.", "## ", "<|endoftext|>"]
        )
    
        # Changed this line:
        answer_text = resp["choices"][0]["text"].strip()  # Now accesses "text" instead of "message"

        # return only highest-scoring node and return one source
        sources: List[Dict[str, Optional[str]]] = []
        if nodes:
            best_node = max(nodes, key=self._get_score)
            info = self._extract_source_info(best_node)
            if info:
                sources.append(info)


        return {
            "answer": answer_text,
            "sources": sources, 
        }