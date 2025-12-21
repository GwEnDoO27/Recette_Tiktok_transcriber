import asyncio
import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException  # type: ignore
from fastapi.responses import StreamingResponse
from internals.core.Convertion.speak_to_text import speak_to_text
from internals.core.Downloading.downloader import find_the_downloader
from internals.Utils.environnement import get_environment
from internals.Utils.extract import extract_recipes
from internals.Utils.formatter import format_recipe_for_display
from pydantic import BaseModel  # type: ignore

transform_tiktok = APIRouter()

# Gestion de la concurrence multi-utilisateurs
MAX_CONCURRENT_JOBS = 2  # Limite à 2 traitements simultanés
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
active_jobs_lock = asyncio.Lock()
active_jobs_count = 0

# Stockage des jobs en mémoire
jobs: Dict[str, Any] = {}


class VideoRequest(BaseModel):
    link: str


def process_video_task(job_id: str, link: str):
    """
    Tâche de traitement vidéo en arrière-plan.
    Met à jour le dictionnaire jobs avec le statut et le résultat.
    """
    try:
        print(f"Starting job {job_id} for link: {link}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["current_step"] = "Configuration..."

        # Configuration
        whisper_model, ollama_model_primary, ollama_url = get_environment()

        # Téléchargement
        jobs[job_id]["current_step"] = "Téléchargement de la vidéo..."
        path, metadata = find_the_downloader(link)

        if not path:
            jobs[job_id] = {
                "status": "failed",
                "error": "Impossible de télécharger la vidéo. Vérifiez l'URL."
            }
            return

        # Transcription
        jobs[job_id]["current_step"] = "Transcription de l'audio (1-2 min)..."
        transcription = speak_to_text(path, model_size=whisper_model)

        if not transcription:
            jobs[job_id] = {
                "status": "failed",
                "error": "Échec de la transcription."
            }
            return

        # Extraction
        jobs[job_id]["current_step"] = "Extraction de la recette..."
        recipe = extract_recipes(ollama_url, ollama_model_primary, transcription, metadata)

        if not recipe:
            jobs[job_id] = {
                "status": "failed",
                "error": "Échec de l'extraction de la recette."
            }
            return

        # Formatage du texte
        formatted_text = format_recipe_for_display(recipe, link)

        # Succès
        jobs[job_id] = {
            "status": "completed",
            "result": {
                "recipe": recipe,
                "formatted_text": formatted_text
            }
        }
        print(f"Job {job_id} completed successfully")

    except Exception as e:
        error_msg = f"Erreur: {str(e)}"
        print(f"Error in job {job_id}: {error_msg}")
        jobs[job_id] = {
            "status": "failed",
            "error": error_msg
        }


@transform_tiktok.post("/sptotxt")
async def submit_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """
    Soumet une vidéo pour traitement en arrière-plan.
    Retourne immédiatement un job_id.
    Compatible avec le timeout court d'Apple Shortcuts.
    """
    global active_jobs_count

    # Vérifier si des slots sont disponibles
    async with active_jobs_lock:
        if active_jobs_count >= MAX_CONCURRENT_JOBS:
            raise HTTPException(
                status_code=503,
                detail="Serveur occupé, réessayez dans 30 secondes"
            )

        active_jobs_count += 1

    # Créer un job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "current_step": "En attente..."
    }

    # Lancer le traitement en arrière-plan
    async def wrapped_task():
        try:
            await asyncio.to_thread(process_video_task, job_id, request.link)
        finally:
            async with active_jobs_lock:
                global active_jobs_count
                active_jobs_count -= 1

    background_tasks.add_task(wrapped_task)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Traitement lancé. Utilisez GET /status/{job_id} pour vérifier l'avancement."
    }


@transform_tiktok.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Récupère le statut et le résultat d'un job.
    Utilisé par Apple Shortcuts pour faire du polling.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job introuvable")

    return jobs[job_id]


