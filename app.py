from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from utils.ai_analyzer import analyze_business_idea, generate_similar_idea
from utils.linkedin_poster import post_to_linkedin, generate_linkedin_posts
import json
import requests
import base64

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,
    'max_overflow': 20
}

db = SQLAlchemy(app)

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI', 'https://intelix.dev/linkedin/callback')

# DEVELOPER MODE - UNLIMITED VALIDATIONS
DEVELOPER_USERS = ['ved@intelix.com']

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    linkedin_access_token = db.Column(db.String(500))
    linkedin_user_id = db.Column(db.String(100))
    validations_this_month = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    validations = db.relationship('Validation', backref='user', lazy=True)

class Validation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    idea = db.Column(db.Text, nullable=False)
    business_name = db.Column(db.String(200))
    analysis = db.Column(db.Text)
    similar_idea = db.Column(db.Text)
    marketing_posts = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100))

def check_and_reset_monthly_limit(user):
    try:
        if user.validations_this_month is None:
            user.validations_this_month = 0
        if user.last_reset_date is None:
            user.last_reset_date = datetime.utcnow()
            db.session.commit()
            return 0
        
        now = datetime.utcnow()
        last_reset = user.last_reset_date
        
        if last_reset.month != now.month or last_reset.year != now.year:
            user.validations_this_month = 0
            user.last_reset_date = now
            db.session.commit()
            print(f"Reset validations for user {user.username} - New month!")
        
        return user.validations_this_month
    except Exception as e:
        print(f"Error in check_and_reset_monthly_limit: {e}")
        return 0

def get_next_reset_date():
    now = datetime.utcnow()
    if now.month == 12:
        return datetime(now.year + 1, 1, 1)
    else:
        return datetime(now.year, now.month + 1, 1)

def is_developer(user):
    return user.username in DEVELOPER_USERS

def get_free_validation_count():
    """Get number of free validations used in this session"""
    return session.get('free_validations', 0)

def increment_free_validation():
    """Increment free validation counter"""
    count = session.get('free_validations', 0)
    session['free_validations'] = count + 1
    return session['free_validations']

# Database Setup Routes
@app.route('/create-tables-now')
def create_tables():
    try:
        with app.app_context():
            db.create_all()
        return "<h1>✅ All tables created successfully!</h1><p><a href='/home'>Go to Home</a></p>"
    except Exception as e:
        return f"<h1>❌ Error creating tables:</h1><p>{str(e)}</p>"

