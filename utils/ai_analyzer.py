import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()

def analyze_business_idea(idea):
    """
    Analyze business idea using Claude AI
    Returns detailed analysis
    """
    
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    prompt = f"""Analyze this business idea in extreme detail:

IDEA: {idea}

Provide a comprehensive analysis with:

1. STRENGTHS (list 5-7 specific strengths)
2. WEAKNESSES (list 5-7 specific weaknesses and risks)
3. MARKET SIZE (give detailed estimate - small/medium/large and why)
4. TARGET AUDIENCE (be very specific - age, demographics, behaviors)
5. COMPETITION (who are the competitors and how to differentiate)
6. REVENUE POTENTIAL (realistic revenue model and estimates)
7. EXECUTION DIFFICULTY (technical, time, resources needed)
8. KEY RISKS (what could go wrong)

Be brutally honest. Give specific, actionable insights.

Return ONLY a valid JSON object with these exact keys (no markdown, no extra text):
{{
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "market_size": "detailed market size analysis",
    "target_audience": "detailed target audience description",
    "competition": "competition analysis",
    "revenue_potential": "revenue model and potential",
    "execution_difficulty": "difficulty analysis",
    "key_risks": ["risk1", "risk2", ...]
}}
"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract response
    response_text = message.content[0].text
    
    # Parse JSON from response
    # Remove markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    analysis = json.loads(response_text.strip())
    
    return analysis