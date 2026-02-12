"""
Router pour l'interface web TikTok/Instagram to Recipe.
Gestion des requêtes multiples avec UID unique par session.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from internals.core.Convertion.speak_to_text import speak_to_text
from internals.core.Downloading.downloader import find_the_downloader
from internals.Utils.environnement import get_environment
from internals.Utils.extract import extract_recipes
from internals.Utils.formatter import format_recipe_for_display

web_router = APIRouter()

# Configuration
MAX_CONCURRENT_JOBS = 3
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
active_jobs_lock = asyncio.Lock()
active_jobs_count = 0

# Stockage des jobs en memoire (par user_id)
# Structure: { user_id: { job_id: job_data } }
user_jobs: Dict[str, Dict[str, Any]] = {}


class WebVideoRequest(BaseModel):
    """Requete pour soumettre une video."""
    url: str = Field(..., description="URL de la video TikTok/Instagram")
    user_id: Optional[str] = Field(None, description="ID utilisateur pour regrouper les jobs")


class JobResponse(BaseModel):
    """Reponse apres soumission d'un job."""
    job_id: str
    user_id: str
    status: str
    message: str
    created_at: str


def get_or_create_user_id(user_id: Optional[str]) -> str:
    """Genere un user_id si non fourni."""
    if user_id and user_id in user_jobs:
        return user_id
    new_id = str(uuid.uuid4())[:8]
    user_jobs[new_id] = {}
    return new_id


def process_web_video_task(user_id: str, job_id: str, url: str):
    """
    Tache de traitement video en arriere-plan.
    Met a jour le dictionnaire user_jobs avec le statut et le resultat.
    """
    try:
        print(f"[Web] Starting job {job_id} for user {user_id}, URL: {url}")
        user_jobs[user_id][job_id]["status"] = "processing"
        user_jobs[user_id][job_id]["current_step"] = "Configuration..."
        user_jobs[user_id][job_id]["progress"] = 10

        # Configuration
        whisper_model, ollama_model_primary, ollama_url = get_environment()

        # Telechargement ou extraction depuis un site web
        user_jobs[user_id][job_id]["current_step"] = "Telechargement de la video..."
        user_jobs[user_id][job_id]["progress"] = 20
        path, metadata = find_the_downloader(url)

        if not path:
            user_jobs[user_id][job_id].update({
                "status": "failed",
                "error": "Impossible de telecharger la video. Verifiez l'URL.",
                "progress": 0,
                "completed_at": datetime.now().isoformat()
            })
            return

        # Verifier si c'est un dictionnaire (site web) ou un chemin de fichier (video)
        if isinstance(path, dict):
            # C'est une recette extraite d'un site web
            user_jobs[user_id][job_id]["current_step"] = "Formatage de la recette..."
            user_jobs[user_id][job_id]["progress"] = 80

            instructions = path.get("instruction", "Instructions non disponibles")
            if isinstance(instructions, str):
                steps = [step.strip() for step in instructions.split('\n') if step.strip()]
            else:
                steps = instructions

            ingredients = path.get("ingredients", [])
            if not isinstance(ingredients, list):
                ingredients = []

            recipe = {
                "title": path.get("title", "Recette sans titre"),
                "ingredients": ingredients,
                "steps": steps,
                "source": "website"
            }
            formatted_text = format_recipe_for_display(recipe, url)
        else:
            # C'est une video - proceder a la transcription
            user_jobs[user_id][job_id]["current_step"] = "Transcription audio..."
            user_jobs[user_id][job_id]["progress"] = 40
            transcription = speak_to_text(path, model_size=whisper_model)

            if not transcription:
                user_jobs[user_id][job_id].update({
                    "status": "failed",
                    "error": "Echec de la transcription audio.",
                    "progress": 0,
                    "completed_at": datetime.now().isoformat()
                })
                return

            # Extraction avec LLM
            user_jobs[user_id][job_id]["current_step"] = "Extraction de la recette..."
            user_jobs[user_id][job_id]["progress"] = 70
            recipe = extract_recipes(ollama_url, ollama_model_primary, transcription, metadata)

            if not recipe:
                user_jobs[user_id][job_id].update({
                    "status": "failed",
                    "error": "Echec de l'extraction de la recette.",
                    "progress": 0,
                    "completed_at": datetime.now().isoformat()
                })
                return

            formatted_text = format_recipe_for_display(recipe, url)

        # Succes
        user_jobs[user_id][job_id].update({
            "status": "completed",
            "progress": 100,
            "current_step": "Termine",
            "completed_at": datetime.now().isoformat(),
            "result": {
                "recipe": recipe,
                "formatted_text": formatted_text
            }
        })
        print(f"[Web] Job {job_id} completed successfully for user {user_id}")

    except Exception as e:
        error_msg = f"Erreur: {str(e)}"
        print(f"[Web] Error in job {job_id} for user {user_id}: {error_msg}")
        user_jobs[user_id][job_id].update({
            "status": "failed",
            "error": error_msg,
            "progress": 0,
            "completed_at": datetime.now().isoformat()
        })


