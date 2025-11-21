from fastapi import APIRouter, HTTPException, BackgroundTasks  # type: ignore
from pydantic import BaseModel
import uuid
from typing import Dict, Any

from internals.core.Convertion.speak_to_text import speak_to_text
from internals.core.Downloading.downloader import TikTokDownloader
from internals.Utils.environnement import get_environment
from internals.Utils.extract import extract_recipes

transform_tiktok = APIRouter()

# In-memory job storage
# Structure: { "job_id": { "status": "pending" | "completed" | "failed", "result": ..., "error": ... } }
jobs: Dict[str, Any] = {}


class VideoRequest(BaseModel):
    link: str


def process_video_task(job_id: str, link: str):
    """
    Background task to process the video.
    Updates the global jobs dictionary with status and result.
    """
    try:
        print(f"Starting job {job_id} for link: {link}")
        
        try:
            whisper_model, ollama_model_primary, ollama_url = get_environment()
        except Exception as e:
            error_msg = f"Erreur configuration: {str(e)}"
            print(error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            return

        path = None
        try:
            downloader = TikTokDownloader()
            path = downloader.download_video(link)
        except Exception as e:
            error_msg = f"Erreur téléchargement: {str(e)}"
            print(error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            return

        if not path:
            error_msg = "Impossible de télécharger la vidéo. Vérifiez l'URL."
            print(error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            return

        transcription = None
        try:
            transcription = speak_to_text(path, model_size=whisper_model)
            if not transcription:
                error_msg = "Échec de la transcription."
                print(error_msg)
                jobs[job_id] = {"status": "failed", "error": error_msg}
                return
        except Exception as e:
            error_msg = f"Erreur transcription: {str(e)}"
            print(error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            return

        try:
            recipe = extract_recipes(ollama_url, ollama_model_primary, transcription)
            if recipe:
                jobs[job_id] = {"status": "completed", "result": {"recipe": recipe}}
                print(f"Job {job_id} completed successfully.")
            else:
                error_msg = "Échec de l'extraction de la recette."
                print(error_msg)
                jobs[job_id] = {"status": "failed", "error": error_msg}
        except Exception as e:
            error_msg = f"Erreur extraction recette: {str(e)}"
            print(error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}

    except Exception as e:
        error_msg = f"Erreur inattendue: {str(e)}"
        print(error_msg)
        jobs[job_id] = {"status": "failed", "error": error_msg}


@transform_tiktok.post("/sptotxt")
async def Trad_Tiktok(request: VideoRequest, background_tasks: BackgroundTasks):
    """
    Starts the video processing job in the background.
    Returns a job_id immediately.
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    
    background_tasks.add_task(process_video_task, job_id, request.link)
    
    return {"job_id": job_id, "status": "pending"}


@transform_tiktok.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns the status and result of a job.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]
