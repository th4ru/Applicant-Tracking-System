import re

def compute_candidate_match(candidate_data, job):
    """
    Evaluates candidate against a job's requirements and returns:
    - match_score: integer 0-100
    - ai_headline: quick summary string
    - ai_pros: list of strength highlights
    - ai_cons: list of gaps / areas to verify
    - ai_questions: list of 3 targeted phone-screen questions
    """
    required_skills = [s.strip().lower() for s in (job.required_skills or [])]
    nice_skills = [s.strip().lower() for s in (job.nice_to_have_skills or [])]
    
    cand_skills = [s.strip().lower() for s in (candidate_data.get("skills") or [])]
    cand_exp = float(candidate_data.get("years_of_experience") or 0)
    job_min_exp = float(job.min_years_experience or 0)
    
    resume_text = (candidate_data.get("raw_resume") or "").lower()
    
    # 1. Skill Overlap Calculation
    matched_required = []
    missing_required = []
    
    for r_skill in required_skills:
        # Check skill list or resume text
        if any(r_skill in c or c in r_skill for c in cand_skills) or re.search(r'\b' + re.escape(r_skill) + r'\b', resume_text):
            matched_required.append(r_skill)
        else:
            missing_required.append(r_skill)
            
    matched_nice = []
    for n_skill in nice_skills:
        if any(n_skill in c or c in n_skill for c in cand_skills) or re.search(r'\b' + re.escape(n_skill) + r'\b', resume_text):
            matched_nice.append(n_skill)
            
    # Compute skill score (0 - 50 points)
    if required_skills:
        req_ratio = len(matched_required) / len(required_skills)
        skill_score = req_ratio * 40
    else:
        skill_score = 35
        
    if nice_skills:
        nice_ratio = len(matched_nice) / len(nice_skills)
        skill_score += nice_ratio * 10
    else:
        skill_score += 10

    # 2. Experience Score (0 - 30 points)
    if job_min_exp <= 0:
        exp_score = 30
    else:
        if cand_exp >= job_min_exp:
            exp_score = min(30, 24 + ((cand_exp - job_min_exp) * 2))
        else:
            ratio = cand_exp / job_min_exp
            exp_score = max(5, ratio * 24)

    # 3. Context & Keyword Density (0 - 20 points)
    context_score = 12
    key_terms = ["lead", "architect", "scale", "performance", "api", "production", "ci/cd", "optimized", "cloud", "team"]
    hits = sum(1 for term in key_terms if term in resume_text)
    context_score += min(8, hits)
    
    total_score = int(round(skill_score + exp_score + context_score))
    total_score = max(15, min(99, total_score))  # clamp between 15 and 99
    
    # Generate structured Recruiter Insights
    pros = []
    cons = []
    
    # Pros
    if matched_required:
        pros.append(f"Direct match on {len(matched_required)}/{len(required_skills)} core skills: {', '.join([s.title() for s in matched_required[:4]])}")
    if matched_nice:
        pros.append(f"Bonus stack coverage: {', '.join([s.title() for s in matched_nice[:3]])}")
    if cand_exp >= job_min_exp:
        pros.append(f"Experience target met: {cand_exp:g} yrs vs {job_min_exp:g} yrs minimum required")
    elif cand_exp >= (job_min_exp - 1):
        pros.append(f"Close experience profile: {cand_exp:g} yrs with relevant modern tooling")
        
    if "lead" in resume_text or "architect" in resume_text:
        pros.append("Demonstrated leadership & architecture ownership on previous teams")
    elif total_score >= 80:
        pros.append("Strong domain portfolio and consistent career progression")

    # Cons / Gaps
    if missing_required:
        cons.append(f"Missing explicit proof of: {', '.join([s.title() for s in missing_required[:3]])}")
    if cand_exp < job_min_exp:
        cons.append(f"Experience gap: Has {cand_exp:g} yrs; role requests {job_min_exp:g}+ yrs")
    if not matched_nice and nice_skills:
        cons.append("Lacks secondary preferred technologies listed in job requisition")
    if len(cons) == 0:
        cons.append("High match profile; probe for compensation alignment and notice period")

    # Generate phone screen questions
    questions = []
    if missing_required:
        q_skill = missing_required[0].title()
        questions.append(f"How much hands-on production experience do you have with {q_skill}, and how have you applied it in prior roles?")
    else:
        top_skill = matched_required[0].title() if matched_required else "your core stack"
        questions.append(f"Can you walk through a high-impact system you designed or refactored using {top_skill}?")

    questions.append(f"In this role at {job.title}, what architectural trade-offs do you prioritize when balancing development speed vs maintainability?")
    questions.append(f"What type of engineering culture and team dynamic helps you do your best work?")

    headline = f"{total_score}% Match • {candidate_data.get('current_title', 'Candidate')} with {cand_exp:g} yrs exp"
    if matched_required:
        headline += f" in {', '.join([s.title() for s in matched_required[:2]])}"

    return {
        "match_score": total_score,
        "ai_headline": headline,
        "ai_pros": pros[:4],
        "ai_cons": cons[:3],
        "ai_questions": questions[:3]
    }
