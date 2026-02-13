# Recipe Transcriber - TikTok, Instagram & Web

Application web qui extrait automatiquement des recettes de cuisine depuis des vidéos TikTok/Instagram ou des sites de recettes. Elle télécharge la vidéo, transcrit l'audio via Whisper, puis utilise un LLM local (Ollama) pour structurer la recette.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 Docker Compose (TST-Net)                 │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │   Frontend   │  │   Backend    │  │    Whisper    │   │
│  │   Next.js    │  │   FastAPI    │  │   GPU Service │   │
│  │  :60802      │  │  :60801      │  │  :9000 (int.) │   │
│  └──────────────┘  └──────┬───────┘  └───────────────┘   │
│                           │                              │
└───────────────────────────┼──────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  Ollama (host)  │
                   │    :11434       │
                   └─────────────────┘
```

| Service    | Techno                          | Port  | Rôle                                    |
|------------|---------------------------------|-------|-----------------------------------------|
| Backend    | FastAPI (Python 3.12)           | 60801 | API, téléchargement, orchestration      |
| Frontend   | Next.js 15 / React 19 / Tailwind| 60802 | Interface utilisateur                   |
| Whisper    | OpenAI Whisper + CUDA 11.8      | 9000  | Transcription audio (GPU)               |
| Ollama     | gemma3:latest (configurable)    | 11434 | Extraction structurée de la recette     |

## Fonctionnalités

- Téléchargement de vidéos TikTok et Instagram (via yt-dlp)
- Scraping de sites de recettes (journaldesfemmes.fr, marmiton, etc.)
- Transcription audio par Whisper avec gestion GPU (chargement/déchargement du modèle)
- Extraction de recettes structurées (titre, ingrédients, étapes, temps, difficulté)
- File d'attente de jobs avec suivi de progression en temps réel
- Interface web glassmorphism avec copie en un clic

## Prérequis

- **Docker** & **Docker Compose**
- **GPU NVIDIA** avec [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- **Ollama** installé et lancé sur la machine hôte

```bash
# Vérifier que Ollama tourne
curl http://localhost:11434/api/tags

# Télécharger le modèle utilisé
ollama pull gemma3:latest
```

## Installation & Lancement

### 1. Cloner le projet

```bash
git clone <url-du-repo>
cd Recette_Tiktok_transcriber
```

### 2. Configurer l'environnement

Créer le fichier `Backend/.env` :

```env
ALLOWED_ORIGINS=["http://localhost"]
APP_CONFIG_TITLE="TikTok to recipes"
APP_CONFIG_DESCRITPION="Api qui converti un tiktok cuisine en recette utilisable"
APP_CONFIG_VERSION="0.1.0"
CORS_ALLOW_METHODS=["POST", "GET"]
WHISPER_MODEL="medium"
OLLAMA_MODEL_PRIMARY="gemma3:latest"
OLLAMA_BASE_URL="http://host.docker.internal:11434"
WHISPER_BASE_URL="http://whisper:9000"
```

### 3. Lancer avec Docker Compose

```bash
docker compose up --build
```

Au premier lancement, le service Whisper télécharge le modèle (~1.5 Go pour `medium`). Le healthcheck a un `start_period` de 120s pour laisser le temps au téléchargement.

### 4. Accéder à l'application

- **Interface web** : http://localhost:60802
- **API backend** : http://localhost:60801
- **Documentation API** : http://localhost:60801/docs

## Utilisation

1. Ouvrir http://localhost:60802
2. Se connecter
3. Coller l'URL d'une vidéo TikTok, Instagram ou d'un site de recettes
4. Cliquer sur "Transcrire"
5. Suivre la progression en temps réel
6. Copier la recette formatée

## API Endpoints

### Web UI

| Méthode  | Route                           | Description                    |
|----------|---------------------------------|--------------------------------|
| `POST`   | `/api/web/submit`               | Soumettre une URL              |
| `GET`    | `/api/web/job/{user_id}/{job_id}` | Statut d'un job              |
| `GET`    | `/api/web/jobs/{user_id}`       | Liste des jobs d'un utilisateur|
| `DELETE` | `/api/web/job/{user_id}/{job_id}` | Supprimer un job             |
| `GET`    | `/api/web/stats`                | Statistiques globales          |

### Direct API

| Méthode  | Route                | Description                       |
|----------|----------------------|-----------------------------------|
| `POST`   | `/api/sptotxt`       | Soumettre une vidéo (retourne job_id) |
| `GET`    | `/api/status/{job_id}` | Vérifier le statut d'un job     |
| `GET`    | `/api/health`        | Health check                      |

## Structure du projet

```
.
├── Backend/
│   ├── main.py                        # Point d'entrée FastAPI
│   ├── requirements.txt
│   ├── dockerfile.backend
│   ├── .env
│   ├── routers/
│   │   ├── health.py                  # Health check
│   │   ├── recipes.py                 # API directe
│   │   └── web.py                     # API pour le frontend
│   └── internals/
│       ├── core/
│       │   ├── Convertion/            # Transcription audio
│       │   ├── Downloading/           # Téléchargement vidéo/scraping
│       │   └── llm/                   # Client Ollama
│       └── Utils/                     # Config, extraction, formatage
├── Whisper/
│   ├── main.py                        # Service Whisper (FastAPI + GPU)
│   ├── requirements.txt
│   └── dockerfile.whisper
├── frontend/
│   ├── src/app/                       # Pages Next.js
│   ├── src/components/                # Composants React
│   ├── package.json
│   └── dockerfile.frontend
└── compose.yml                        # Orchestration Docker
```

## Pipeline de traitement

```
URL soumise
    │
    ├─ TikTok/Instagram ──► yt-dlp ──► Extraction audio (moviepy)
    │                                        │
    │                                        ▼
    │                                   Whisper (GPU)
    │                                        │
    │                                        ▼
    │                                   Transcription
    │                                        │
    ├─ Site de recettes ──► recipe_scrapers ──┤
    │                                        │
    │                                        ▼
    │                                  Ollama (LLM)
    │                                        │
    │                                        ▼
    └────────────────────────────── Recette structurée (JSON)
```

## Configuration GPU

Ce projet est configuré pour une **NVIDIA GeForce GTX 1060** (Pascal, sm_61) :
- Image Docker : `nvidia/cuda:11.8.0-runtime-ubuntu22.04`
- PyTorch : index `cu118` (les builds CUDA 12.x ne supportent pas sm_61)
- Le service Whisper gère le chargement/déchargement du modèle pour optimiser l'utilisation VRAM

Pour une GPU plus récente (Ampere, Ada Lovelace...), vous pouvez utiliser une image CUDA 12.x et l'index PyTorch correspondant.

## Stack technique

**Backend** : FastAPI, yt-dlp, moviepy, recipe_scrapers, BeautifulSoup4, requests

**Frontend** : Next.js 15, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Radix UI, Lucide Icons

**Whisper** : OpenAI Whisper, PyTorch (CUDA 11.8), FastAPI

**Infrastructure** : Docker Compose, NVIDIA Container Toolkit, Ollama
