import requests
import os
import base64

def generate_voiceover(script_text, voice_name="en-US-Neural2-F"):
    """
    Generate AI voiceover using Google Cloud Text-to-Speech REST API
    
    Args:
        script_text: The script to convert to speech
        voice_name: Voice to use (default: Neural2-F - female voice)
    
    Returns:
        Audio file bytes or None if failed
    """
    try:
        api_key = os.getenv('GOOGLE_TTS_API_KEY')
        
        if not api_key:
            print("ERROR: GOOGLE_TTS_API_KEY not found")
            return None
        
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        
        payload = {
            "input": {
                "text": script_text
            },
            "voice": {
                "languageCode": "en-US",
                "name": voice_name,
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
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"Google TTS Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'audioContent' in data:
                audio_content = base64.b64decode(data['audioContent'])
                print(f"Audio generated successfully: {len(audio_content)} bytes")
                return audio_content
            else:
                print(f"No audioContent in response: {data}")
                return None
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timeout after 30 seconds")
        return None
    except Exception as e:
        print(f"Google TTS Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_available_voices():
    """Get list of available Google TTS voices"""
    voices = {
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
    return voices
