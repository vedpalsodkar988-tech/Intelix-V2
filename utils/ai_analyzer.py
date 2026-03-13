import anthropic
import os
import json

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def analyze_business_idea(idea_text):
    """Analyze business idea using Claude API"""
    
    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY
    )
    
    prompt = f"""Analyze this business idea and provide a structured analysis:

Business Idea: {idea_text}

Provide your analysis in the following JSON format:
{{
    "market_size": "Brief description of market size and opportunity (2-3 sentences)",
    "target_audience": "Description of ideal customers (2-3 sentences)",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
    "competition": "Analysis of competitive landscape (2-3 sentences)",
    "revenue_potential": "Revenue model and potential (2-3 sentences)",
    "execution_difficulty": "How hard is it to execute? (2-3 sentences)",
    "key_risks": ["risk 1", "risk 2", "risk 3"]
}}

Return ONLY the JSON, no additional text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.content[0].text
    
    # Parse JSON response
    analysis = json.loads(response_text)
    
    return analysis
