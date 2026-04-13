"""
tts.py -- Text-to-speech using Google Gemini TTS.

Converts a narration script to a WAV audio file using the Gemini TTS API
(gemini-2.5-pro-preview-tts by default). Voice and model are explicit
parameters, not env vars, so they appear in the substrait call fact payload
and contribute to manifest identity.

Environment variables:
    GOOGLE_API_KEY -- Required for real TTS; must be set in .env or environment.

Usage:
    from agent.tools.tts import generate_speech

    # Real TTS
    result = generate_speech(script="...", output_path="/path/to/narration.wav")

    # Mock (test runs -- no Gemini call, writes silent WAV)
    result = generate_speech(script="...", output_path="...", mock=True)
"""

from __future__ import annotations

import os
import wave
from pathlib import Path


def generate_speech(
    script: str,
    output_path: str,
    voice: str = "Vindemiatrix",
    model: str = "gemini-2.5-pro-preview-tts",
    mock: bool = False,
) -> dict:
    """
    Convert narration text to speech and save as a WAV file.

    Args:
        script:      Narration text (~140-160 words ~= ~60 seconds of speech).
        output_path: Absolute path to write the .wav file.
        voice:       Gemini voice name (default: Vindemiatrix).
        model:       Gemini TTS model ID.
        mock:        If True, write a silent 1-second WAV and skip Gemini.
                     Use this for test runs -- mock=True appears in the
                     substrait call fact so the run is distinguishable.

    Returns:
        {"status": "success", "path": str, "bytes": int, "duration_seconds": float}
        {"status": "success", ..., "mock": True}   -- when mock=True
        {"status": "error",   "error": str}
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if mock:
        silence = b"\x00\x00" * 24000  # 1 second, 16-bit mono silence at 24 kHz
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(silence)
        return {
            "status":           "success",
            "path":             str(out),
            "bytes":            len(silence),
            "duration_seconds": 1.0,
            "mock":             True,
        }

    try:
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {"status": "error", "error": "GOOGLE_API_KEY not set"}

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=script,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            ),
        )

        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Gemini returns 24 kHz, 16-bit mono PCM
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)

        return {
            "status":           "success",
            "path":             str(out),
            "bytes":            len(audio_data),
            "duration_seconds": round(len(audio_data) / (24000 * 2), 1),
        }

    except Exception as exc:
        return {"status": "error", "error": str(exc)}
