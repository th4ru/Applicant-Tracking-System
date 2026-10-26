import io
import csv
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, Response
from models import db, Job, Candidate, CandidateNote, ActivityLog
from services.scoring import compute_candidate_match
from services.seed_data import seed_database

def utcnow():
    return datetime.now(timezone.utc)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== JOBS ENDPOINTS ====================

@api_bp.route('/jobs', methods=['GET'])
def get_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict(include_counts=True) for j in jobs])

@api_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    job = Job.query.get_or_404(job_id)
    return jsonify(job.to_dict(include_counts=True))

@api_bp.route('/jobs', methods=['POST'])
def create_job():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"error": "Job title is required"}), 400

    job = Job(
        title=title,
        department=data.get('department', 'Engineering'),
        location=data.get('location', 'Remote'),
        job_type=data.get('job_type', 'Full-time'),
        experience_level=data.get('experience_level', 'Mid-Senior'),
        description=data.get('description', ''),
        salary_range=data.get('salary_range', '$120k - $160k'),
        min_years_experience=float(data.get('min_years_experience', 3.0)),
        status=data.get('status', 'active')
    )
    job.required_skills = data.get('required_skills', [])
    job.nice_to_have_skills = data.get('nice_to_have_skills', [])

    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict(include_counts=True)), 201


# ==================== CANDIDATES ENDPOINTS ====================

@api_bp.route('/candidates', methods=['GET'])
def get_candidates():
    query = Candidate.query

    # Filter: Job ID
    job_id = request.args.get('job_id')
    if job_id and job_id.isdigit():
        query = query.filter(Candidate.job_id == int(job_id))

    # Filter: Stage
    stage = request.args.get('stage')
    if stage and stage != 'all':
        query = query.filter(Candidate.stage == stage)

    # Filter: Starred
    starred = request.args.get('starred')
    if starred is not None and starred.lower() in ['true', '1']:
        query = query.filter(Candidate.starred == True)

    # Filter: Score Range
    min_score = request.args.get('min_score')
    if min_score and min_score.isdigit():
        query = query.filter(Candidate.match_score >= int(min_score))

    max_score = request.args.get('max_score')
    if max_score and max_score.isdigit():
        query = query.filter(Candidate.match_score <= int(max_score))

    # Filter: Min Experience
    min_exp = request.args.get('min_exp')
    if min_exp:
        try:
            query = query.filter(Candidate.years_of_experience >= float(min_exp))
        except ValueError:
            pass

    # Filter: Full Text Search across Name, Email, Title, Company, Resume, Skills
    search = request.args.get('search', '').strip().lower()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Candidate.name.ilike(search_pattern),
                Candidate.email.ilike(search_pattern),
                Candidate.current_title.ilike(search_pattern),
                Candidate.current_company.ilike(search_pattern),
                Candidate.skills_json.ilike(search_pattern),
                Candidate.raw_resume.ilike(search_pattern)
            )
        )

    # Sorting
    sort_by = request.args.get('sort_by', 'score_desc')
    if sort_by == 'score_desc':
        query = query.order_by(Candidate.match_score.desc(), Candidate.applied_at.desc())
    elif sort_by == 'score_asc':
        query = query.order_by(Candidate.match_score.asc(), Candidate.applied_at.desc())
    elif sort_by == 'applied_desc':
        query = query.order_by(Candidate.applied_at.desc())
    elif sort_by == 'applied_asc':
        query = query.order_by(Candidate.applied_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Candidate.name.asc())
    elif sort_by == 'exp_desc':
        query = query.order_by(Candidate.years_of_experience.desc())
    else:
        query = query.order_by(Candidate.match_score.desc())

    # Pagination
    total = query.count()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(5, int(request.args.get('per_page', 25))))

    candidates = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return jsonify({
        "candidates": [c.to_dict(full=False) for c in candidates],
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    })

