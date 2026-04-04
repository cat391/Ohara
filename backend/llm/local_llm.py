from llama_cpp import Llama
from pathlib import Path
from typing import List, Dict, Optional
# Model is Phi-3.5-mini-instruct-Q4_K_M.gguf

class LocalLLM:
    """
    LocalLLM class to handle local LLM operations using LlamaCpp.
    """

    def __init__(self, model_dir):
        self.llm = Llama(
            model_path=str(model_dir),
            n_gpu_layers=30,
            n_threads=5,
            n_ctx=4096,  # Phi-3.5 supports larger context
            verbose=False,
            use_mmap=True,
            use_mlock=True,
        )
      
        

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
        # Fallback: fills in missing file name or folder path 
        fp = md.get("file_path")
        if fp and (not file_name or not folder_path):
            p = Path(fp)
            file_name = file_name or p.name
            folder_path = folder_path or str(p.parent)

        ######################### DEBUGGING #########################
        print(f"Extracting source info: file_name={file_name}, folder_path={folder_path}, node={node}")
        ######################### DEBUGGING #########################
        
        # If it's still missing, try to use rec_doc_id
        if (not file_name or not folder_path):
            rdid = getattr(node, "ref_doc_id", None)
            if rdid is None and isinstance(node, dict):
                rdid = node.get("ref_doc_id")
            if rdid:
                p = Path(str(rdid))
                file_name = file_name or p.name
                folder_path = folder_path or str(p.parent)


        # Final fallback, try relationship SOURCE metadata
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
    
    def _best_score(self, nodes):
        try:
            return max(self._get_score(n) for n in nodes) if nodes else 0.0
        except Exception:
            return 0.0

    def _clean_answer(self, text):
        """Clean markdown artifacts from LLM output."""
        import re
        # Remove bold **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        # Remove italics *text* or _text_
        text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'\1', text)
        text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
        # Remove stray underscores at word boundaries
        text = re.sub(r'(\w)_\s', r'\1 ', text)
        text = re.sub(r'\s_(\w)', r' \1', text)
        # Remove inline code backticks
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Collapse multiple spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def answer_question(self, nodes, query):
        best_score = self._best_score(nodes)
        print(f"[DEBUG] Best similarity score: {best_score:.3f}")

        if best_score < 0.80:  
            return {"answer": "I don't have enough information in the provided vault to answer.", "sources": None}

        chunk_texts = []
        # Retrieve text from top three nodes
        for n in nodes:
            try:
                print(f"Processing node: {n}")
                chunk_texts.append(self._retrieve_node_text(n))
            except ValueError:
                # Skip nodes we can’t decode instead of crashing the whole call
                continue
        


        context = "\n".join(chunk_texts[:5])
        prompt = f"""<|user|>
Answer the question using ONLY information from the context below.
If the context does not contain the answer, respond: "I don't have information about that in your notes."

Context:
{context}

Question:
{query}

Rules:
- Use ONLY facts from the context. Do not use outside knowledge.
- If the context doesn't answer the question, say "I don't have information about that in your notes."
- Answer in 1-2 sentences maximum.
- Do not explain or give examples unless asked.
<|end|>
<|assistant|>"""  
    
        resp = self.llm.create_completion(
            prompt=prompt,
            max_tokens=100,
            temperature=0.4,
            stop=["<|end|>", "<|user|>", "<|endoftext|>", "\n\n"]
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

        # Clean markdown artifacts
        answer_text = self._clean_answer(answer_text)

        # Strip obsidian-style [[wikilinks]]
        if "[[" in answer_text and "]]" in answer_text:
            import re
            answer_text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", answer_text)  # [[link|display]] -> display
            answer_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", answer_text)  # [[link]] -> link


        return {
            "answer": answer_text,
            "sources": sources, 
        }