from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
from dotenv import load_dotenv
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Database connection helper
def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# Timezone helper
def convert_to_ist(utc_time):
    """Convert UTC time to IST"""
    if utc_time.tzinfo is None:
        utc_time = pytz.utc.localize(utc_time)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_time.astimezone(ist)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== ROUTES ==========

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert user
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (username, email, hashed_password)
            )
            user_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Auto-login after signup
            session['user_id'] = user_id
            session['username'] = username
            
            return redirect(url_for('dashboard'))
            
        except psycopg2.IntegrityError:
            return "Email or username already exists!", 400
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get user
            cursor.execute(
                "SELECT id, username, password FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                # Login successful
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect(url_for('dashboard'))
            else:
                return "Invalid email or password!", 401
                
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main validator dashboard (protected)"""
    # Get user stats
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM validations WHERE user_id = %s",
        (session['user_id'],)
    )
    validation_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', username=session.get('username'), validation_count=validation_count)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """Analyze business idea with real AI"""
    idea = request.form.get('idea')
    
    # Import the analyzer
    from utils.ai_analyzer import analyze_business_idea
    
    # Get real AI analysis
    try:
        analysis = analyze_business_idea(idea)
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO validations (user_id, idea_text, analysis) VALUES (%s, %s, %s)",
            (session['user_id'], idea, json.dumps(analysis))
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Store in session for marketing page
        session['current_idea'] = idea
        session['current_analysis'] = analysis
        
    except Exception as e:
        return f"Error analyzing idea: {str(e)}"
    
    return render_template('analysis.html', analysis=analysis, idea=idea)

@app.route('/marketing', methods=['GET', 'POST'])
@login_required
def marketing():
    """Marketing campaign setup"""
    if request.method == 'POST':
        # Get idea and analysis from session (not from form)
        idea = session.get('current_idea')
        analysis = session.get('current_analysis')
        
        if not idea or not analysis:
            return redirect(url_for('dashboard'))
        
        # Generate marketing posts
        from utils.content_generator import generate_marketing_posts
        
        try:
            posts = generate_marketing_posts(idea, analysis)
        except Exception as e:
            return f"Error generating posts: {str(e)}"
        
        return render_template('marketing.html', posts=posts, idea=idea)
    
    return render_template('marketing.html')

@app.route('/results')
@login_required
def results():
    """Validation results"""
    return render_template('results.html')

@app.route('/settings')
@login_required
def settings():
    """User settings page"""
    # Get user info from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT username, email, created_at FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user = cursor.fetchone()
    
    # Get validation count
    cursor.execute(
        "SELECT COUNT(*) FROM validations WHERE user_id = %s",
        (session['user_id'],)
    )
    validation_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    # Convert created_at to IST
    created_at_ist = convert_to_ist(user[2])
    
    user_data = {
        'username': user[0],
        'email': user[1],
        'created_at': created_at_ist,
        'validation_count': validation_count
    }
    
    return render_template('settings.html', user=user_data)

@app.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current password hash
    cursor.execute(
        "SELECT password FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user = cursor.fetchone()
    
    if user and check_password_hash(user[0], current_password):
        # Update password
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (new_hash, session['user_id'])
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('settings') + '?success=password')
    else:
        cursor.close()
        conn.close()
        return redirect(url_for('settings') + '?error=password')

@app.route('/settings/delete', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all data"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete all validations
    cursor.execute("DELETE FROM validations WHERE user_id = %s", (user_id,))
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Clear session
    session.clear()
    
    return redirect(url_for('index'))

@app.route('/validations')
@login_required
def validations():
    """User's validation history"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, idea_text, created_at FROM validations WHERE user_id = %s ORDER BY created_at DESC",
        (session['user_id'],)
    )
    validations_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    validations_data = [
        {
            'id': v[0],
            'idea': v[1][:100] + '...' if len(v[1]) > 100 else v[1],
            'date': convert_to_ist(v[2])
        }
        for v in validations_list
    ]
    
    return render_template('validations.html', validations=validations_data)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """404 error page"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """500 error page"""
    return render_template('500.html'), 500

# ========== RUN APP ==========

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
