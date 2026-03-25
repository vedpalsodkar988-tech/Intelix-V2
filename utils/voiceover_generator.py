from google.cloud import texttospeech
import os
import base64

def generate_voiceover(script_text, voice_name="en-US-Neural2-F"):
    """
    Generate AI voiceover using Google Cloud Text-to-Speech
    
    Args:
        script_text: The script to convert to speech
        voice_name: Voice to use (default: Neural2-F - female voice)
    
    Returns:
        Audio file bytes or None if failed
    """
    try:
        # Set API key
        os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'] = '{"type": "service_account", "project_id": "intelix", "private_key_id": "dummy", "private_key": "dummy", "client_email": "dummy@intelix.iam.gserviceaccount.com", "client_id": "dummy", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"}'
        
        # Initialize client with API key
        client = texttospeech.TextToSpeechClient.from_service_account_info({
            "type": "service_account",
            "project_id": "intelix-voiceover",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\n-----END PRIVATE KEY-----\n",
            "client_email": "intelix@intelix-voiceover.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        
        # Configure the voice request
        synthesis_input = texttospeech.SynthesisInput(text=script_text)
        
        # Select voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Configure audio
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Generate speech
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
        
    except Exception as e:
        print(f"Google TTS Error: {str(e)}")
        
        # Fallback: Try with direct API key method
        try:
            return generate_voiceover_with_api_key(script_text)
        except Exception as e2:
            print(f"Fallback error: {str(e2)}")
            return None


def generate_voiceover_with_api_key(script_text):
    """
    Fallback method using REST API with API key
    """
    import requests
    
    api_key = os.getenv('GOOGLE_TTS_API_KEY')
    
    if not api_key:
        raise Exception("GOOGLE_TTS_API_KEY not found")
    
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    
    payload = {
        "input": {
            "text": script_text
        },
        "voice": {
            "languageCode": "en-US",
            "name": "en-US-Neural2-F",
            "ssmlGender": "FEMALE"
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 1.0,
            "pitch": 0.0
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        audio_content = base64.b64decode(data['audioContent'])
        return audio_content
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")


def get_available_voices():
    """Get list of available voices"""
    return {
        "en-US-Neural2-F": "Female (Natural)",
        "en-US-Neural2-A": "Male (Natural)",
        "en-US-Neural2-C": "Female (Warm)",
        "en-US-Neural2-D": "Male (Deep)",
        "en-US-Neural2-E": "Female (Young)",
        "en-US-Neural2-G": "Female (Professional)",
        "en-US-Neural2-H": "Female (Expressive)",
        "en-US-Neural2-I": "Male (Confident)",
        "en-US-Neural2-J": "Male (Friendly)"
    }
