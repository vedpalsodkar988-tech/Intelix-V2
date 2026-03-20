import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def add_business_name_column():
    """Add business_name column to validations table"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Add business_name column
        cursor.execute("""
            ALTER TABLE validations 
            ADD COLUMN IF NOT EXISTS business_name VARCHAR(255);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully added business_name column to validations table!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    add_business_name_column()