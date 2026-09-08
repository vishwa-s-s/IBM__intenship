import os
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")

# Mapping of voice names to Voice IDs (Some default voices)
VOICE_MAP = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Clyde": "2EiwWnXFnvU5JabPnv8n",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Dave": "CYw3kZ02Hs0563khs1Fj",
    "Fin": "D38z5RcWu1voky8WS1ja"
}

def get_client():
    if not api_key:
        raise Exception("ElevenLabs API key is missing. Please set ELEVENLABS_API_KEY in your .env file.")
    return ElevenLabs(api_key=api_key)

def generate_audio(text: str, voice_id: str) -> bytes:
    """
    Generates audio for the given text using the specified ElevenLabs voice_id.
    """
    client = get_client()
    try:
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2", # Good for multi-language
        )
        
        audio_bytes = b"".join(list(audio_generator))
        return audio_bytes
    except Exception as e:
        raise Exception(f"Failed to generate audio with ElevenLabs: {str(e)}")

def get_voices():
    """
    Returns available standard voices. Custom voices could be fetched dynamically if needed.
    """
    return [{"name": name, "id": vid} for name, vid in VOICE_MAP.items()]
