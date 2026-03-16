import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def create_oauth_table():
    """Create table for storing OAuth tokens"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            platform VARCHAR(50) NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, platform)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ OAuth tokens table created!")

def create_posts_table():
    """Create table for tracking posts"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            platform VARCHAR(50) NOT NULL,
            post_id TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_user_month 
        ON posts(user_id, created_at)
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Posts table created!")

if __name__ == '__main__':
    create_oauth_table()
    create_posts_table()
