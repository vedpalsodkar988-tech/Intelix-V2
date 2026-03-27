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
    """Analyze business idea with Claude AI - OPTIMIZED FOR SPEED"""
    
    prompt = f"""
    Analyze this business idea:
    
    "{idea}"
    
    Provide analysis in these sections (keep each section to 2-3 sentences):
    
    1. Market Size & Opportunity (2-3 sentences)
    2. Target Audience (2-3 sentences)
    3. Strengths & Opportunities (3 bullet points)
    4. Weaknesses & Challenges (3 bullet points)
    5. Competition Analysis (2-3 sentences)
    6. Revenue Potential (2-3 sentences)
    7. Execution Difficulty (2-3 sentences)
    8. Key Risks (3 bullet points)
    9. FINAL VERDICT: Rate 1-10 with short verdict (e.g., "7/10 - Worth Testing")
    10. CLEAR DECISION: ONE recommendation (e.g., "✅ Build small test version first")
    11. NEXT STEPS: 3 specific action items
    12. ONE LINE SUMMARY: Single sentence summary
    
    Return ONLY valid JSON:
    {{
        "market_size": "text",
        "target_audience": "text",
        "strengths": ["point 1", "point 2", "point 3"],
        "weaknesses": ["point 1", "point 2", "point 3"],
        "competition": "text",
        "revenue_potential": "text",
        "execution_difficulty": "text",
        "key_risks": ["risk 1", "risk 2", "risk 3"],
        "verdict": "7/10 - Worth Testing",
        "decision": "✅ Build small test version first",
        "next_steps": ["action 1", "action 2", "action 3"],
        "summary": "one sentence"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        analysis_text = response.content[0].text
        cleaned_text = clean_json_response(analysis_text)
        analysis = json.loads(cleaned_text)
        
        return analysis
        
    except Exception as e:
        print(f"Analysis Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "market_size": "Analysis failed. Please try again.",
            "target_audience": "Analysis failed. Please try again.",
            "strengths": ["Please retry"],
            "weaknesses": ["Please retry"],
            "competition": "Analysis failed. Please try again.",
            "revenue_potential": "Analysis failed. Please try again.",
            "execution_difficulty": "Analysis failed. Please try again.",
            "key_risks": ["Please retry"],
            "verdict": "Unable to analyze",
            "decision": "Please try validating again",
            "next_steps": ["Retry validation"],
            "summary": "Analysis failed"
        }


def generate_similar_idea(original_idea, analysis):
    """Generate 1 similar business idea"""
    
    prompt = f"""
    Original: {original_idea}
    
    Generate 1 related idea (different approach, same industry).
    
    JSON only:
    {{
        "title": "5-8 words",
        "description": "2 sentences",
        "market_potential": "High/Medium/Low",
        "competition": "High/Medium/Low",
        "why_related": "1 sentence"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=250,
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
