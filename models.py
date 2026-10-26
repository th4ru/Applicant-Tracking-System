from datetime import datetime, timezone
import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False, default="General")
    location = db.Column(db.String(100), nullable=False, default="Remote")
    job_type = db.Column(db.String(50), nullable=False, default="Full-time")
    experience_level = db.Column(db.String(50), nullable=False, default="Mid-Senior")
    description = db.Column(db.Text, nullable=False, default="")
    salary_range = db.Column(db.String(80), default="$120k - $160k")
    required_skills_json = db.Column(db.Text, nullable=False, default="[]")
    nice_to_have_skills_json = db.Column(db.Text, nullable=False, default="[]")
    min_years_experience = db.Column(db.Float, default=3.0)
    status = db.Column(db.String(20), default="active")  # active, closed, draft
    created_at = db.Column(db.DateTime, default=get_utc_now)

    candidates = db.relationship('Candidate', backref='job', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def required_skills(self):
        try:
            return json.loads(self.required_skills_json) if self.required_skills_json else []
        except Exception:
            return []

    @required_skills.setter
    def required_skills(self, skills):
        self.required_skills_json = json.dumps(skills if isinstance(skills, list) else [])

    @property
    def nice_to_have_skills(self):
        try:
            return json.loads(self.nice_to_have_skills_json) if self.nice_to_have_skills_json else []
        except Exception:
            return []

    @nice_to_have_skills.setter
    def nice_to_have_skills(self, skills):
        self.nice_to_have_skills_json = json.dumps(skills if isinstance(skills, list) else [])

    def to_dict(self, include_counts=False):
        data = {
            "id": self.id,
            "title": self.title,
            "department": self.department,
            "location": self.location,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "description": self.description,
            "salary_range": self.salary_range,
            "required_skills": self.required_skills,
            "nice_to_have_skills": self.nice_to_have_skills,
            "min_years_experience": self.min_years_experience,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_counts:
            # Aggregate counts by stage
            candidates_list = self.candidates.all()
            data["total_candidates"] = len(candidates_list)
            data["stage_counts"] = {
                "new": sum(1 for c in candidates_list if c.stage == 'new'),
                "screening": sum(1 for c in candidates_list if c.stage == 'screening'),
                "phone_screen": sum(1 for c in candidates_list if c.stage == 'phone_screen'),
                "interview": sum(1 for c in candidates_list if c.stage == 'interview'),
                "offer": sum(1 for c in candidates_list if c.stage == 'offer'),
                "hired": sum(1 for c in candidates_list if c.stage == 'hired'),
                "rejected": sum(1 for c in candidates_list if c.stage == 'rejected'),
            }
        return data


class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), default="")
    location = db.Column(db.String(100), default="Remote")
    current_title = db.Column(db.String(120), default="Software Engineer")
    current_company = db.Column(db.String(120), default="")
    years_of_experience = db.Column(db.Float, default=2.0)
    education = db.Column(db.String(200), default="B.S. in Computer Science")
    skills_json = db.Column(db.Text, default="[]")
    raw_resume = db.Column(db.Text, default="")
    portfolio_url = db.Column(db.String(255), default="")
    linkedin_url = db.Column(db.String(255), default="")
    github_url = db.Column(db.String(255), default="")
    
    stage = db.Column(db.String(30), default='new', index=True)
    match_score = db.Column(db.Integer, default=50, index=True)
    ai_headline = db.Column(db.String(255), default="")
    ai_pros_json = db.Column(db.Text, default="[]")
    ai_cons_json = db.Column(db.Text, default="[]")
    ai_questions_json = db.Column(db.Text, default="[]")
    
    starred = db.Column(db.Boolean, default=False, index=True)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 rating
    applied_at = db.Column(db.DateTime, default=get_utc_now, index=True)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)

    notes = db.relationship('CandidateNote', backref='candidate', cascade='all, delete-orphan', order_by='CandidateNote.created_at.desc()')
    activity_logs = db.relationship('ActivityLog', backref='candidate', cascade='all, delete-orphan', order_by='ActivityLog.timestamp.desc()')

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json) if self.skills_json else []
        except Exception:
            return []

    @skills.setter
    def skills(self, skills_list):
        self.skills_json = json.dumps(skills_list if isinstance(skills_list, list) else [])

    @property
    def ai_pros(self):
        try:
            return json.loads(self.ai_pros_json) if self.ai_pros_json else []
        except Exception:
            return []

    @ai_pros.setter
    def ai_pros(self, items):
        self.ai_pros_json = json.dumps(items if isinstance(items, list) else [])

    @property
    def ai_cons(self):
        try:
            return json.loads(self.ai_cons_json) if self.ai_cons_json else []
        except Exception:
            return []

    @ai_cons.setter
    def ai_cons(self, items):
        self.ai_cons_json = json.dumps(items if isinstance(items, list) else [])

    @property
    def ai_questions(self):
        try:
            return json.loads(self.ai_questions_json) if self.ai_questions_json else []
        except Exception:
            return []

    @ai_questions.setter
    def ai_questions(self, items):
        self.ai_questions_json = json.dumps(items if isinstance(items, list) else [])

    def to_dict(self, full=False):
        data = {
            "id": self.id,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else "Unknown Role",
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "current_title": self.current_title,
            "current_company": self.current_company,
            "years_of_experience": self.years_of_experience,
            "education": self.education,
            "skills": self.skills,
            "portfolio_url": self.portfolio_url,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "stage": self.stage,
            "match_score": self.match_score,
            "ai_headline": self.ai_headline,
            "starred": self.starred,
            "rating": self.rating,
            "applied_at": self.applied_at.strftime("%b %d, %Y") if self.applied_at else "",
            "applied_at_iso": self.applied_at.isoformat() if self.applied_at else "",
            "notes_count": len(self.notes),
        }
        if full:
            data.update({
                "raw_resume": self.raw_resume,
                "ai_pros": self.ai_pros,
                "ai_cons": self.ai_cons,
                "ai_questions": self.ai_questions,
                "notes": [n.to_dict() for n in self.notes],
                "activity_logs": [a.to_dict() for a in self.activity_logs],
            })
        return data


class CandidateNote(db.Model):
    __tablename__ = 'candidate_notes'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    author = db.Column(db.String(80), default="Recruiter")
    category = db.Column(db.String(50), default="Screening")
    rating = db.Column(db.Integer, nullable=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "author": self.author,
            "category": self.category,
            "rating": self.rating,
            "text": self.text,
            "created_at": self.created_at.strftime("%b %d, %Y %I:%M %p") if self.created_at else "",
            "created_at_iso": self.created_at.isoformat() if self.created_at else "",
        }


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    actor = db.Column(db.String(80), default="Recruiter")
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.String(255), default="")
    timestamp = db.Column(db.DateTime, default=get_utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.strftime("%b %d, %I:%M %p") if self.timestamp else "",
            "timestamp_iso": self.timestamp.isoformat() if self.timestamp else "",
        }
