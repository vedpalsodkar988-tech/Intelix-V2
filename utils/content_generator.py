import anthropic
import os
import json
import re

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def generate_marketing_posts(idea_text, analysis):
    """Generate 3 marketing posts for social validation"""
    
    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY
    )
    
    prompt = f"""Based on this business idea and analysis, create 3 different social media posts for validation testing:

Business Idea: {idea_text}

Analysis Summary:
- Target Audience: {analysis['target_audience']}
- Key Strengths: {', '.join(analysis['strengths'][:2])}

Create 3 posts in JSON format:
{{
    "post1": {{
        "title": "Personal Story Post",
        "content": "A personal, relatable post (LinkedIn style, 150-200 words) that shares a problem story and hints at the solution. Sound human, not salesy."
    }},
    "post2": {{
        "title": "Problem/Solution Post",
        "content": "A direct problem/solution post (Twitter style, 200-250 chars) that's punchy and creates curiosity."
    }},
    "post3": {{
        "title": "Quick Poll Post",
        "content": "An engaging poll or question (both platforms, 100-150 words) that gets people to comment their pain points."
    }}
}}

Make posts sound HUMAN, not like AI. Use casual language, real emotions, and authentic storytelling. Return ONLY JSON, no other text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.content[0].text
    
    # Clean response - remove markdown code blocks if present
    response_text = response_text.strip()
    if response_text.startswith('```'):
        # Remove ```json or ``` from start
        response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
        # Remove ``` from end
        response_text = re.sub(r'\s*```$', '', response_text)
    
    # Parse JSON response
    posts = json.loads(response_text.strip())
    
    return posts
