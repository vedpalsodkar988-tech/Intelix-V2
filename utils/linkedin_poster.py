import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def generate_linkedin_posts(idea, business_name=""):
    """Generate 3 LinkedIn posts for the business idea"""
    
    business_mention = f"Business Name: {business_name}\n" if business_name else ""
    
    prompt = f"""Generate 3 specific LinkedIn marketing posts for this business:

{business_mention}Business Idea: {idea}

Create 3 posts that are DIRECTLY about this specific business concept:

1. PROBLEM/SOLUTION POST:
- Identify the exact problem this business solves
- Explain the specific solution
- Use concrete details from the idea
- 120-150 words

2. VALUE PROPOSITION POST:
- Highlight what makes THIS business unique
- Focus on specific benefits and outcomes
- Mention key features
- 120-150 words

3. ENGAGEMENT POST:
- Generate excitement about THIS specific concept
- Ask for feedback on THIS idea
- Be conversational and inviting
- 120-150 words

RULES:
- Every post MUST mention specific details from the business idea
- Include the business name if provided: {business_name}
- Use 2-3 relevant emojis per post
- End each with a question
- Be professional but conversational
- NO generic startup language

Output as JSON only:
{{
  "post1": {{"title": "Problem/Solution", "content": "..."}},
  "post2": {{"title": "Value Proposition", "content": "..."}},
  "post3": {{"title": "Engagement", "content": "..."}}
}}"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            temperature=0.9,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text.strip()
        
        # Remove markdown formatting
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        response_text = response_text.strip()
        
        print(f"Marketing AI Response (first 500 chars): {response_text[:500]}")
        
        # Parse JSON
        posts = json.loads(response_text)
        
        # Validate all required keys exist
        required_keys = ['post1', 'post2', 'post3']
        if not all(key in posts for key in required_keys):
            raise ValueError(f"Missing required keys. Got: {list(posts.keys())}")
        
        # Validate each post has content
        for key in required_keys:
            if 'content' not in posts[key]:
                raise ValueError(f"{key} missing content")
            if len(posts[key]['content']) < 50:
                raise ValueError(f"{key} content too short")
        
        print("✅ Marketing posts generated successfully!")
        return posts
        
    except json.JSONDecodeError as je:
        print(f"❌ JSON Parse Error: {je}")
        print(f"Response was: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        raise Exception("Failed to generate valid marketing posts. Please try again.")
        
    except Exception as e:
        print(f"❌ Marketing Generation Error: {e}")
        raise Exception(f"Failed to generate marketing posts: {str(e)}")

def post_to_linkedin(access_token, user_id, content):
    """Post content to LinkedIn"""
    import requests
    
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
