import os
import requests
from datetime import datetime, timedelta
import psycopg2
from urllib.parse import urlencode

# LinkedIn OAuth config
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI')

# Twitter OAuth config
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_REDIRECT_URI = os.getenv('TWITTER_REDIRECT_URI')

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
    """Post content to LinkedIn"""
    access_token = get_linkedin_token(user_id)
    if not access_token:
        raise Exception("LinkedIn not connected")
    
    # Get user profile ID
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
    profile_data = profile_response.json()
    person_urn = profile_data.get('sub')
    
    # Create post
    post_data = {
        "author": f"urn:li:person:{person_urn}",
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
    
    headers['Content-Type'] = 'application/json'
    headers['X-Restli-Protocol-Version'] = '2.0.0'
    
    response = requests.post(
        'https://api.linkedin.com/v2/ugcPosts',
        headers=headers,
        json=post_data
    )
    
    if response.status_code == 201:
        save_post(user_id, 'linkedin', response.json().get('id'), content)
        return True
    else:
        raise Exception(f"LinkedIn posting failed: {response.text}")

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
    
    response = requests.post(
        'https://api.twitter.com/2/oauth2/token',
        data=data,
        auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
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
    """Post content to Twitter"""
    access_token = get_twitter_token(user_id)
    if not access_token:
        raise Exception("Twitter not connected")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    post_data = {'text': content}
    
    response = requests.post(
        'https://api.twitter.com/2/tweets',
        headers=headers,
        json=post_data
    )
    
    if response.status_code == 201:
        save_post(user_id, 'twitter', response.json()['data']['id'], content)
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
