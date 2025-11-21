import os

import whisper  # type: ignore
from moviepy import VideoFileClip  # type: ignore


def speak_to_text(path: str, model_size: str = "base"):
    """
    Transcribe video to text using OpenAI Whisper

    Args:
        path (str): Path to video file
        model_size (str): Whisper model size (tiny, base, small, medium, large)
            - tiny: fastest, least accurate (~1GB RAM)
            - base: fast, good accuracy (~1GB RAM) [DEFAULT]
            - small: balanced (~2GB RAM)
            - medium: accurate (~5GB RAM)
            - large: most accurate, slowest (~10GB RAM)

    Returns:
        str: Transcribed text
    """
    print(f"\n{'=' * 60}")
    print(f"WHISPER TRANSCRIPTION - Model: {model_size}")
    print(f"{'=' * 60}\n")

    def sanitized_name_to_wav(path: str):
        # Replace .mp4 extension with .wav and keep the full path
        return path.replace(".mp4", ".wav")

    # Extract audio from video
    print("Step 1/3: Extracting audio from video...")
    video = VideoFileClip(path)
    audio_file_sanitized_name = sanitized_name_to_wav(path)

    duration = video.duration
    print(f"  ✓ Video duration: {duration:.2f}s")

    video.audio.write_audiofile(audio_file_sanitized_name, logger=None)
    video.close()
    print(f"  ✓ Audio extracted: {audio_file_sanitized_name}\n")

    # Load Whisper model
    print(f"Step 2/3: Loading Whisper model '{model_size}'...")
    try:
        model = whisper.load_model(model_size)
        print("  ✓ Model loaded successfully\n")
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        return ""

    # Transcribe with Whisper
    print("Step 3/3: Transcribing audio (this may take a moment)...")
    try:
        # Whisper options:
        # - language: None for auto-detection, or specify like "fr", "en"
        # - task: "transcribe" or "translate" (translate converts to English)
        # - verbose: False to reduce output
        result = model.transcribe(
            audio_file_sanitized_name,
            language=None,  # Auto-detect language
            task="transcribe",
            verbose=False,
            fp16=False,  # Set to True if you have a CUDA GPU
        )

        detected_language = result.get("language", "unknown")
        print(f"  ✓ Detected language: {detected_language}")
        print("  ✓ Transcription complete\n")

        # Extract the full text
        transcribed_text = result["text"].strip()

        # Clean up audio file
        try:
            os.remove(audio_file_sanitized_name)
            print("  ✓ Cleaned up temporary file\n")
        except OSError as e:
            print(f"  ! Warning: Could not remove temporary file: {e}\n")

        # Print results
        print(f"{'=' * 60}")
        print("TRANSCRIPTION RESULT:")
        print(f"{'=' * 60}")
        print(transcribed_text)
        print(f"{'=' * 60}\n")

        # Optionally, print segments with timestamps
        if result.get("segments"):
            print("\nDETAILED SEGMENTS:")
            print(f"{'-' * 60}")
            for segment in result["segments"]:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"].strip()
                print(f"[{start:.2f}s - {end:.2f}s] {text}")
            print(f"{'-' * 60}\n")

        return transcribed_text

    except Exception as e:
        print(f"  ✗ Error during transcription: {e}")

        # Clean up on error
        try:
            if os.path.exists(audio_file_sanitized_name):
                os.remove(audio_file_sanitized_name)
        except OSError:
            pass

        return ""