@app.route('/migrate-db-now')
def migrate_db():
    try:
        from sqlalchemy import text
        
        with db.engine.connect() as conn:
            try:
                conn.execute(text('ALTER TABLE "user" ADD COLUMN validations_this_month INTEGER DEFAULT 0'))
                conn.commit()
                result1 = "✅ Added validations_this_month column"
            except Exception as e:
                result1 = f"ℹ️ validations_this_month: {str(e)}"
            
            try:
                conn.execute(text("ALTER TABLE \"user\" ADD COLUMN last_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()
                result2 = "✅ Added last_reset_date column"
            except Exception as e:
                result2 = f"ℹ️ last_reset_date: {str(e)}"
            
            try:
                conn.execute(text('ALTER TABLE "validation" ADD COLUMN session_id VARCHAR(100)'))
                conn.commit()
                result3 = "✅ Added session_id column to validation"
            except Exception as e:
                result3 = f"ℹ️ session_id: {str(e)}"
        
        return f"<h1>Migration Results:</h1><p>{result1}</p><p>{result2}</p><p>{result3}</p><p><a href='/home'>Go to Home</a></p>"
    except Exception as e:
        return f"<h1>Migration Error:</h1><p>{str(e)}</p>"

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    # Get current validation count
    free_count = get_free_validation_count()
    
    # Get recent validations from session
    session_id = session.get('session_id')
    recent_validations = []
    
    if session_id:
        recent_validations = Validation.query.filter_by(session_id=session_id).order_by(Validation.created_at.desc()).limit(3).all()
    
    return render_template('home.html', validation_count=free_count, recent_validations=recent_validations)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if User.query.filter_by(username=username).first():
                return render_template('signup.html', error='Username already exists')
            
            if User.query.filter_by(email=email).first():
                return render_template('signup.html', error='Email already registered')
            
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username, 
                email=email, 
                password=hashed_password,
                validations_this_month=0,
                last_reset_date=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            
            # Transfer session validations to user
            session_id = session.get('session_id')
            if session_id:
                Validation.query.filter_by(session_id=session_id).update({'user_id': new_user.id, 'session_id': None})
                db.session.commit()
            
            # Redirect to LinkedIn auth
            return redirect(url_for('linkedin_auth'))
        except Exception as e:
            print(f"Signup error: {e}")
            db.session.rollback()
            return render_template('signup.html', error='An error occurred. Please try again.')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            print(f"Login attempt for username: {username}")
            
            if not username or not password:
                return render_template('login.html', error='Please enter both username and password')
            
            user = User.query.filter_by(username=username).first()
            
            print(f"User found: {user is not None}")
            
            if user and check_password_hash(user.password, password):
                print(f"Password verified for user: {username}")
                
                session['user_id'] = user.id
                
                try:
                    if user.validations_this_month is None:
                        user.validations_this_month = 0
                    if user.last_reset_date is None:
                        user.last_reset_date = datetime.utcnow()
                    db.session.commit()
                    print(f"User columns fixed for: {username}")
                except Exception as e:
                    print(f"Error fixing user columns: {e}")
                    db.session.rollback()
                
                print(f"Redirecting to home for user: {username}")
                return redirect(url_for('home'))
            else:
                print(f"Invalid credentials for username: {username}")
                return render_template('login.html', error='Invalid username or password')
        
        except Exception as e:
            print(f"Login error: {e}")
            db.session.rollback()
            return render_template('login.html', error='An error occurred. Please try again.')
    
    return render_template('login.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Check if user is logged in
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        
        # If not logged in, unlimited validations for now
        if not user:
            free_count = get_free_validation_count()
            # No limit enforced - allow unlimited free validations
        
        # Check developer mode or monthly limit for logged-in users
        if user:
            developer_mode = is_developer(user)
            
            if not developer_mode:
                validations_used = check_and_reset_monthly_limit(user)
                
                if validations_used >= 7:
                    return render_template('limit_reached.html', 
                                         validations_used=validations_used,
                                         reset_date=get_next_reset_date())
            else:
                print(f"🔓 Developer mode: Unlimited validations for {user.username}")
        
        idea = request.form.get('idea')
        business_name = request.form.get('business_name', '')
        
        validation_depth = session.get('validation_depth', 0) + 1
        session['validation_depth'] = validation_depth
        
        print(f"Analyzing idea (depth: {validation_depth}): {idea[:50]}...")
        
        # Get AI analysis
        analysis = analyze_business_idea(idea)
        
        # Generate similar idea only for first validation
        similar_idea = None
        if validation_depth == 1:
            similar_idea = generate_similar_idea(idea, analysis)
        
        # Generate session ID if not logged in
        if not user:
            if 'session_id' not in session:
                session['session_id'] = os.urandom(16).hex()
            session_id = session['session_id']
        else:
            session_id = None
        
        # Save validation to database
        validation = Validation(
            user_id=user.id if user else None,
            session_id=session_id,
            idea=idea,
            business_name=business_name,
            analysis=json.dumps(analysis),
            similar_idea=json.dumps(similar_idea) if similar_idea else None
        )
        db.session.add(validation)
        
        # Increment counters
        if user and not is_developer(user):
            user.validations_this_month += 1
        elif not user:
            increment_free_validation()
        
        db.session.commit()
        
        if validation_depth == 1:
            session['original_validation_id'] = validation.id
        
        original_validation_id = session.get('original_validation_id')
        
        return render_template('analysis.html', 
                             idea=idea,
                             business_name=business_name,
                             analysis=analysis,
                             similar_idea=similar_idea,
                             validation_depth=validation_depth,
                             original_validation_id=original_validation_id,
                             is_logged_in='user_id' in session)
    
    except Exception as e:
        print(f"Analyze error: {e}")
        db.session.rollback()
        return render_template('home.html', 
                             error='An error occurred. Please try again.')

@app.route('/validation/<int:validation_id>')
def view_validation(validation_id):
    try:
        validation = Validation.query.get_or_404(validation_id)
        
        # Check if user owns this validation (either logged in or session matches)
        user_id = session.get('user_id')
        session_id = session.get('session_id')
        
        if validation.user_id:
            if not user_id or validation.user_id != user_id:
                return "Unauthorized", 403
        elif validation.session_id:
            if validation.session_id != session_id:
                return "Unauthorized", 403
        
        analysis = json.loads(validation.analysis)
        similar_idea = json.loads(validation.similar_idea) if validation.similar_idea else None
        marketing_posts = json.loads(validation.marketing_posts) if validation.marketing_posts else None
        
        return render_template('analysis.html',
                             idea=validation.idea,
                             business_name=validation.business_name,
                             analysis=analysis,
                             similar_idea=similar_idea,
                             marketing_posts=marketing_posts,
                             validation_depth=1,
                             from_history=True,
                             is_logged_in='user_id' in session)
    except Exception as e:
        print(f"View validation error: {e}")
        return redirect(url_for('home'))

@app.route('/marketing', methods=['POST'])
def marketing():
    try:
        idea = request.form.get('idea', '')
        business_name = request.form.get('business_name', '')
        
        if not idea:
            print("ERROR: No idea provided in marketing route!")
            return "<h1>❌ Error: No idea provided</h1><p><a href='/home'>Back to Home</a></p>"
        
        print(f"Generating marketing posts for: {idea[:50]}...")
        
        posts = generate_linkedin_posts(idea, business_name)
        
        # Check if user is logged in
        is_logged_in = 'user_id' in session
        
        # Save to database
        if is_logged_in:
            user = User.query.get(session['user_id'])
            last_validation = Validation.query.filter_by(user_id=user.id).order_by(Validation.created_at.desc()).first()
            if last_validation:
                last_validation.marketing_posts = json.dumps(posts)
                db.session.commit()
        else:
            # Save to session-based validation
            session_id = session.get('session_id')
            if session_id:
                last_validation = Validation.query.filter_by(session_id=session_id).order_by(Validation.created_at.desc()).first()
                if last_validation:
                    last_validation.marketing_posts = json.dumps(posts)
                    db.session.commit()
        
        return render_template('marketing.html', 
                             idea=idea,
                             business_name=business_name,
                             posts=posts,
                             is_logged_in=is_logged_in,
                             show_signup_popup=not is_logged_in)
    except Exception as e:
        print(f"Marketing error: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return f"<h1>❌ Error generating marketing posts:</h1><p>{str(e)}</p><p><a href='/home'>Back to Home</a></p>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# LinkedIn OAuth Routes
@app.route('/linkedin/auth')
def linkedin_auth():
    if 'user_id' not in session:
        return redirect(url_for('signup'))
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={LINKEDIN_CLIENT_ID}&redirect_uri={LINKEDIN_REDIRECT_URI}&scope=openid%20profile%20w_member_social"
    
    return redirect(auth_url)

@app.route('/linkedin/callback')
def linkedin_callback():
    if 'user_id' not in session:
        return redirect(url_for('signup'))
    
    try:
        code = request.args.get('code')
        
        if not code:
            return redirect(url_for('home'))
        
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': LINKEDIN_REDIRECT_URI,
            'client_id': LINKEDIN_CLIENT_ID,
            'client_secret': LINKEDIN_CLIENT_SECRET
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        access_token = token_json.get('access_token')
        
        if access_token:
            user = User.query.get(session['user_id'])
            user.linkedin_access_token = access_token
            
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers).json()
            user.linkedin_user_id = user_info.get('sub')
            
            db.session.commit()
            
            return redirect(url_for('home'))
        
        return redirect(url_for('home'))
    except Exception as e:
        print(f"LinkedIn callback error: {e}")
        db.session.rollback()
        return redirect(url_for('home'))

@app.route('/post/linkedin', methods=['POST'])
def post_linkedin():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        user = User.query.get(session['user_id'])
        
        if not user.linkedin_access_token:
            return jsonify({'success': False, 'error': 'LinkedIn not connected'}), 400
        
        content = request.form.get('content')
        
        result = post_to_linkedin(user.linkedin_access_token, user.linkedin_user_id, content)
        
        if result['success']:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result['error']}), 400
    except Exception as e:
        print(f"Post LinkedIn error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate-voiceover', methods=['POST'])
def generate_voiceover_route():
    try:
        from utils.voiceover_generator import generate_voiceover
        
        data = request.get_json()
        script = data.get('script', '')
        
        if not script:
            return jsonify({'success': False, 'error': 'No script provided'}), 400
        
        print(f"Generating voiceover for script: {script[:50]}...")
        
        audio_content = generate_voiceover(script)
        
        if audio_content:
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            return jsonify({
                'success': True,
                'audio': audio_base64
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate voiceover'}), 500
            
    except Exception as e:
        print(f"Voiceover generation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
