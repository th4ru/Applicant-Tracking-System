import random
from datetime import datetime, timezone, timedelta
from models import db, Job, Candidate, CandidateNote, ActivityLog
from services.scoring import compute_candidate_match

def utcnow():
    return datetime.now(timezone.utc)

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Cameron", "Dakota",
    "Elena", "Marcus", "Priya", "Chen", "Aisha", "Mateo", "Sophie", "Lucas", "Yuki", "Devon",
    "Fatima", "Liam", "Zoe", "Kavya", "Hiroshi", "Chloe", "Dmitri", "Nia", "Gabriel", "Maya",
    "Tariq", "Hanna", "Arjun", "Leila", "Diego", "Amara", "Viktor", "Mei", "Sean", "Ananya",
    "Julian", "Sora", "Beatriz", "Kofi", "Freja", "Rohan", "Ines", "Kenji", "Zara", "Felix"
]

LAST_NAMES = [
    "Vance", "Mercer", "Chen", "Patel", "Novak", "O'Connor", "Kim", "Santos", "Tanaka", "Larsson",
    "Al-Mansoor", "Dubois", "Kowalski", "Gupta", "Moreno", "Nakamura", "Becker", "Diallo", "Lindqvist", "Rossi",
    "Sharma", "Zhang", "Fischer", "Mendoza", "Okafor", "Svensson", "Watanabe", "Hernandez", "Bauer", "Popov"
]

COMPANIES = [
    "Stripe", "Datadog", "Airbnb", "Shopify", "Cloudflare", "Figma", "Notion", "Vercel",
    "Scale AI", "Brex", "DoorDash", "Pinterest", "Robinhood", "Instacart", "Twilio", "GitLab",
    "HubSpot", "Dropbox", "Coinbase", "Segment", "Linear", "Ramp", "Supabase", "Retool"
]

LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX", "Chicago, IL",
    "Boston, MA", "Denver, CO", "Los Angeles, CA", "Remote (US)", "Remote (Global)", "Toronto, Canada", "London, UK"
]

UNIVERSITIES = [
    "Stanford University", "UC Berkeley", "Carnegie Mellon University", "MIT", "Georgia Tech",
    "University of Washington", "UT Austin", "University of Waterloo", "Cornell University", "UCLA",
    "University of Michigan", "NYU Courant", "Imperial College London", "National Univ of Singapore"
]

