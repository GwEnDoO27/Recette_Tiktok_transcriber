"""
Whisper Transcription Service - GPU-enabled FastAPI micro-service.
Cold start: loads model on demand, unloads after transcription to free VRAM.
Asks Ollama to unload its model before loading Whisper to free GPU memory.
"""

import gc
import os
import tempfile
import threading
import time
import traceback
from contextlib import asynccontextmanager

import requests as req
import torch
import whisper  # type: ignore
from fastapi import FastAPI, File, HTTPException, UploadFile  # type: ignore


# Lock to serialize model load/unload and transcription
_model_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_size = os.getenv("WHISPER_MODEL", "medium")
    app.state.device = "cuda" if torch.cuda.is_available() else "cpu"
    app.state.fp16 = app.state.device == "cuda"
    app.state.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    print(f"Whisper service ready (cold start mode)")
    print(f"  Model: {app.state.model_size}")
    print(f"  Device: {app.state.device}")
    print(f"  Ollama URL: {app.state.ollama_url}")
    if app.state.device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"  GPU: {gpu_name} ({vram:.1f} GB VRAM)")
    print(f"  Model will be loaded on first request and unloaded after use.")

    yield


app = FastAPI(title="Whisper Transcription Service", lifespan=lifespan)


def _get_vram_free_mb():
    """Get free VRAM in MB."""
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info(0)
        return free / (1024**2)
    return 0


def _evict_ollama():
    """Ask Ollama to unload all models from VRAM (keep_alive=0)."""
    ollama_url = app.state.ollama_url
    print(f"  VRAM free before eviction: {_get_vram_free_mb():.0f} MB")

    try:
        # List loaded models
        resp = req.get(f"{ollama_url}/api/ps", timeout=5)
        print(f"  Ollama /api/ps response: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  Warning: Ollama /api/ps returned {resp.status_code}")
            return

        data = resp.json()
        models = data.get("models", [])
        print(f"  Ollama loaded models: {[m.get('name') for m in models]}")

        if not models:
            print(f"  No Ollama models loaded in VRAM.")
            return

        for m in models:
            name = m.get("name")
            if name:
                print(f"  Evicting Ollama model '{name}'...")
                evict_resp = req.post(
                    f"{ollama_url}/api/generate",
                    json={"model": name, "prompt": "", "keep_alive": 0},
                    timeout=30,
                )
                print(f"  Evict response: {evict_resp.status_code}")

        # Wait for Ollama to actually release VRAM
        for i in range(10):
            time.sleep(2)
            free_mb = _get_vram_free_mb()
            print(f"  VRAM free after {(i+1)*2}s: {free_mb:.0f} MB")
            if free_mb > 3000:  # Need at least 3 GB for large model
                print(f"  Sufficient VRAM available.")
                return

        print(f"  Warning: VRAM may still be insufficient.")

    except Exception as e:
        print(f"  Warning: Could not evict Ollama models: {e}")
        traceback.print_exc()


def _load_model():
    """Evict Ollama then load whisper model into VRAM."""
    if app.state.device == "cuda":
        _evict_ollama()
    print(f"  Loading Whisper model '{app.state.model_size}' on {app.state.device}...")
    model = whisper.load_model(app.state.model_size, device=app.state.device)
    print(f"  Model loaded.")
    return model


def _unload_model(model):
    """Unload model and free VRAM."""
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"  Model unloaded, VRAM freed.")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None):
    """
    Transcribe an audio file.
    Cold start: evicts Ollama, loads model, transcribes, then unloads.
    """
    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()

        with _model_lock:
            model = _load_model()
            try:
                result = model.transcribe(
                    tmp.name,
                    language=language,
                    task="transcribe",
                    verbose=False,
                    fp16=app.state.fp16,
                )
            finally:
                _unload_model(model)

        detected_language = result.get("language", "unknown")
        text = result["text"].strip()

        return {
            "text": text,
            "language": detected_language,
        }

    except Exception as e:
        print(f"  ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@app.get("/health")
async def health():
    """Health check endpoint."""
    info = {
        "status": "healthy",
        "model": app.state.model_size,
        "device": app.state.device,
        "mode": "cold_start",
    }
    if app.state.device == "cuda":
        info["gpu_name"] = torch.cuda.get_device_name(0)
    return info


@app.get("/")
async def root():
    return {
        "service": "Whisper Transcription Service",
        "model": app.state.model_size,
        "device": app.state.device,
        "mode": "cold_start",
    }