@api_bp.route('/candidates/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    return jsonify(candidate.to_dict(full=True))

@api_bp.route('/candidates', methods=['POST'])
def create_candidate():
    data = request.get_json() or {}
    job_id = data.get('job_id')
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()

    if not job_id or not name or not email:
        return jsonify({"error": "job_id, name, and email are required"}), 400

    job = Job.query.get_or_404(job_id)

    years_exp = float(data.get('years_of_experience', 2.0))
    skills = data.get('skills', [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',') if s.strip()]

    raw_resume = data.get('raw_resume', '')
    if not raw_resume:
        raw_resume = f"# {name}\n**{data.get('current_title', 'Software Engineer')}**\n\nExperience: {years_exp} years.\nSkills: {', '.join(skills)}"

    match_data = compute_candidate_match({
        "skills": skills,
        "years_of_experience": years_exp,
        "raw_resume": raw_resume,
        "current_title": data.get('current_title', '')
    }, job)

    candidate = Candidate(
        job_id=job.id,
        name=name,
        email=email,
        phone=data.get('phone', ''),
        location=data.get('location', 'Remote'),
        current_title=data.get('current_title', 'Software Engineer'),
        current_company=data.get('current_company', ''),
        years_of_experience=years_exp,
        education=data.get('education', 'B.S. in Computer Science'),
        raw_resume=raw_resume,
        portfolio_url=data.get('portfolio_url', ''),
        linkedin_url=data.get('linkedin_url', ''),
        github_url=data.get('github_url', ''),
        stage=data.get('stage', 'new'),
        match_score=match_data["match_score"],
        ai_headline=match_data["ai_headline"]
    )
    candidate.skills = skills
    candidate.ai_pros = match_data["ai_pros"]
    candidate.ai_cons = match_data["ai_cons"]
    candidate.ai_questions = match_data["ai_questions"]

    db.session.add(candidate)
    db.session.flush()

    log = ActivityLog(
        candidate_id=candidate.id,
        actor="Recruiter",
        action="Application Created",
        details=f"Manually added applicant for {job.title}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(candidate.to_dict(full=True)), 201

@api_bp.route('/candidates/<int:candidate_id>/stage', methods=['PATCH'])
def update_candidate_stage(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    data = request.get_json() or {}
    new_stage = data.get('stage')
    actor = data.get('actor', 'Recruiter')
    note_text = data.get('note', '')

    valid_stages = ['new', 'screening', 'phone_screen', 'interview', 'offer', 'hired', 'rejected']
    if new_stage not in valid_stages:
        return jsonify({"error": f"Invalid stage. Allowed: {valid_stages}"}), 400

    old_stage = candidate.stage
    candidate.stage = new_stage
    candidate.updated_at = utcnow()

    log = ActivityLog(
        candidate_id=candidate.id,
        actor=actor,
        action=f"Stage changed: {old_stage.title()} → {new_stage.title()}",
        details=note_text if note_text else f"Moved candidate to {new_stage.replace('_', ' ').title()}"
    )
    db.session.add(log)

    if note_text:
        note = CandidateNote(
            candidate_id=candidate.id,
            author=actor,
            category="Stage Update",
            text=note_text
        )
        db.session.add(note)

    db.session.commit()
    return jsonify({
        "success": True,
        "candidate": candidate.to_dict(full=True)
    })

@api_bp.route('/candidates/<int:candidate_id>/star', methods=['PATCH'])
def toggle_candidate_star(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    candidate.starred = not candidate.starred
    candidate.updated_at = utcnow()

    log = ActivityLog(
        candidate_id=candidate.id,
        actor="Recruiter",
        action="Starred Candidate" if candidate.starred else "Unstarred Candidate",
        details="Toggled star status"
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "starred": candidate.starred})

@api_bp.route('/candidates/<int:candidate_id>/rating', methods=['PATCH'])
def update_candidate_rating(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    data = request.get_json() or {}
    rating = data.get('rating')

    if rating is not None:
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                rating = None
        except ValueError:
            rating = None

    candidate.rating = rating
    candidate.updated_at = utcnow()

    log = ActivityLog(
        candidate_id=candidate.id,
        actor="Recruiter",
        action=f"Updated rating to {rating}/5" if rating else "Cleared rating",
        details="Recruiter scorecard evaluation"
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "rating": candidate.rating})

@api_bp.route('/candidates/<int:candidate_id>/notes', methods=['POST'])
def add_candidate_note(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    data = request.get_json() or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({"error": "Note text is required"}), 400

    author = data.get('author', 'Recruiter')
    category = data.get('category', 'Screening')
    rating = data.get('rating')
    if rating:
        try:
            rating = int(rating)
            candidate.rating = rating
        except ValueError:
            rating = None

    note = CandidateNote(
        candidate_id=candidate.id,
        author=author,
        category=category,
        rating=rating,
        text=text
    )
    db.session.add(note)

    log = ActivityLog(
        candidate_id=candidate.id,
        actor=author,
        action="Added Note",
        details=f"Category: {category}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": True,
        "note": note.to_dict(),
        "candidate": candidate.to_dict(full=True)
    }), 201

@api_bp.route('/candidates/<int:candidate_id>/rescore', methods=['POST'])
def rescore_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    job = candidate.job

    match_data = compute_candidate_match({
        "skills": candidate.skills,
        "years_of_experience": candidate.years_of_experience,
        "raw_resume": candidate.raw_resume,
        "current_title": candidate.current_title
    }, job)

    candidate.match_score = match_data["match_score"]
    candidate.ai_headline = match_data["ai_headline"]
    candidate.ai_pros = match_data["ai_pros"]
    candidate.ai_cons = match_data["ai_cons"]
    candidate.ai_questions = match_data["ai_questions"]
    candidate.updated_at = utcnow()

    log = ActivityLog(
        candidate_id=candidate.id,
        actor="AI Assistant",
        action="Candidate Rescored",
        details=f"New match score: {candidate.match_score}%"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "success": True,
        "candidate": candidate.to_dict(full=True)
    })


# ==================== BULK ACTIONS (CRITICAL FOR HIGH VOLUME) ====================

@api_bp.route('/candidates/bulk-stage', methods=['POST'])
def bulk_update_stage():
    """
    Bulk moves selected candidate IDs to a new stage in one swift recruiter action.
    """
    data = request.get_json() or {}
    candidate_ids = data.get('candidate_ids', [])
    new_stage = data.get('stage')
    actor = data.get('actor', 'Recruiter')

    valid_stages = ['new', 'screening', 'phone_screen', 'interview', 'offer', 'hired', 'rejected']
    if not candidate_ids or not isinstance(candidate_ids, list):
        return jsonify({"error": "candidate_ids array is required"}), 400
    if new_stage not in valid_stages:
        return jsonify({"error": f"Invalid stage. Allowed: {valid_stages}"}), 400

    candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    count = 0
    now = utcnow()

    for c in candidates:
        old_stage = c.stage
        c.stage = new_stage
        c.updated_at = now
        log = ActivityLog(
            candidate_id=c.id,
            actor=actor,
            action=f"Bulk Moved to {new_stage.replace('_', ' ').title()}",
            details=f"Bulk action moved from {old_stage} to {new_stage}",
            timestamp=now
        )
        db.session.add(log)
        count += 1

    db.session.commit()
    return jsonify({
        "success": True,
        "updated_count": count,
        "stage": new_stage
    })

@api_bp.route('/candidates/bulk-reject', methods=['POST'])
def bulk_reject_candidates():
    """
    Bulk rejects candidates with optional disposition reason and logs the decision.
    """
    data = request.get_json() or {}
    candidate_ids = data.get('candidate_ids', [])
    reason = data.get('reason', 'Role requirements mismatch')
    actor = data.get('actor', 'Recruiter')

    if not candidate_ids or not isinstance(candidate_ids, list):
        return jsonify({"error": "candidate_ids array is required"}), 400

    candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    count = 0
    now = utcnow()

    for c in candidates:
        c.stage = 'rejected'
        c.updated_at = now
        log = ActivityLog(
            candidate_id=c.id,
            actor=actor,
            action="Bulk Rejected",
            details=f"Reason: {reason}",
            timestamp=now
        )
        db.session.add(log)
        count += 1

    db.session.commit()
    return jsonify({
        "success": True,
        "rejected_count": count,
        "reason": reason
    })

@api_bp.route('/candidates/bulk-email', methods=['POST'])
def bulk_email_candidates():
    """
    Simulates sending templated email notifications to selected candidates.
    Recruiters love this because writing 50 emails one by one takes hours.
    """
    data = request.get_json() or {}
    candidate_ids = data.get('candidate_ids', [])
    template = data.get('template', 'interview_invite')  # interview_invite, rejection, update
    subject = data.get('subject', 'Update regarding your application')
    body_template = data.get('body', 'Hello {{name}}, thank you for your application to {{job_title}}.')
    actor = data.get('actor', 'Recruiter')

    if not candidate_ids or not isinstance(candidate_ids, list):
        return jsonify({"error": "candidate_ids array is required"}), 400

    candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    sent_logs = []
    now = utcnow()

    for c in candidates:
        log = ActivityLog(
            candidate_id=c.id,
            actor=actor,
            action=f"Bulk Email Sent ({template.replace('_', ' ').title()})",
            details=f"Subject: {subject}",
            timestamp=now
        )
        db.session.add(log)
        sent_logs.append({
            "candidate_id": c.id,
            "name": c.name,
            "email": c.email,
            "status": "sent"
        })

    db.session.commit()
    return jsonify({
        "success": True,
        "sent_count": len(sent_logs),
        "dispatches": sent_logs
    })


# ==================== ANALYTICS & EXPORT ====================

@api_bp.route('/analytics', methods=['GET'])
def get_analytics():
    job_id = request.args.get('job_id')
    query = Candidate.query
    if job_id and job_id.isdigit():
        query = query.filter(Candidate.job_id == int(job_id))

    all_candidates = query.all()
    total = len(all_candidates)

    stage_order = ['new', 'screening', 'phone_screen', 'interview', 'offer', 'hired', 'rejected']
    stages_count = {s: 0 for s in stage_order}
    for c in all_candidates:
        stages_count[c.stage] = stages_count.get(c.stage, 0) + 1

    # Score breakdown
    score_buckets = {
        "90-100% (Top Match)": sum(1 for c in all_candidates if c.match_score >= 90),
        "75-89% (Strong Fit)": sum(1 for c in all_candidates if 75 <= c.match_score < 90),
        "50-74% (Moderate)": sum(1 for c in all_candidates if 50 <= c.match_score < 75),
        "<50% (Low Match)": sum(1 for c in all_candidates if c.match_score < 50),
    }

    # Top skills across candidate pool
    skills_freq = {}
    for c in all_candidates:
        for s in c.skills:
            clean_s = s.strip()
            skills_freq[clean_s] = skills_freq.get(clean_s, 0) + 1

    sorted_skills = sorted(skills_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # Average score
    avg_score = round(sum(c.match_score for c in all_candidates) / total, 1) if total > 0 else 0

    return jsonify({
        "total_candidates": total,
        "avg_match_score": avg_score,
        "stages_funnel": [
            {"stage": s, "label": s.replace('_', ' ').title(), "count": stages_count[s]}
            for s in stage_order
        ],
        "score_distribution": score_buckets,
        "top_skills": [{"skill": s, "count": count} for s, count in sorted_skills],
    })

@api_bp.route('/export', methods=['GET'])
def export_candidates_csv():
    """
    Exports candidates to CSV matching current query filters.
    """
    query = Candidate.query
    job_id = request.args.get('job_id')
    if job_id and job_id.isdigit():
        query = query.filter(Candidate.job_id == int(job_id))

    stage = request.args.get('stage')
    if stage and stage != 'all':
        query = query.filter(Candidate.stage == stage)

    candidates = query.order_by(Candidate.match_score.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Job Title", "Name", "Email", "Phone", "Location", "Current Title",
        "Current Company", "Years Experience", "Education", "Match Score (%)",
        "Stage", "Starred", "Rating", "Skills", "Applied Date"
    ])

    for c in candidates:
        writer.writerow([
            c.id,
            c.job.title if c.job else "",
            c.name,
            c.email,
            c.phone,
            c.location,
            c.current_title,
            c.current_company,
            c.years_of_experience,
            c.education,
            c.match_score,
            c.stage,
            "Yes" if c.starred else "No",
            c.rating or "",
            ", ".join(c.skills),
            c.applied_at.strftime("%Y-%m-%d %H:%M") if c.applied_at else ""
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=applicants_export_{utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@api_bp.route('/reset-demo', methods=['POST'])
def reset_demo():
    """
    Re-seeds database with fresh set of realistic candidates across all jobs.
    """
    jobs_count, candidates_count = seed_database(target_count_per_job=30, force_clean=True)
    return jsonify({
        "success": True,
        "message": f"Successfully re-seeded {jobs_count} job positions and {candidates_count} applicant profiles."
    })
