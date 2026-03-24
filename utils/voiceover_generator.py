from elevenlabs import ElevenLabs, VoiceSettings
import os

def generate_voiceover(script_text, voice_name="Rachel"):
    """
    Generate AI voiceover for reel script
    
    Args:
        script_text: The script to convert to speech
        voice_name: Voice to use (Rachel, Josh, Antoni, etc.)
    
    Returns:
        Audio file bytes
    """
    try:
        client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        
        # Generate audio
        audio = client.text_to_speech.convert(
            text=script_text,
            voice_id=get_voice_id(voice_name),
            model_id="eleven_turbo_v2_5",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True
            )
        )
        
        # Convert generator to bytes
        audio_bytes = b"".join(audio)
        
        return audio_bytes
        
    except Exception as e:
        print(f"Voiceover generation error: {str(e)}")
        return None


def get_voice_id(voice_name):
    """Get voice ID from voice name"""
    voices = {
        "Rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, American
        "Josh": "TxGEqnHWrfWFTfGW9XjX",    # Male, American
        "Antoni": "ErXwobaYiN019PkySvjV",  # Male, American
        "Bella": "EXAVITQu4vr4xnSDxMaL",   # Female, American
        "Arnold": "VR6AewLTigWG4xSOukaG",  # Male, American
        "Adam": "pNInz6obpgDQGcFmaJgB",    # Male, American
        "Domi": "AZnzlk1XvdvUeBnXmlld",    # Female, American
        "Elli": "MF3mGyEYCl7XYWbV9V6O",    # Female, American
    }
    
    return voices.get(voice_name, voices["Rachel"])


def save_voiceover_to_file(audio_bytes, filename):
    """Save audio bytes to file"""
    try:
        with open(filename, 'wb') as f:
            f.write(audio_bytes)
        return True
    except Exception as e:
        print(f"Error saving voiceover: {str(e)}")
        return False
