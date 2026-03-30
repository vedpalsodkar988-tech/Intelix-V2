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
    
    business_context = f"The business is called '{business_name}'. " if business_name else ""
    
    prompt = f"""You are a LinkedIn marketing expert. Generate 3 engaging LinkedIn posts for this specific business idea:

Business Idea: "{idea}"
{business_context}

CRITICAL INSTRUCTIONS:
- Each post MUST be specifically about THIS exact business idea
- Include the business name "{business_name}" if provided
- Reference specific features and benefits of THIS idea
- Make posts unique and tailored to THIS concept
- DO NOT write generic startup posts

Create 3 different post styles:

POST 1 - Problem/Solution:
- Start with the specific problem this idea solves
- Explain how THIS business solves it
- Be specific and concrete

POST 2 - Value Proposition:
- Highlight unique benefits of THIS specific idea
- Explain the transformation/outcome for users
- Use specific details from the idea

POST 3 - Call to Action:
- Share excitement about THIS specific concept
- Invite feedback on THIS idea
- Ask a specific question related to THIS business

REQUIREMENTS:
- 100-150 words per post
- Professional but conversational tone
- Include 2-3 relevant emojis per post
- End with engagement question
- Be SPECIFIC to this business idea

Return ONLY valid JSON, no other text:

{{
    "post1": {{
        "title": "Problem/Solution",
        "content": "your post here - MUST mention the specific idea"
    }},
    "post2": {{
        "title": "Value Proposition",
        "content": "your post here - MUST mention the specific benefits"
    }},
    "post3": {{
        "title": "Call to Action",
        "content": "your post here - MUST be about this specific idea"
    }}
}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        )
        
        posts_text = response.content[0].text
        print(f"Raw AI Response: {posts_text[:300]}...")  # Debug log
        
        cleaned_text = clean_json_response(posts_text)
        print(f"Cleaned JSON: {cleaned_text[:300]}...")  # Debug log
        
        posts = json.loads(cleaned_text)
        
        # Validate structure
        if not all(key in posts for key in ['post1', 'post2', 'post3']):
            raise ValueError("Invalid JSON structure")
        
        # Validate content mentions the idea
        idea_lower = idea.lower()
        business_lower = business_name.lower() if business_name else ""
        
        for post_key in ['post1', 'post2', 'post3']:
            content_lower = posts[post_key]['content'].lower()
            # Check if post is too generic
            if len(content_lower) < 50 or (business_name and business_lower not in content_lower):
                print(f"Warning: {post_key} might be too generic")
        
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
    business_text = f"{business_name} - " if business_name else ""
    
    # Make fallback posts specific to the idea
    return {
        "post1": {
            "title": "Problem/Solution",
            "content": f"🎯 {business_text}{idea}\n\nThis innovative solution addresses a real market need. By focusing on the core problem, we're building something that actually helps people.\n\nWhat challenges do you see in this space? Let's discuss! 👇"
        },
        "post2": {
            "title": "Value Proposition",
            "content": f"🚀 Excited about {business_text}{idea}\n\n✨ Why this matters:\n• Solves a genuine problem\n• User-focused approach\n• Built with real feedback in mind\n\nWould you use something like this? Share your thoughts! 💭"
        },
        "post3": {
            "title": "Call to Action",
            "content": f"📢 Building: {business_text}{idea}\n\n🔍 We're in the early stages and want YOUR input!\n\nWhat features would make this most valuable to you?\n\nDrop a comment or DM - all feedback welcome! 🙌"
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
