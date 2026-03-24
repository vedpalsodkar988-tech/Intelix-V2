import anthropic
import os
import json
import re

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def clean_json_response(text):
    """Clean Claude's response to extract valid JSON"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        text = text[start:end+1]
    
    return text.strip()

def analyze_business_idea(idea):
    """Analyze business idea with Claude AI"""
    
    prompt = f"""
    Analyze this business idea:
    
    "{idea}"
    
    Return ONLY valid JSON (no markdown):
    {{
        "market_size": "2-3 sentences on market size and opportunity",
        "target_audience": "2-3 sentences on target customers",
        "strengths": ["strength 1", "strength 2", "strength 3"],
        "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
        "competition": "2-3 sentences on competition",
        "revenue_potential": "2-3 sentences on monetization",
        "execution_difficulty": "2-3 sentences on difficulty",
        "key_risks": ["risk 1", "risk 2", "risk 3"]
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,  # REDUCED from 2000
            messages=[{"role": "user", "content": prompt}]
        )
        
        analysis_text = response.content[0].text
        cleaned_text = clean_json_response(analysis_text)
        analysis = json.loads(cleaned_text)
        
        return analysis
        
    except Exception as e:
        print(f"Analysis Error: {str(e)}")
        return {
            "market_size": "Analysis failed. Please try again.",
            "target_audience": "Analysis failed. Please try again.",
            "strengths": ["Please retry"],
            "weaknesses": ["Please retry"],
            "competition": "Analysis failed. Please try again.",
            "revenue_potential": "Analysis failed. Please try again.",
            "execution_difficulty": "Analysis failed. Please try again.",
            "key_risks": ["Please retry"]
        }


def generate_similar_idea(original_idea, analysis):
    """Generate 1 similar business idea"""
    
    prompt = f"""
    Original idea: {original_idea}
    
    Generate 1 related business idea (different approach, same industry).
    
    Return ONLY valid JSON (no markdown):
    {{
        "title": "5-8 word title",
        "description": "2 sentences",
        "market_potential": "High/Medium/Low",
        "competition": "High/Medium/Low",
        "why_related": "1 sentence"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,  # REDUCED from 500
            messages=[{"role": "user", "content": prompt}]
        )
        
        similar_idea_text = response.content[0].text
        cleaned_text = clean_json_response(similar_idea_text)
        similar_idea = json.loads(cleaned_text)
        
        return similar_idea
        
    except Exception as e:
        print(f"Similar Idea Error: {str(e)}")
        return {
            "title": "Related Opportunity",
            "description": "Generation failed. Please retry.",
            "market_potential": "Medium",
            "competition": "Medium",
            "why_related": "Unable to generate"
        }


def generate_reel_scripts(idea, business_name=None):
    """Generate 3 reel scripts"""
    
    brand = business_name if business_name else "this product"
    
    prompt = f"""
    Business: {idea}
    Brand: {brand}
    
    Create 3 reel scripts (15-30 sec each). Different styles: Problem-Solution, Storytelling, Educational.
    
    Return ONLY valid JSON (no markdown):
    {{
        "reel1": {{
            "title": "title",
            "duration": "15-20 seconds",
            "style": "Problem-Solution",
            "hook": "first 3 sec",
            "script": "voiceover",
            "text_overlays": ["text 1", "text 2", "text 3"],
            "music_vibe": "vibe",
            "cta": "cta"
        }},
        "reel2": {{...}},
        "reel3": {{...}}
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,  # REDUCED from 2000
            messages=[{"role": "user", "content": prompt}]
        )
        
        reels_text = response.content[0].text
        cleaned_text = clean_json_response(reels_text)
        reels = json.loads(cleaned_text)
        
        return reels
        
    except Exception as e:
        print(f"Reel Scripts Error: {str(e)}")
        return {
            "reel1": {
                "title": "Script 1",
                "duration": "15-20 seconds",
                "style": "Problem-Solution",
                "hook": "Generation failed",
                "script": "Unable to generate. Please retry.",
                "text_overlays": ["Retry"],
                "music_vibe": "Upbeat",
                "cta": "Try again"
            },
            "reel2": {
                "title": "Script 2",
                "duration": "15-20 seconds",
                "style": "Storytelling",
                "hook": "Generation failed",
                "script": "Unable to generate. Please retry.",
                "text_overlays": ["Retry"],
                "music_vibe": "Calm",
                "cta": "Try again"
            },
            "reel3": {
                "title": "Script 3",
                "duration": "15-20 seconds",
                "style": "Educational",
                "hook": "Generation failed",
                "script": "Unable to generate. Please retry.",
                "text_overlays": ["Retry"],
                "music_vibe": "Energetic",
                "cta": "Try again"
            }
        }
