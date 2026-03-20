from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
from dotenv import load_dotenv
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
from datetime import datetime
import pytz
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Session configuration for OAuth
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Import OAuth handlers
from utils.oauth_handler import *

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
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (username, email, hashed_password)
            )
            user_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            session.permanent = True
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
            
            cursor.execute(
                "SELECT id, username, password FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                session.permanent = True
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
    """Main validator dashboard"""
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
    """Analyze business idea with AI"""
    idea = request.form.get('idea')
    
    from utils.ai_analyzer import analyze_business_idea
    
    try:
        analysis = analyze_business_idea(idea)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO validations (user_id, idea_text, analysis) VALUES (%s, %s, %s)",
            (session['user_id'], idea, json.dumps(analysis))
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        session['current_idea'] = idea
        session['current_analysis'] = analysis
        
    except Exception as e:
        return f"Error analyzing idea: {str(e)}"
    
    return render_template('analysis.html', analysis=analysis, idea=idea, from_history=False)

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

@app.route('/validation/<int:validation_id>')
@login_required
def view_validation(validation_id):
    """View a specific validation and generate fresh posts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, idea_text, analysis, created_at FROM validations WHERE id = %s AND user_id = %s",
            (validation_id, session['user_id'])
        )
        validation = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not validation:
            return "Validation not found", 404
        
        # Handle both dict and string types for analysis
        analysis_data = validation[2]
        if isinstance(analysis_data, dict):
            analysis = analysis_data
        elif isinstance(analysis_data, str):
            analysis = json.loads(analysis_data)
        else:
            analysis = json.loads(str(analysis_data))
        
        # Store in session for marketing page
        session['current_idea'] = validation[1]
        session['current_analysis'] = analysis
        
        return render_template('analysis.html', 
                             analysis=analysis, 
                             idea=validation[1],
                             from_history=True)
    except Exception as e:
        print(f"Error in view_validation: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading validation: {str(e)}", 500

@app.route('/marketing', methods=['GET', 'POST'])
@login_required
def marketing():
    """Marketing campaign setup - ALWAYS generates fresh posts"""
    if request.method == 'POST':
        idea = session.get('current_idea')
        analysis = session.get('current_analysis')
        
        if not idea or not analysis:
            return redirect(url_for('dashboard'))
        
        from utils.content_generator import generate_marketing_posts
        
        try:
            # ALWAYS generate fresh posts - never use cached ones
            posts = generate_marketing_posts(idea, analysis)
        except Exception as e:
            return f"Error generating posts: {str(e)}"
        
        linkedin_connected = is_platform_connected(session['user_id'], 'linkedin')
        posts_used = get_posts_this_month(session['user_id'])
        
        return render_template('marketing.html', 
                             posts=posts, 
                             idea=idea,
                             linkedin_connected=linkedin_connected,
                             posts_used=posts_used,
                             posts_limit=5)
    
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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT username, email, created_at FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user = cursor.fetchone()
    
    cursor.execute(
        "SELECT COUNT(*) FROM validations WHERE user_id = %s",
        (session['user_id'],)
    )
    validation_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    created_at_ist = convert_to_ist(user[2])
    
    linkedin_connected = is_platform_connected(session['user_id'], 'linkedin')
    
    user_data = {
        'username': user[0],
        'email': user[1],
        'created_at': created_at_ist,
        'validation_count': validation_count,
        'linkedin_connected': linkedin_connected
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
    
    cursor.execute(
        "SELECT password FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user = cursor.fetchone()
    
    if user and check_password_hash(user[0], current_password):
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
    
    cursor.execute("DELETE FROM validations WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM posts WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM oauth_tokens WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    session.clear()
    
    return redirect(url_for('index'))

# ========== OAUTH ROUTES ==========

@app.route('/oauth/linkedin')
@login_required
def oauth_linkedin():
    """Initiate LinkedIn OAuth"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session.modified = True
    auth_url = get_linkedin_auth_url(state)
    return redirect(auth_url)

@app.route('/oauth/linkedin/callback')
def oauth_linkedin_callback():
    """Handle LinkedIn OAuth callback"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return redirect(url_for('settings') + f'?error=linkedin&msg={error}')
    
    if not code:
        return redirect(url_for('settings') + '?error=linkedin&msg=no_code')
    
    stored_state = session.get('oauth_state')
    
    if not stored_state or state != stored_state:
        print(f"State mismatch: stored={stored_state}, received={state}")
    
    try:
        token_data = exchange_linkedin_code(code)
        
        if 'error' in token_data:
            error_msg = token_data.get('error_description', token_data.get('error', 'Unknown error'))
            return redirect(url_for('settings') + f'?error=linkedin&msg={error_msg}')
        
        save_linkedin_token(session['user_id'], token_data)
        
        session.pop('oauth_state', None)
        
        return redirect(url_for('settings') + '?success=linkedin')
    except Exception as e:
        print(f"LinkedIn OAuth error: {str(e)}")
        return redirect(url_for('settings') + f'?error=linkedin&msg={str(e)}')

@app.route('/oauth/disconnect/linkedin', methods=['POST'])
@login_required
def disconnect_linkedin():
    """Disconnect LinkedIn account"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM oauth_tokens 
        WHERE user_id = %s AND platform = 'linkedin'
    """, (session['user_id'],))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('settings') + '?success=linkedin_disconnected')

# ========== POSTING ROUTES ==========

@app.route('/post/linkedin', methods=['POST'])
@login_required
def post_linkedin_route():
    """Post to LinkedIn"""
    content = request.form.get('content')
    
    posts_count = get_posts_this_month(session['user_id'])
    if posts_count >= 5:
        return jsonify({'error': 'Monthly post limit reached (5/5). Upgrade to Pro for unlimited posts!'}), 403
    
    try:
        post_to_linkedin(session['user_id'], content)
        return jsonify({'success': True, 'posts_remaining': 5 - posts_count - 1})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/connection-status')
@login_required
def connection_status():
    """Check platform connection status"""
    return jsonify({
        'linkedin': is_platform_connected(session['user_id'], 'linkedin'),
        'posts_used': get_posts_this_month(session['user_id']),
        'posts_limit': 5
    })

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# ========== RUN APP ==========

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
