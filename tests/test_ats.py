import unittest
import json
from app import create_app
from models import db, Job, Candidate, CandidateNote, ActivityLog

class TalentFlowATSTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create a test job
            self.job = Job(
                title="Staff Backend Engineer",
                department="Engineering",
                location="Remote",
                description="Lead distributed systems architecture and microservices scaling.",
                required_skills_json=json.dumps(["Python", "PostgreSQL", "Docker", "AWS"]),
                nice_to_have_skills_json=json.dumps(["Kafka", "Redis"]),
                min_years_experience=5.0
            )
            db.session.add(self.job)
            db.session.commit()
            self.job_id = self.job.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_check(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_create_and_get_job(self):
        res = self.client.get('/api/jobs')
        self.assertEqual(res.status_code, 200)
        jobs = res.get_json()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Staff Backend Engineer")

    def test_create_candidate_with_auto_scoring(self):
        payload = {
            "job_id": self.job_id,
            "name": "Jane Doe",
            "email": "jane@example.com",
            "current_title": "Senior Backend Dev",
            "current_company": "Acme Corp",
            "years_of_experience": 6.0,
            "skills": ["Python", "PostgreSQL", "AWS", "Docker", "Redis"],
            "raw_resume": "Senior software engineer with 6 years leading distributed systems on AWS and PostgreSQL."
        }
        res = self.client.post('/api/candidates', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertGreaterEqual(data["match_score"], 80)
        self.assertTrue(len(data["ai_pros"]) > 0)
        self.assertTrue(len(data["ai_questions"]) > 0)

    def test_candidate_stage_update_and_audit_trail(self):
        # Create candidate
        with self.app.app_context():
            cand = Candidate(
                job_id=self.job_id,
                name="Bob Smith",
                email="bob@example.com",
                stage="new",
                match_score=75
            )
            db.session.add(cand)
            db.session.commit()
            cand_id = cand.id

        # Move to screening
        res = self.client.patch(f'/api/candidates/{cand_id}/stage', json={
            "stage": "screening",
            "actor": "Recruiter Alice",
            "note": "Resume looks solid for backend role."
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["candidate"]["stage"], "screening")

        # Check candidate details and activity log
        res2 = self.client.get(f'/api/candidates/{cand_id}')
        data2 = res2.get_json()
        self.assertEqual(len(data2["activity_logs"]), 1)
        self.assertEqual(len(data2["notes"]), 1)
        self.assertIn("Screening", data2["activity_logs"][0]["action"])

    def test_bulk_stage_update(self):
        with self.app.app_context():
            c1 = Candidate(job_id=self.job_id, name="User One", email="u1@test.com", stage="new")
            c2 = Candidate(job_id=self.job_id, name="User Two", email="u2@test.com", stage="new")
            db.session.add_all([c1, c2])
            db.session.commit()
            ids = [c1.id, c2.id]

        res = self.client.post('/api/candidates/bulk-stage', json={
            "candidate_ids": ids,
            "stage": "phone_screen",
            "actor": "Senior Recruiter"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["updated_count"], 2)

        # Verify stages changed
        with self.app.app_context():
            updated = Candidate.query.filter(Candidate.id.in_(ids)).all()
            for c in updated:
                self.assertEqual(c.stage, "phone_screen")

    def test_bulk_reject(self):
        with self.app.app_context():
            c1 = Candidate(job_id=self.job_id, name="Candidate X", email="x@test.com", stage="new")
            db.session.add(c1)
            db.session.commit()
            cand_id = c1.id

        res = self.client.post('/api/candidates/bulk-reject', json={
            "candidate_ids": [cand_id],
            "reason": "Missing required distributed systems background"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["rejected_count"], 1)

        with self.app.app_context():
            cand = Candidate.query.get(cand_id)
            self.assertEqual(cand.stage, "rejected")

    def test_analytics_and_export(self):
        with self.app.app_context():
            c1 = Candidate(job_id=self.job_id, name="Candidate Alpha", email="a@test.com", stage="offer", match_score=92)
            c1.skills = ["Python", "AWS"]
            db.session.add(c1)
            db.session.commit()

        # Analytics
        res_analytics = self.client.get('/api/analytics')
        self.assertEqual(res_analytics.status_code, 200)
        analytics_data = res_analytics.get_json()
        self.assertEqual(analytics_data["total_candidates"], 1)
        self.assertEqual(analytics_data["avg_match_score"], 92.0)

        # Export CSV
        res_export = self.client.get('/api/export')
        self.assertEqual(res_export.status_code, 200)
        self.assertIn("text/csv", res_export.content_type)
        self.assertIn("Candidate Alpha", res_export.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
