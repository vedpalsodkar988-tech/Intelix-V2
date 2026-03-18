import os
import requests
from datetime import datetime, timedelta
import psycopg2
from urllib.parse import urlencode
import base64

# LinkedIn OAuth config
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI')

# Twitter OAuth config
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_REDIRECT_URI = os.getenv('TWITTER_REDIRECT_URI')
TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

# ========== LINKEDIN OAUTH ==========

def get_linkedin_auth_url(state):
    """Generate LinkedIn OAuth URL"""
    params = {
        'response_type': 'code',
        'client_id': LINKEDIN_CLIENT_ID,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'state': state,
        'scope': 'openid profile email w_member_social'
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

def exchange_linkedin_code(code):
    """Exchange authorization code for access token"""
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET
    }
    
    response = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data=data)
    return response.json()

def save_linkedin_token(user_id, token_data):
    """Save LinkedIn token to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 5184000))
    
    cursor.execute("""
        INSERT INTO oauth_tokens (user_id, platform, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, platform) 
        DO UPDATE SET access_token = %s, refresh_token = %s, expires_at = %s
    """, (
        user_id, 'linkedin', 
        token_data['access_token'], 
        token_data.get('refresh_token'),
        expires_at,
        token_data['access_token'],
        token_data.get('refresh_token'),
        expires_at
    ))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_linkedin_token(user_id):
    """Get LinkedIn token from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT access_token FROM oauth_tokens 
        WHERE user_id = %s AND platform = 'linkedin'
    """, (user_id,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else None

def post_to_linkedin(user_id, content):
    """Post content to LinkedIn - Try multiple methods"""
    access_token = get_linkedin_token(user_id)
    if not access_token:
        raise Exception("LinkedIn not connected")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    person_id = None
    
    # METHOD 1: Try userinfo endpoint
    try:
        print("[LINKEDIN DEBUG] Trying Method 1: /v2/userinfo")
        profile_response = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            person_id = profile_data.get('sub')
            print(f"[LINKEDIN DEBUG] Method 1 SUCCESS - Person ID: {person_id}")
    except Exception as e:
        print(f"[LINKEDIN DEBUG] Method 1 failed: {str(e)}")
    
    # METHOD 2: Try /me endpoint
    if not person_id:
        try:
            print("[LINKEDIN DEBUG] Trying Method 2: /v2/me")
            profile_response = requests.get(
                'https://api.linkedin.com/v2/me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                person_id = profile_data.get('id')
                print(f"[LINKEDIN DEBUG] Method 2 SUCCESS - Person ID: {person_id}")
        except Exception as e:
            print(f"[LINKEDIN DEBUG] Method 2 failed: {str(e)}")
    
    # METHOD 3: Try posting WITHOUT getting person ID first
    # Use the shares endpoint which doesn't require person URN
    if not person_id:
        print("[LINKEDIN DEBUG] Trying Method 3: /v2/shares (no person ID required)")
        try:
            share_data = {
                "content": {
                    "contentEntities": [],
                    "title": ""
                },
                "distribution": {
                    "linkedInDistributionTarget": {}
                },
                "text": {
                    "text": content
                }
            }
            
            response = requests.post(
                'https://api.linkedin.com/v2/shares',
                headers=headers,
                json=share_data
            )
            
            print(f"[LINKEDIN DEBUG] Shares API Response Status: {response.status_code}")
            print(f"[LINKEDIN DEBUG] Shares API Response Body: {response.text}")
            
            if response.status_code in [200, 201]:
                save_post(user_id, 'linkedin', 'success', content)
                return True
            else:
                raise Exception(f"Shares API failed: {response.text}")
        except Exception as e:
            print(f"[LINKEDIN DEBUG] Method 3 failed: {str(e)}")
            raise Exception(f"LinkedIn posting failed. Your app may need additional permissions. Error: {str(e)}")
    
    # If we got person_id from Method 1 or 2, use UGC Posts API
    if person_id:
        try:
            print(f"[LINKEDIN DEBUG] Using UGC Posts API with person ID: {person_id}")
            post_data = {
                "author": f"urn:li:person:{person_id}",
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
            
            response = requests.post(
                'https://api.linkedin.com/v2/ugcPosts',
                headers=headers,
                json=post_data
            )
            
            print(f"[LINKEDIN DEBUG] UGC Post Response Status: {response.status_code}")
            print(f"[LINKEDIN DEBUG] UGC Post Response Body: {response.text}")
            
            if response.status_code == 201:
                save_post(user_id, 'linkedin', 'success', content)
                return True
            else:
                raise Exception(f"UGC Post creation failed: {response.text}")
        except Exception as e:
            print(f"[LINKEDIN DEBUG] UGC Post failed: {str(e)}")
            raise Exception(f"LinkedIn error: {str(e)}")
    
    raise Exception("All LinkedIn posting methods failed")

# ========== TWITTER OAUTH ==========

def get_twitter_auth_url(state):
    """Generate Twitter OAuth URL"""
    params = {
        'response_type': 'code',
        'client_id': TWITTER_CLIENT_ID,
        'redirect_uri': TWITTER_REDIRECT_URI,
        'scope': 'tweet.read tweet.write users.read offline.access',
        'state': state,
        'code_challenge': 'challenge',
        'code_challenge_method': 'plain'
    }
    return f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"

def exchange_twitter_code(code):
    """Exchange authorization code for access token"""
    data = {
        'code': code,
        'grant_type': 'authorization_code',
        'client_id': TWITTER_CLIENT_ID,
        'redirect_uri': TWITTER_REDIRECT_URI,
        'code_verifier': 'challenge'
    }
    
    # Create Basic Auth header
    credentials = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(
        'https://api.twitter.com/2/oauth2/token',
        data=data,
        headers=headers
    )
    
    return response.json()

def save_twitter_token(user_id, token_data):
    """Save Twitter token to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200))
    
    cursor.execute("""
        INSERT INTO oauth_tokens (user_id, platform, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, platform) 
        DO UPDATE SET access_token = %s, refresh_token = %s, expires_at = %s
    """, (
        user_id, 'twitter',
        token_data['access_token'],
        token_data.get('refresh_token'),
        expires_at,
        token_data['access_token'],
        token_data.get('refresh_token'),
        expires_at
    ))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_twitter_token(user_id):
    """Get Twitter token from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT access_token FROM oauth_tokens 
        WHERE user_id = %s AND platform = 'twitter'
    """, (user_id,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else None

def post_to_twitter(user_id, content):
    """Post content to Twitter with Debug"""
    access_token = get_twitter_token(user_id)
    if not access_token:
        raise Exception("Twitter not connected")
    
    # Truncate if over 280 characters
    if len(content) > 280:
        content = content[:277] + "..."
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    post_data = {'text': content}
    
    print(f"[TWITTER DEBUG] Posting with access_token: {access_token[:20]}...")
    print(f"[TWITTER DEBUG] Content length: {len(content)}")
    
    response = requests.post(
        'https://api.twitter.com/2/tweets',
        headers=headers,
        json=post_data
    )
    
    print(f"[TWITTER DEBUG] Response Status: {response.status_code}")
    print(f"[TWITTER DEBUG] Response Body: {response.text}")
    
    if response.status_code == 201:
        post_id = response.json()['data']['id']
        save_post(user_id, 'twitter', post_id, content)
        return True
    else:
        raise Exception(f"Twitter posting failed: {response.text}")

# ========== UTILITY FUNCTIONS ==========

def is_platform_connected(user_id, platform):
    """Check if user has connected a platform"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM oauth_tokens 
        WHERE user_id = %s AND platform = %s
    """, (user_id, platform))
    
    result = cursor.fetchone()[0] > 0
    cursor.close()
    conn.close()
    
    return result

def get_posts_this_month(user_id):
    """Count posts made this month"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM posts 
        WHERE user_id = %s 
        AND created_at >= date_trunc('month', CURRENT_DATE)
    """, (user_id,))
    
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    return result

def save_post(user_id, platform, post_id, content):
    """Save post to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO posts (user_id, platform, post_id, content)
        VALUES (%s, %s, %s, %s)
    """, (user_id, platform, post_id, content))
    
    conn.commit()
    cursor.close()
    conn.close()
