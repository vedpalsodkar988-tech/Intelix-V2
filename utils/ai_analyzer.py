import anthropic
import os
import json
import re

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def clean_json_response(text):
    """Clean Claude's response to extract valid JSON"""
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Remove any text before first { and after last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        text = text[start:end+1]
    
    return text.strip()

def analyze_business_idea(idea):
    """Analyze business idea with Claude AI"""
    
    prompt = f"""
    Analyze this business idea comprehensively:
    
    "{idea}"
    
    Provide a detailed analysis with these sections:
    
    1. Market Size & Opportunity: Estimate the total addressable market and growth potential
    2. Target Audience: Define the specific customer segments who would benefit most
    3. Strengths & Opportunities: List 3-4 key advantages and opportunities
    4. Weaknesses & Challenges: List 3-4 potential obstacles and weaknesses
    5. Competition Analysis: Describe the competitive landscape
    6. Revenue Potential: Assess monetization opportunities and pricing strategies
    7. Execution Difficulty: Rate complexity and required resources
    8. Key Risks: Identify 3-4 major risks to consider
    
    IMPORTANT: Return ONLY valid JSON, no other text. Format:
    {{
        "market_size": "detailed text",
        "target_audience": "detailed text",
        "strengths": ["strength 1", "strength 2", "strength 3"],
        "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
        "competition": "detailed text",
        "revenue_potential": "detailed text",
        "execution_difficulty": "detailed text",
        "key_risks": ["risk 1", "risk 2", "risk 3"]
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        analysis_text = response.content[0].text
        
        # Clean the response
        cleaned_text = clean_json_response(analysis_text)
        
        # Parse JSON
        analysis = json.loads(cleaned_text)
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON Error: {str(e)}")
        print(f"Raw response: {analysis_text}")
        
        # Return fallback response
        return {
            "market_size": "Unable to analyze at this time. Please try again.",
            "target_audience": "Unable to analyze at this time. Please try again.",
            "strengths": ["Analysis failed - please retry"],
            "weaknesses": ["Analysis failed - please retry"],
            "competition": "Unable to analyze at this time. Please try again.",
            "revenue_potential": "Unable to analyze at this time. Please try again.",
            "execution_difficulty": "Unable to analyze at this time. Please try again.",
            "key_risks": ["Analysis failed - please retry"]
        }
    except Exception as e:
        print(f"API Error: {str(e)}")
        raise


def generate_similar_idea(original_idea, analysis):
    """Generate 1 similar business idea based on validated idea"""
    
    prompt = f"""
    Original idea: {original_idea}
    
    Target audience: {analysis['target_audience']}
    Market size: {analysis['market_size']}
    
    Generate 1 DIFFERENT but RELATED business idea that:
    - Targets similar audience
    - Solves a related problem
    - Is in same industry/vertical
    - But has different approach/angle
    
    Make it creative and actionable.
    
    IMPORTANT: Return ONLY valid JSON, no other text. Format:
    {{
        "title": "Short catchy title (5-8 words)",
        "description": "Clear 2-sentence description of the business idea",
        "market_potential": "High/Medium/Low",
        "competition": "High/Medium/Low",
        "why_related": "1 sentence explaining why this is related to original idea"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        similar_idea_text = response.content[0].text
        
        # Clean the response
        cleaned_text = clean_json_response(similar_idea_text)
        
        # Parse JSON
        similar_idea = json.loads(cleaned_text)
        
        return similar_idea
        
    except json.JSONDecodeError as e:
        print(f"JSON Error in similar idea: {str(e)}")
        print(f"Raw response: {similar_idea_text}")
        
        # Return fallback
        return {
            "title": "Related Business Opportunity",
            "description": "Similar idea generation failed. Please try validating again.",
            "market_potential": "Medium",
            "competition": "Medium",
            "why_related": "Unable to generate at this time"
        }
    except Exception as e:
        print(f"API Error in similar idea: {str(e)}")
        return {
            "title": "Related Business Opportunity",
            "description": "Similar idea generation failed. Please try validating again.",
            "market_potential": "Medium",
            "competition": "Medium",
            "why_related": "Unable to generate at this time"
        }


def generate_reel_scripts(idea, business_name=None):
    """Generate 3 short video scripts (Reels/Shorts) for the business idea"""
    
    brand = business_name if business_name else "this product"
    
    prompt = f"""
    Business idea: {idea}
    Brand name: {brand}
    
    Create 3 short video scripts for Instagram Reels or YouTube Shorts (15-30 seconds each).
    
    Each script should:
    - Hook viewer in first 3 seconds
    - Present the problem
    - Show the solution (the product)
    - End with clear CTA
    - Be engaging and natural (not salesy)
    - Include text overlay suggestions
    
    Format for each:
    - Scene descriptions
    - What to say (script)
    - Text overlays to add
    - Background music vibe
    
    Make them different styles:
    1. Problem-solution style
    2. Storytelling/personal style
    3. Quick tips/educational style
    
    IMPORTANT: Return ONLY valid JSON, no other text. Format:
    {{
        "reel1": {{
            "title": "Hook title",
            "duration": "15-20 seconds",
            "style": "Problem-Solution",
            "hook": "First 3 seconds text",
            "script": "Full voiceover script",
            "text_overlays": ["overlay 1", "overlay 2", "overlay 3"],
            "music_vibe": "Energetic/Calm/Upbeat",
            "cta": "Call to action"
        }},
        "reel2": {{
            "title": "Hook title",
            "duration": "15-20 seconds",
            "style": "Storytelling",
            "hook": "First 3 seconds text",
            "script": "Full voiceover script",
            "text_overlays": ["overlay 1", "overlay 2", "overlay 3"],
            "music_vibe": "Energetic/Calm/Upbeat",
            "cta": "Call to action"
        }},
        "reel3": {{
            "title": "Hook title",
            "duration": "15-20 seconds",
            "style": "Educational",
            "hook": "First 3 seconds text",
            "script": "Full voiceover script",
            "text_overlays": ["overlay 1", "overlay 2", "overlay 3"],
            "music_vibe": "Energetic/Calm/Upbeat",
            "cta": "Call to action"
        }}
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        reels_text = response.content[0].text
        
        # Clean the response
        cleaned_text = clean_json_response(reels_text)
        
        # Parse JSON
        reels = json.loads(cleaned_text)
        
        return reels
        
    except json.JSONDecodeError as e:
        print(f"JSON Error in reel scripts: {str(e)}")
        print(f"Raw response: {reels_text}")
        
        # Return fallback
        return {
            "reel1": {
                "title": "Reel Script 1",
                "duration": "15-20 seconds",
                "style": "Problem-Solution",
                "hook": "Script generation failed",
                "script": "Unable to generate reel scripts at this time. Please try again.",
                "text_overlays": ["Try again later"],
                "music_vibe": "Upbeat",
                "cta": "Retry validation"
            },
            "reel2": {
                "title": "Reel Script 2",
                "duration": "15-20 seconds",
                "style": "Storytelling",
                "hook": "Script generation failed",
                "script": "Unable to generate reel scripts at this time. Please try again.",
                "text_overlays": ["Try again later"],
                "music_vibe": "Calm",
                "cta": "Retry validation"
            },
            "reel3": {
                "title": "Reel Script 3",
                "duration": "15-20 seconds",
                "style": "Educational",
                "hook": "Script generation failed",
                "script": "Unable to generate reel scripts at this time. Please try again.",
                "text_overlays": ["Try again later"],
                "music_vibe": "Energetic",
                "cta": "Retry validation"
            }
        }
    except Exception as e:
        print(f"API Error in reel scripts: {str(e)}")
        raise
