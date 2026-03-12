import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()

def generate_marketing_posts(idea, analysis):
    """
    Generate viral social media posts for the business idea
    Returns 3 different post variations
    """
    
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    prompt = f"""You are a viral content creator. Create 3 different social media posts to validate this business idea:

BUSINESS IDEA: {idea}

ANALYSIS SUMMARY:
- Target Audience: {analysis.get('target_audience', 'Not specified')}
- Main Strengths: {', '.join(analysis.get('strengths', [])[:3])}

Create 3 DIFFERENT posts with these styles:

POST 1: Personal Story Approach
- Start with a personal frustration/experience
- Use casual, authentic language
- Include specific numbers if relevant
- Ask a direct question to audience
- Be humble, not salesy
- 150-200 words

POST 2: Problem/Solution Hook
- Start with the problem
- Present the solution idea
- Include call to action for feedback
- Use emojis strategically
- 120-150 words

POST 3: Poll/Engagement Style
- Pose a question or poll
- Make it interactive
- Short and punchy
- Easy to respond to
- 80-120 words

CRITICAL RULES:
- Sound HUMAN, not corporate
- NO generic startup jargon
- Be vulnerable and authentic
- Ask for honest feedback
- Make it conversational

Return ONLY valid JSON:
{{
    "post1": {{
        "title": "Personal Story",
        "content": "the actual post text here",
        "hook": "opening line"
    }},
    "post2": {{
        "title": "Problem/Solution",
        "content": "the actual post text here",
        "hook": "opening line"
    }},
    "post3": {{
        "title": "Quick Poll",
        "content": "the actual post text here",
        "hook": "opening line"
    }}
}}
"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract response
    response_text = message.content[0].text
    
    # Remove markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    # Parse JSON
    posts = json.loads(response_text.strip())
    
    return posts
