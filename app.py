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

db = SQLAlchemy(app)

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = 'https://intelix.dev/linkedin/callback'

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea = db.Column(db.Text, nullable=False)
    business_name = db.Column(db.String(200))
    analysis = db.Column(db.Text)
    similar_idea = db.Column(db.Text)
    marketing_posts = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper function to check and reset monthly validations
def check_and_reset_monthly_limit(user):
    """Check if it's a new month and reset validation counter"""
    try:
        # Fix user if missing columns
        if user.validations_this_month is None:
            user.validations_this_month = 0
        if user.last_reset_date is None:
            user.last_reset_date = datetime.utcnow()
            db.session.commit()
            return 0
        
        now = datetime.utcnow()
        last_reset = user.last_reset_date
        
        # Check if we're in a new month
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
    """Get the date of next month's 1st"""
    now = datetime.utcnow()
    if now.month == 12:
        return datetime(now.year + 1, 1, 1)
    else:
        return datetime(now.year, now.month + 1, 1)

# Database Setup Routes
@app.route('/create-tables-now')
def create_tables():
    """Create all database tables"""
    try:
        with app.app_context():
            db.create_all()
        return "<h1>✅ All tables created successfully!</h1><p><a href='/dashboard'>Go to Dashboard</a></p><p><a href='/'>Go to Home</a></p>"
    except Exception as e:
        return f"<h1>❌ Error creating tables:</h1><p>{str(e)}</p>"

