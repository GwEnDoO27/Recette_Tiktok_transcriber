import os

from moviepy import VideoFileClip  # type: ignore

from internals.core.Convertion.whisper_client import WhisperClient


def speak_to_text(path: str, model_size: str = "base"):
    """
    Transcribe video to text using external Whisper service.

    Args:
        path (str): Path to video file
        model_size (str): Kept for backward compatibility (unused,
            the whisper service controls its own model)

    Returns:
        str: Transcribed text
    """
    whisper_url = os.getenv("WHISPER_BASE_URL", "http://localhost:9000")

    print(f"\n{'=' * 60}")
    print(f"WHISPER TRANSCRIPTION - via {whisper_url}")
    print(f"{'=' * 60}\n")

    # Step 1: Extract audio from video
    audio_path = path.replace(".mp4", ".wav")
    print("Step 1/3: Extracting audio from video...")
    video = VideoFileClip(path)
    duration = video.duration
    print(f"  ✓ Video duration: {duration:.2f}s")
    video.audio.write_audiofile(audio_path, logger=None)
    video.close()
    print(f"  ✓ Audio extracted: {audio_path}\n")

    # Step 2: Connect to Whisper service
    print("Step 2/3: Connecting to Whisper service...")
    client = WhisperClient(base_url=whisper_url)
    if not client.check_connection():
        print(f"  ✗ Cannot connect to Whisper at {whisper_url}")
        _cleanup(audio_path)
        return ""
    print("  ✓ Connected successfully\n")

    # Step 3: Transcribe via external service
    print("Step 3/3: Transcribing audio (this may take a moment)...")
    text = client.transcribe(audio_path)
    _cleanup(audio_path)

    if text:
        print("  ✓ Transcription complete\n")
        print(f"{'=' * 60}")
        print("TRANSCRIPTION RESULT:")
        print(f"{'=' * 60}")
        print(text)
        print(f"{'=' * 60}\n")
        return text
    else:
        print("  ✗ Transcription failed\n")
        return ""


def _cleanup(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
            print("  ✓ Cleaned up temporary file")
    except OSError as e:
        print(f"  ! Warning: Could not remove temporary file: {e}")
