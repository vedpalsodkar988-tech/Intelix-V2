import os
from anthropic import Anthropic
import json
import re

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def generate_marketing_posts(idea, analysis, business_name=None):
    """Generate 3 diverse marketing posts for LinkedIn validation"""
    
    # Determine how to refer to the solution
    if business_name and business_name.strip():
        solution_ref = f'"{business_name}"'
        solution_type = "named product"
    else:
        solution_ref = '"this solution"'
        solution_type = "generic reference"
    
    prompt = f"""You are a marketing expert creating LinkedIn posts to validate a business idea.

BUSINESS IDEA: {idea}

BUSINESS/PRODUCT NAME: {business_name if business_name else "NOT PROVIDED - Use generic terms like 'this solution', 'the app', 'my product', etc."}

ANALYSIS INSIGHTS:
- Target Market: {analysis.get('target_market', 'N/A')}
- Strengths: {analysis.get('strengths', 'N/A')}
- Viability Score: {analysis.get('viability_score', 'N/A')}/10

Create 3 DIFFERENT LinkedIn posts that:
1. PRESENT THE PROBLEM the idea solves
2. INTRODUCE THE SOLUTION using {solution_ref} (the business idea)
3. INCLUDE A CLEAR CALL-TO-ACTION (visit website, DM for early access, comment interest, etc.)
4. Make it PROMOTIONAL but authentic and engaging
5. Each post should have a DIFFERENT angle/approach

POST GUIDELINES:
- Keep each post 150-250 words
- Use natural, conversational tone
- Include relevant emojis (2-4 per post)
- End with clear call-to-action
- Use {solution_ref} when mentioning the product/solution
- Add line breaks for readability
- Don't just describe the problem - SELL THE SOLUTION

POST TYPES (use different angles):
Post 1: Personal story → Problem → Solution → CTA
Post 2: Problem statement → Solution intro → Benefits → CTA  
Post 3: Question/Hook → Problem validation → Solution reveal → CTA

IMPORTANT: 
- Don't just ask questions without mentioning the solution
- Each post should clearly introduce the business idea as the answer
- Include phrases like "I'm building {solution_ref}", "We're launching {solution_ref}", "Introducing {solution_ref}"
- End with action-oriented CTAs like:
  * "Interested? Drop a comment or DM me!"
  * "Early access starting soon - comment 'interested' below!"
  * "Building this now - want to be a beta tester?"
  * "Link in comments / DM for early access"

Return your response as a JSON object with this EXACT structure:
{{
    "post1": {{
        "title": "Personal Story Post",
        "content": "Your first post content here..."
    }},
    "post2": {{
        "title": "Problem-Solution Post",
        "content": "Your second post content here..."
    }},
    "post3": {{
        "title": "Engagement Hook Post",
        "content": "Your third post content here..."
    }}
}}

CRITICAL: Return ONLY the JSON object, nothing else. No markdown, no code blocks, no explanations."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        # Clean up response
        response_text = response_text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        posts = json.loads(response_text)
        
        return posts
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print(f"Response was: {response_text}")
        raise Exception("Failed to parse AI response")
    except Exception as e:
        print(f"Error generating posts: {str(e)}")
        raise