@web_router.post("/submit", response_model=JobResponse)
async def submit_video(request: WebVideoRequest, background_tasks: BackgroundTasks):
    """
    Soumet une video pour traitement.
    Retourne immediatement un job_id et user_id pour suivi.
    """
    global active_jobs_count

    # Verifier les slots disponibles
    async with active_jobs_lock:
        if active_jobs_count >= MAX_CONCURRENT_JOBS:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Serveur occupe",
                    "message": "Trop de requetes en cours. Reessayez dans quelques secondes.",
                    "retry_after": 10
                }
            )
        active_jobs_count += 1

    # Gerer user_id
    user_id = get_or_create_user_id(request.user_id)
    if user_id not in user_jobs:
        user_jobs[user_id] = {}

    # Creer le job
    job_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    user_jobs[user_id][job_id] = {
        "status": "pending",
        "current_step": "En attente...",
        "progress": 0,
        "url": request.url,
        "created_at": created_at,
        "completed_at": None,
        "result": None,
        "error": None
    }

    # Lancer le traitement en arriere-plan
    async def wrapped_task():
        try:
            await asyncio.to_thread(process_web_video_task, user_id, job_id, request.url)
        finally:
            async with active_jobs_lock:
                global active_jobs_count
                active_jobs_count -= 1

    background_tasks.add_task(wrapped_task)

    return JobResponse(
        job_id=job_id,
        user_id=user_id,
        status="pending",
        message="Traitement lance avec succes.",
        created_at=created_at
    )


@web_router.get("/job/{user_id}/{job_id}")
async def get_job_status(user_id: str, job_id: str):
    """
    Recupere le statut d'un job specifique.
    """
    if user_id not in user_jobs:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if job_id not in user_jobs[user_id]:
        raise HTTPException(status_code=404, detail="Job introuvable")

    return user_jobs[user_id][job_id]


@web_router.get("/jobs/{user_id}")
async def get_user_jobs(user_id: str):
    """
    Liste tous les jobs d'un utilisateur.
    """
    if user_id not in user_jobs:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    jobs_list = []
    for job_id, job_data in user_jobs[user_id].items():
        jobs_list.append({
            "job_id": job_id,
            **job_data
        })

    # Trier par date de creation (plus recent en premier)
    jobs_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "user_id": user_id,
        "total_jobs": len(jobs_list),
        "jobs": jobs_list
    }


@web_router.delete("/job/{user_id}/{job_id}")
async def delete_job(user_id: str, job_id: str):
    """
    Supprime un job termine ou echoue.
    """
    if user_id not in user_jobs:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if job_id not in user_jobs[user_id]:
        raise HTTPException(status_code=404, detail="Job introuvable")

    job = user_jobs[user_id][job_id]
    if job["status"] in ["pending", "processing"]:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un job en cours de traitement"
        )

    del user_jobs[user_id][job_id]
    return {"message": "Job supprime avec succes", "job_id": job_id}


@web_router.delete("/jobs/{user_id}")
async def clear_user_jobs(user_id: str, completed_only: bool = True):
    """
    Supprime les jobs d'un utilisateur.
    Par defaut, supprime uniquement les jobs termines.
    """
    if user_id not in user_jobs:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    deleted_count = 0
    jobs_to_delete = []

    for job_id, job_data in user_jobs[user_id].items():
        if completed_only:
            if job_data["status"] in ["completed", "failed"]:
                jobs_to_delete.append(job_id)
        else:
            if job_data["status"] not in ["pending", "processing"]:
                jobs_to_delete.append(job_id)

    for job_id in jobs_to_delete:
        del user_jobs[user_id][job_id]
        deleted_count += 1

    return {
        "message": f"{deleted_count} job(s) supprime(s)",
        "user_id": user_id,
        "remaining_jobs": len(user_jobs[user_id])
    }


@web_router.get("/stats")
async def get_stats():
    """
    Statistiques globales du service.
    """
    total_users = len(user_jobs)
    total_jobs = sum(len(jobs) for jobs in user_jobs.values())

    status_counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for user_data in user_jobs.values():
        for job_data in user_data.values():
            status = job_data.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1

    return {
        "active_jobs": active_jobs_count,
        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
        "available_slots": MAX_CONCURRENT_JOBS - active_jobs_count,
        "total_users": total_users,
        "total_jobs": total_jobs,
        "jobs_by_status": status_counts
    }
