import requests
import anthropic
import os
import json
import re

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def clean_json_response(text):
    """Clean Claude's response to extract valid JSON"""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Find JSON object
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        text = text[start:end+1]
    
    return text.strip()

def generate_linkedin_posts(idea, business_name=""):
    """Generate 3 LinkedIn posts for the business idea"""
    
    business_context = f"for {business_name}" if business_name else ""
    
    prompt = f"""Generate 3 LinkedIn posts {business_context} about this business idea:

"{idea}"

Create 3 different post styles:
1. Problem/Solution post (highlight the pain point your idea solves)
2. Value proposition post (explain why this matters)
3. Call-to-action post (invite engagement/feedback)

Each post should be:
- 100-150 words
- Professional but conversational
- Include relevant emojis
- End with a question or CTA

IMPORTANT: Return ONLY a valid JSON object, nothing else. No explanation, no markdown, just the JSON.

Format:
{{
    "post1": {{
        "title": "Problem/Solution",
        "content": "post text here"
    }},
    "post2": {{
        "title": "Value Proposition",
        "content": "post text here"
    }},
    "post3": {{
        "title": "Call to Action",
        "content": "post text here"
    }}
}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        posts_text = response.content[0].text
        print(f"Raw AI Response: {posts_text[:200]}...")  # Debug log
        
        cleaned_text = clean_json_response(posts_text)
        print(f"Cleaned JSON: {cleaned_text[:200]}...")  # Debug log
        
        posts = json.loads(cleaned_text)
        
        # Validate structure
        if not all(key in posts for key in ['post1', 'post2', 'post3']):
            raise ValueError("Invalid JSON structure")
        
        return posts
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(f"Failed to parse: {cleaned_text if 'cleaned_text' in locals() else 'N/A'}")
        return generate_fallback_posts(idea, business_name)
    except Exception as e:
        print(f"LinkedIn Posts Error: {str(e)}")
        return generate_fallback_posts(idea, business_name)

def generate_fallback_posts(idea, business_name=""):
    """Generate fallback posts when AI fails"""
    business = business_name if business_name else "this business"
    
    return {
        "post1": {
            "title": "Problem/Solution",
            "content": f"🎯 Problem: Many people struggle with the challenges that {idea.lower()} addresses.\n\n💡 Solution: {business} offers an innovative approach to solve this.\n\nWhat's your biggest challenge in this space? Let's discuss! 👇"
        },
        "post2": {
            "title": "Value Proposition",
            "content": f"🚀 Excited to share our vision: {idea}\n\n✨ Why it matters:\n• Solves real problems\n• Creates genuine value\n• Built for the future\n\nWhat do you think? Drop your thoughts below! 💭"
        },
        "post3": {
            "title": "Call to Action",
            "content": f"📢 We're building something special: {business_name if business_name else 'a new solution'}\n\n🔍 The idea: {idea}\n\nWe'd love your feedback! What features would you want to see?\n\nComment below or DM me! 👉"
        }
    }

def post_to_linkedin(access_token, user_id, content):
    """Post content to LinkedIn"""
    
    url = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    payload = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            return {'success': True}
        else:
            print(f"LinkedIn API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {'success': False, 'error': f'API Error: {response.status_code}'}
            
    except Exception as e:
        print(f"LinkedIn Posting Error: {str(e)}")
        return {'success': False, 'error': str(e)}
