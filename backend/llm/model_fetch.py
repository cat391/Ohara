import os
import sys
from pathlib import Path

# Where the models live on Hugging Face
LLM_REPO = "LiquidAI/LFM2-1.2B-RAG-GGUF"
LLM_FILENAME = "LFM2-1.2B-RAG-Q4_K_M.gguf"
EMBED_REPO = "BAAI/bge-small-en"

# Legacy filename used when the GGUF was checked into backend/ directly
_LEGACY_LLM_FILENAME = "LiquidAI_LFM2-1.2B-RAG-Q4_K_M.gguf"


def app_data_dir() -> Path:
    """Writable per-user data dir (models + qdrant index live here).

    A frozen (PyInstaller) binary unpacks to a wipe-on-exit temp dir and the
    .app bundle is read-only, so nothing writable can live next to the code.
    """
    override = os.environ.get("OHARA_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "dev.cole.ohara"
    return Path.home() / ".ohara"


def _repo_local_models():
    """When running from source with models already in backend/, use them.

    Keeps the dev loop fully offline and avoids re-downloading weights that
    are already sitting in the repo checkout.
    """
    if getattr(sys, "frozen", False):
        return None
    base = Path(__file__).resolve().parents[1]
    llm_path = base / _LEGACY_LLM_FILENAME
    embed_dir = base / "models" / "bge-small-en"
    if llm_path.exists() and (embed_dir / "config.json").exists():
        return llm_path, embed_dir
    return None


def _download_gguf(dest: Path, progress_cb=None):
    """Stream the GGUF from Hugging Face with resume + progress.

    Hand-rolled instead of hf_hub_download so we get a byte-level progress
    callback (hf's internal tqdm is not exposed). Resumes partial downloads
    via Range requests and renames atomically on completion.
    """
    import requests

    url = f"https://huggingface.co/{LLM_REPO}/resolve/main/{LLM_FILENAME}"
    part = dest.with_suffix(dest.suffix + ".part")

    resume_from = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={resume_from}-"} if resume_from else {}

    with requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True) as r:
        if resume_from and r.status_code == 200:
            # Server ignored the Range header; start over
            resume_from = 0
        r.raise_for_status()

        content_length = int(r.headers.get("content-length", 0))
        total = resume_from + content_length if content_length else None
        done = resume_from

        mode = "ab" if resume_from else "wb"
        with open(part, mode) as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    progress_cb(done / total, LLM_FILENAME)

    if total is not None and part.stat().st_size != total:
        raise RuntimeError(
            f"Download of {LLM_FILENAME} incomplete "
            f"({part.stat().st_size}/{total} bytes)"
        )
    part.rename(dest)


def _download_embeddings(embed_dir: Path):
    """Fetch the bge-small-en snapshot (small; no byte-level progress needed)."""
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=EMBED_REPO,
        local_dir=embed_dir,
        # safetensors is all sentence-transformers needs; skip the duplicate weights
        ignore_patterns=["pytorch_model.bin", "*.onnx", "*.h5"],
    )


def ensure_models(progress_cb=None):
    """Return (llm_path, embed_dir), downloading anything missing.

    progress_cb(fraction, filename) is called during the LLM download.
    No network is touched when everything is already on disk.
    """
    local = _repo_local_models()
    if local:
        return local

    models_dir = app_data_dir() / "models"
    llm_path = models_dir / LLM_FILENAME
    embed_dir = models_dir / "bge-small-en"

    models_dir.mkdir(parents=True, exist_ok=True)
    if not llm_path.exists():
        _download_gguf(llm_path, progress_cb)
    if not (embed_dir / "config.json").exists():
        _download_embeddings(embed_dir)
    return llm_path, embed_dir