ROLES_CATALOG = [
    {
        "title": "Senior Backend Engineer (Python / Distributed Systems)",
        "department": "Engineering",
        "location": "San Francisco, CA / Remote",
        "job_type": "Full-time",
        "experience_level": "Senior (5+ yrs)",
        "description": "We are seeking an experienced Backend Engineer to scale our distributed event-driven platform handling 50M+ daily events. You will design resilient microservices, optimize database performance, and drive high-availability architecture.",
        "salary_range": "$165,000 - $210,000",
        "min_years_experience": 5.0,
        "required_skills": ["Python", "PostgreSQL", "Docker", "AWS", "FastAPI", "Distributed Systems"],
        "nice_to_have_skills": ["Kafka", "Redis", "Kubernetes", "gRPC"],
        "candidate_skills_pool": [
            "Python", "PostgreSQL", "Docker", "AWS", "FastAPI", "Distributed Systems",
            "Kafka", "Redis", "Kubernetes", "gRPC", "Flask", "RabbitMQ", "Linux", "CI/CD", "Go", "Terraform"
        ],
        "titles_pool": [
            "Senior Backend Engineer", "Staff Software Engineer", "Backend Developer", "Software Engineer II",
            "Distributed Systems Engineer", "Lead Cloud Engineer", "Infrastructure Engineer"
        ]
    },
    {
        "title": "Senior Full-Stack Engineer (React / TypeScript / Python)",
        "department": "Product Engineering",
        "location": "New York, NY / Remote",
        "job_type": "Full-time",
        "experience_level": "Mid-Senior (4+ yrs)",
        "description": "Looking for a versatile Full-Stack Engineer to lead feature development across our core recruiter workspace. You will craft high-performance client experiences, build robust backend APIs, and collaborate closely with product design.",
        "salary_range": "$150,000 - $190,000",
        "min_years_experience": 4.0,
        "required_skills": ["TypeScript", "React", "Python", "REST APIs", "SQL", "Tailwind CSS"],
        "nice_to_have_skills": ["Next.js", "GraphQL", "WebSockets", "State Management"],
        "candidate_skills_pool": [
            "TypeScript", "React", "Python", "REST APIs", "SQL", "Tailwind CSS",
            "Next.js", "GraphQL", "WebSockets", "Node.js", "PostgreSQL", "Docker", "Jest", "Redux", "Vite"
        ],
        "titles_pool": [
            "Senior Full-Stack Engineer", "Full Stack Developer", "Frontend Lead", "Software Engineer",
            "UI/UX Platform Engineer", "Web Applications Engineer"
        ]
    },
    {
        "title": "Lead Product Designer (Design Systems & B2B SaaS)",
        "department": "Product Design",
        "location": "Remote",
        "job_type": "Full-time",
        "experience_level": "Lead (6+ yrs)",
        "description": "We are looking for an exceptional Lead Product Designer to champion our design system and elevate complex B2B workflow experiences. You will lead user research, design high-density data interfaces, and partner with engineering.",
        "salary_range": "$160,000 - $195,000",
        "min_years_experience": 6.0,
        "required_skills": ["Figma", "Design Systems", "User Research", "Interaction Design", "Prototyping", "B2B SaaS"],
        "nice_to_have_skills": ["Design Tokens", "HTML/CSS", "Usability Testing", "Data Visualization"],
        "candidate_skills_pool": [
            "Figma", "Design Systems", "User Research", "Interaction Design", "Prototyping", "B2B SaaS",
            "Design Tokens", "HTML/CSS", "Usability Testing", "Data Visualization", "Wireframing", "Information Architecture"
        ],
        "titles_pool": [
            "Lead Product Designer", "Senior UX Designer", "Principal Product Designer", "Design Systems Lead",
            "Senior UI/UX Specialist", "Staff Product Designer"
        ]
    },
    {
        "title": "Staff Data Scientist / ML Engineer",
        "department": "Data & AI",
        "location": "Seattle, WA / Remote",
        "job_type": "Full-time",
        "experience_level": "Staff (6+ yrs)",
        "description": "Join our AI foundations group to build next-generation ranking, matching, and semantic search algorithms. Experience with LLM fine-tuning, embeddings, vector databases, and production inference pipelines required.",
        "salary_range": "$180,000 - $230,000",
        "min_years_experience": 6.0,
        "required_skills": ["Python", "PyTorch", "NLP", "Vector Databases", "Machine Learning", "MLOps"],
        "nice_to_have_skills": ["Hugging Face", "LLMs", "RAG", "Ray", "Triton"],
        "candidate_skills_pool": [
            "Python", "PyTorch", "NLP", "Vector Databases", "Machine Learning", "MLOps",
            "Hugging Face", "LLMs", "RAG", "Ray", "Triton", "Scikit-Learn", "FastAPI", "Docker", "Pandas"
        ],
        "titles_pool": [
            "Staff ML Engineer", "Senior Data Scientist", "AI Research Engineer", "NLP Specialist",
            "Applied Machine Learning Scientist", "Lead Data Engineer"
        ]
    }
]

def generate_realistic_resume(name, title, company, years_exp, skills, university):
    return f"""# {name}
**{title}** | {company}
Email: {name.lower().replace(' ', '.')}@example.com | Location: San Francisco, CA

---

### Executive Summary
Results-driven software professional with {years_exp:g} years of engineering experience architecting scalable systems and delivering high-impact products. Passionate about engineering excellence, clean code, and developer productivity.

### Professional Experience

**{company}** — *{title}*
(2021 – Present)
- Designed and maintained core platform services serving millions of active users with 99.99% uptime.
- Optimized database query patterns and indexing strategies, reducing median response latency by 42%.
- Mentored junior engineers and spearheaded cross-team architectural reviews and automated testing standards.
- Collaborated with product and security stakeholders to deploy zero-trust infrastructure and CI/CD automation.

**Prior Tech Solutions Inc.** — *Software Engineer*
(2018 – 2021)
- Spearheaded the migration from a monolithic application into event-driven containerized microservices.
- Implemented automated monitoring, distributed tracing, and real-time alerting using modern telemetry.
- Built reusable internal UI components and standardized API contracts adopted by 6 engineering teams.

### Education
**{university}**
B.S. in Computer Science & Mathematics (GPA: 3.8/4.0)

### Key Technical Competencies
{", ".join(skills)}
"""