# Garder l'endpoint SSE pour compatibilité (optionnel)
async def process_video_stream(link: str):
    """
    Générateur asynchrone qui traite la vidéo et envoie des événements SSE.
    ATTENTION: Ne fonctionne pas avec le timeout court d'Apple Shortcuts.
    """
    global active_jobs_count

    try:
        async with active_jobs_lock:
            if active_jobs_count >= MAX_CONCURRENT_JOBS:
                yield f"event: error\ndata: {json.dumps({'error': 'Serveur occupé, réessayez dans 30 secondes', 'code': 'server_busy'})}\n\n"
                return

        async with job_semaphore:
            async with active_jobs_lock:
                active_jobs_count += 1
            job_id = str(uuid.uuid4())

            try:
                yield f"event: progress\ndata: {json.dumps({'step': 'init', 'message': 'Démarrage du traitement...', 'job_id': job_id})}\n\n"
                await asyncio.sleep(0.1)

                yield f"event: progress\ndata: {json.dumps({'step': 'config', 'message': 'Configuration de l\'environnement...'})}\n\n"
                whisper_model, ollama_model_primary, ollama_url = get_environment()

                yield f"event: progress\ndata: {json.dumps({'step': 'download', 'message': 'Téléchargement de la vidéo...'})}\n\n"
                path, metadata = await asyncio.to_thread(find_the_downloader, link)

                if not path:
                    yield f"event: error\ndata: {json.dumps({'error': 'Impossible de télécharger la vidéo. Vérifiez l\'URL.', 'code': 'download_failed'})}\n\n"
                    return

                yield f"event: progress\ndata: {json.dumps({'step': 'transcribe', 'message': 'Transcription de l\'audio (cela peut prendre 1-2 minutes)...'})}\n\n"
                transcription = await asyncio.to_thread(speak_to_text, path, whisper_model)

                if not transcription:
                    yield f"event: error\ndata: {json.dumps({'error': 'Échec de la transcription.', 'code': 'transcription_failed'})}\n\n"
                    return

                yield f"event: progress\ndata: {json.dumps({'step': 'extract', 'message': 'Extraction de la recette...'})}\n\n"
                recipe = await asyncio.to_thread(extract_recipes, ollama_url, ollama_model_primary, transcription, metadata)

                if not recipe:
                    yield f"event: error\ndata: {json.dumps({'error': 'Échec de l\'extraction de la recette.', 'code': 'extraction_failed'})}\n\n"
                    return

                # Formatage du texte
                formatted_text = format_recipe_for_display(recipe, link)

                yield f"event: result\ndata: {json.dumps({'recipe': recipe, 'formatted_text': formatted_text, 'job_id': job_id})}\n\n"
                print(f"Job {job_id} completed successfully for link: {link}")

            except ValueError as e:
                yield f"event: error\ndata: {json.dumps({'error': f'URL invalide: {str(e)}', 'code': 'invalid_url'})}\n\n"
            except Exception as e:
                error_msg = f"Erreur: {str(e)}"
                print(f"Error in job {job_id}: {error_msg}")
                yield f"event: error\ndata: {json.dumps({'error': error_msg, 'code': 'unexpected_error'})}\n\n"
            finally:
                async with active_jobs_lock:
                    active_jobs_count -= 1

    except Exception as e:
        print(f"Fatal error in stream: {str(e)}")
        yield f"event: error\ndata: {json.dumps({'error': 'Erreur critique du serveur', 'code': 'fatal_error'})}\n\n"


@transform_tiktok.post("/sptotxt/stream")
async def process_video_endpoint(request: VideoRequest):
    """
    Endpoint SSE (NE PAS UTILISER avec Apple Shortcuts à cause du timeout).
    Préférez /sptotxt + polling /status/{job_id}
    """
    return StreamingResponse(
        process_video_stream(request.link),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@transform_tiktok.get("/health")
async def health_check():
    """
    Endpoint de santé pour vérifier l'état du serveur.
    """
    return {
        "status": "healthy",
        "active_jobs": active_jobs_count,
        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
        "available_slots": MAX_CONCURRENT_JOBS - active_jobs_count
    }
