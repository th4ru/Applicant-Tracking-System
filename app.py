import os
from dotenv import load_dotenv
from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from models import db
from routes.api import api_bp
from services.seed_data import seed_database

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # Configure Database
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'talentflow.db')
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    if not db_url:
        db_url = f'sqlite:///{db_path}'
        
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'talentflow-recruiter-ats-key-2026'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False
    )
    
    if test_config:
        app.config.update(test_config)

    CORS(app)
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "TalentFlow ATS",
            "version": "1.0.0"
        })

    # Initialize and seed database if empty and not in testing
    if not app.config.get('TESTING'):
        with app.app_context():
            db.create_all()
            from models import Job
            if Job.query.count() == 0:
                print("[TalentFlow] Seeding initial demo applicants dataset...")
                seed_database(target_count_per_job=30, force_clean=False)
                print("[TalentFlow] Seeding complete.")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