def seed_database(target_count_per_job=30, force_clean=False):
    """
    Seeds database with realistic jobs and 120-150 candidates.
    Distributes candidates across stages:
    - new (unreviewed): 50%
    - screening: 20%
    - phone_screen: 12%
    - interview: 8%
    - offer: 4%
    - rejected: 6%
    """
    if force_clean:
        db.drop_all()
        db.create_all()
    else:
        db.create_all()
        if Job.query.count() > 0:
            return Job.query.count(), Candidate.query.count()

    created_jobs = []
    for role_info in ROLES_CATALOG:
        job = Job(
            title=role_info["title"],
            department=role_info["department"],
            location=role_info["location"],
            job_type=role_info["job_type"],
            experience_level=role_info["experience_level"],
            description=role_info["description"],
            salary_range=role_info["salary_range"],
            min_years_experience=role_info["min_years_experience"],
            status="active",
            created_at=utcnow() - timedelta(days=random.randint(5, 30))
        )
        job.required_skills = role_info["required_skills"]
        job.nice_to_have_skills = role_info["nice_to_have_skills"]
        db.session.add(job)
        db.session.flush()
        created_jobs.append((job, role_info))

    total_candidates_created = 0
    stages_distribution = (
        ["new"] * 45 +
        ["screening"] * 25 +
        ["phone_screen"] * 15 +
        ["interview"] * 8 +
        ["offer"] * 4 +
        ["rejected"] * 8
    )

    for job, role_info in created_jobs:
        # Generate candidates for each job
        for i in range(target_count_per_job):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@example.com"
            company = random.choice(COMPANIES)
            current_title = random.choice(role_info["titles_pool"])
            location = random.choice(LOCATIONS)
            university = random.choice(UNIVERSITIES)

            # Realistic experience distribution around job requirement
            exp_variance = random.gauss(job.min_years_experience + 0.5, 2.2)
            years_exp = round(max(1.0, min(16.0, exp_variance)), 1)

            # Sample skills with bias toward matching
            pool = role_info["candidate_skills_pool"]
            sample_size = min(len(pool), random.randint(4, 9))
            # Include some required skills intentionally
            if random.random() < 0.75:
                base_skills = random.sample(role_info["required_skills"], min(len(role_info["required_skills"]), random.randint(3, len(role_info["required_skills"]))))
            else:
                base_skills = random.sample(role_info["required_skills"], min(len(role_info["required_skills"]), random.randint(1, 3)))
            
            needed_more = max(0, sample_size - len(base_skills))
            remaining_skills = [s for s in pool if s not in base_skills]
            sampled_additional = random.sample(remaining_skills, min(len(remaining_skills), needed_more)) if needed_more > 0 and remaining_skills else []
            candidate_skills = base_skills + sampled_additional
            random.shuffle(candidate_skills)

            resume = generate_realistic_resume(name, current_title, company, years_exp, candidate_skills, university)

            # Compute match and insights
            candidate_payload = {
                "skills": candidate_skills,
                "years_of_experience": years_exp,
                "raw_resume": resume,
                "current_title": current_title
            }
            match_data = compute_candidate_match(candidate_payload, job)

            stage = random.choice(stages_distribution)
            applied_days_ago = random.randint(1, 28)
            applied_at = utcnow() - timedelta(days=applied_days_ago, hours=random.randint(1, 23))

            candidate = Candidate(
                job_id=job.id,
                name=name,
                email=email,
                phone=f"+1 (555) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
                location=location,
                current_title=current_title,
                current_company=company,
                years_of_experience=years_exp,
                education=f"B.S. in CS, {university}",
                raw_resume=resume,
                portfolio_url=f"https://github.com/{first.lower()}{last.lower()}",
                linkedin_url=f"https://linkedin.com/in/{first.lower()}-{last.lower()}",
                github_url=f"https://github.com/{first.lower()}{last.lower()}",
                stage=stage,
                match_score=match_data["match_score"],
                ai_headline=match_data["ai_headline"],
                starred=(match_data["match_score"] >= 88 and random.random() < 0.6),
                rating=random.randint(3, 5) if stage in ["phone_screen", "interview", "offer"] else None,
                applied_at=applied_at,
                updated_at=applied_at + timedelta(days=random.randint(0, 3))
            )
            candidate.skills = candidate_skills
            candidate.ai_pros = match_data["ai_pros"]
            candidate.ai_cons = match_data["ai_cons"]
            candidate.ai_questions = match_data["ai_questions"]

            db.session.add(candidate)
            db.session.flush()

            # Add activity log
            init_log = ActivityLog(
                candidate_id=candidate.id,
                actor="System",
                action="Application Received",
                details=f"Applied via TalentFlow Portal for {job.title}",
                timestamp=applied_at
            )
            db.session.add(init_log)

            if stage != "new":
                stage_log = ActivityLog(
                    candidate_id=candidate.id,
                    actor="Sarah Jenkins (Senior Recruiter)",
                    action=f"Moved to {stage.replace('_', ' ').title()}",
                    details=f"Candidate met role criteria with {candidate.match_score}% match score",
                    timestamp=applied_at + timedelta(days=1)
                )
                db.session.add(stage_log)

            if stage in ["phone_screen", "interview", "offer"]:
                note = CandidateNote(
                    candidate_id=candidate.id,
                    author="Sarah Jenkins (Recruiter)",
                    category="Screening Call",
                    rating=candidate.rating or 4,
                    text=f"Conducted 20-min initial screen. Candidate articulated their experience at {company} clearly. Strong communication skills and enthusiastic about the team mission.",
                    created_at=applied_at + timedelta(days=2)
                )
                db.session.add(note)

            total_candidates_created += 1

    db.session.commit()
    return len(created_jobs), total_candidates_created
