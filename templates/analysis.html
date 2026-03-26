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
    """Analyze business idea with Claude AI - WITH VERDICT & NEXT STEPS"""
    
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
    
    9. FINAL VERDICT: Rate this idea from 1-10 and give a clear verdict (e.g., "7/10 - Worth Testing", "4/10 - High Risk", "9/10 - Strong Potential")
    
    10. CLEAR DECISION: Give ONE clear recommendation from these options:
    - "✅ Build MVP immediately - Strong market demand"
    - "✅ Build small test version first"
    - "⚠️ Validate demand before building"
    - "⚠️ Pivot the approach - too competitive"
    - "❌ Don't pursue - too many obstacles"
    
    11. NEXT STEPS: List 3-4 specific, actionable next steps the person should take (be concrete and practical)
    
    12. ONE LINE SUMMARY: A single sentence summarizing whether this idea is worth pursuing
    
    IMPORTANT: Return ONLY valid JSON, no other text. Format:
    {{
        "market_size": "detailed text",
        "target_audience": "detailed text",
        "strengths": ["strength 1", "strength 2", "strength 3"],
        "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
        "competition": "detailed text",
        "revenue_potential": "detailed text",
        "execution_difficulty": "detailed text",
        "key_risks": ["risk 1", "risk 2", "risk 3"],
        "verdict": "7/10 - Worth Testing",
        "decision": "✅ Build small test version first",
        "next_steps": ["Talk to 5 target users this week", "Build simple landing page", "Test demand in 7 days"],
        "summary": "This idea has good potential but needs validation before scaling"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
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
            "key_risks": ["Please retry"],
            "verdict": "Unable to analyze",
            "decision": "Please try validating again",
            "next_steps": ["Retry validation"],
            "summary": "Analysis failed"
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
            max_tokens=300,
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