@app.route('/migrate-db-now')
def migrate_db():
    """One-time migration to add new columns"""
    try:
        from sqlalchemy import text
        
        with db.engine.connect() as conn:
            # Add validations_this_month column
            try:
                conn.execute(text('ALTER TABLE "user" ADD COLUMN validations_this_month INTEGER DEFAULT 0'))
                conn.commit()
                result1 = "✅ Added validations_this_month column"
            except Exception as e:
                result1 = f"ℹ️ validations_this_month: {str(e)}"
            
            # Add last_reset_date column
            try:
                conn.execute(text("ALTER TABLE \"user\" ADD COLUMN last_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()
                result2 = "✅ Added last_reset_date column"
            except Exception as e:
                result2 = f"ℹ️ last_reset_date: {str(e)}"
        
        return f"<h1>Migration Results:</h1><p>{result1}</p><p>{result2}</p><p><a href='/dashboard'>Go to Dashboard</a></p>"
    except Exception as e:
        return f"<h1>Migration Error:</h1><p>{str(e)}</p>"

@app.route('/fix-old-users-now')
def fix_old_users():
    """Add missing columns data to existing users"""
    try:
        from sqlalchemy import text
        
        with db.engine.connect() as conn:
            # Update all users to have default values for new columns
            try:
                conn.execute(text("UPDATE \"user\" SET validations_this_month = 0 WHERE validations_this_month IS NULL"))
                conn.execute(text("UPDATE \"user\" SET last_reset_date = CURRENT_TIMESTAMP WHERE last_reset_date IS NULL"))
                conn.commit()
                return "<h1>✅ All old users fixed!</h1><p>You can login now!</p><p><a href='/login'>Go to Login</a></p>"
            except Exception as e:
                conn.rollback()
                return f"<h1>❌ Error:</h1><p>{str(e)}</p>"
    except Exception as e:
        return f"<h1>❌ Error:</h1><p>{str(e)}</p>"

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
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
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Set session BEFORE checking monthly limit
            session['user_id'] = user.id
            
            # Fix user if missing columns
            try:
                if user.validations_this_month is None:
                    user.validations_this_month = 0
                if user.last_reset_date is None:
                    user.last_reset_date = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                print(f"Error fixing user columns: {e}")
            
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Check and reset monthly limit if needed
    validations_used = check_and_reset_monthly_limit(user)
    
    # Reset validation depth when visiting dashboard
    session['validation_depth'] = 0
    session.pop('original_validation_id', None)
    
    return render_template('dashboard.html', 
                         username=user.username, 
                         validation_count=validations_used,
                         validations_remaining=7 - validations_used)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Check and reset monthly limit if needed
    validations_used = check_and_reset_monthly_limit(user)
    
    # Check if user has reached monthly limit (7 validations)
    if validations_used >= 7:
        return render_template('limit_reached.html', 
                             validations_used=validations_used,
                             reset_date=get_next_reset_date())
    
    idea = request.form.get('idea')
    business_name = request.form.get('business_name', '')
    
    # Track validation depth
    validation_depth = session.get('validation_depth', 0) + 1
    session['validation_depth'] = validation_depth
    
    print(f"Analyzing idea (depth: {validation_depth}): {idea[:50]}...")
    
    # Get AI analysis
    analysis = analyze_business_idea(idea)
    
    # Generate similar idea only for first validation
    similar_idea = None
    if validation_depth == 1:
        similar_idea = generate_similar_idea(idea, analysis)
    
    # Save validation to database
    validation = Validation(
        user_id=user.id,
        idea=idea,
        business_name=business_name,
        analysis=json.dumps(analysis),
        similar_idea=json.dumps(similar_idea) if similar_idea else None
    )
    db.session.add(validation)
    
    # Increment monthly validation counter
    user.validations_this_month += 1
    
    db.session.commit()
    
    # Store original validation ID for back button
    if validation_depth == 1:
        session['original_validation_id'] = validation.id
    
    original_validation_id = session.get('original_validation_id')
    
    return render_template('analysis.html', 
                         idea=idea,
                         business_name=business_name,
                         analysis=analysis,
                         similar_idea=similar_idea,
                         validation_depth=validation_depth,
                         original_validation_id=original_validation_id)

@app.route('/validation/<int:validation_id>')
def view_validation(validation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    validation = Validation.query.get_or_404(validation_id)
    
    if validation.user_id != session['user_id']:
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
                         from_history=True)

@app.route('/marketing', methods=['POST'])
def marketing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    idea = request.form.get('idea', session.get('current_idea', ''))
    business_name = request.form.get('business_name', session.get('current_business_name', ''))
    
    session['current_idea'] = idea
    session['current_business_name'] = business_name
    
    print(f"Generating marketing posts for: {idea[:50]}...")
    
    posts = generate_linkedin_posts(idea, business_name)
    
    last_validation = Validation.query.filter_by(user_id=user.id).order_by(Validation.created_at.desc()).first()
    if last_validation:
        last_validation.marketing_posts = json.dumps(posts)
        db.session.commit()
    
    return render_template('marketing.html', 
                         idea=idea,
                         business_name=business_name,
                         posts=posts)

@app.route('/validations')
def validations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    user_validations = Validation.query.filter_by(user_id=user.id).order_by(Validation.created_at.desc()).all()
    
    return render_template('validations.html', validations=user_validations)

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Check and reset monthly limit
    validations_used = check_and_reset_monthly_limit(user)
    
    return render_template('settings.html', 
                         user=user,
                         validations_used=validations_used,
                         validations_remaining=7 - validations_used,
                         reset_date=get_next_reset_date())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# LinkedIn OAuth Routes
@app.route('/linkedin/auth')
def linkedin_auth():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={LINKEDIN_CLIENT_ID}&redirect_uri={LINKEDIN_REDIRECT_URI}&scope=openid%20profile%20w_member_social"
    
    return redirect(auth_url)

@app.route('/linkedin/callback')
def linkedin_callback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    code = request.args.get('code')
    
    if not code:
        return "LinkedIn authentication failed", 400
    
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
        
        return redirect(url_for('settings'))
    
    return "Failed to get access token", 400

@app.route('/post/linkedin', methods=['POST'])
def post_linkedin():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    user = User.query.get(session['user_id'])
    
    if not user.linkedin_access_token:
        return jsonify({'success': False, 'error': 'LinkedIn not connected'}), 400
    
    content = request.form.get('content')
    
    result = post_to_linkedin(user.linkedin_access_token, user.linkedin_user_id, content)
    
    if result['success']:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

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
