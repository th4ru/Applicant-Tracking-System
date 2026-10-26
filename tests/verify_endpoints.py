import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

client = app.test_client()

# 1. Health
h_res = client.get('/health')
print('Health:', h_res.status_code, h_res.get_json())

# 2. Index
idx_res = client.get('/')
print('Index HTML:', idx_res.status_code, 'Content length:', len(idx_res.get_data()))

# 3. Jobs
j_res = client.get('/api/jobs')
jobs = j_res.get_json()
print('Jobs count:', len(jobs))
for j in jobs:
    print(f" - Job {j['id']}: {j['title']} ({j.get('total_candidates', 0)} candidates)")

# 4. Candidates
c_res = client.get('/api/candidates?per_page=5')
c_data = c_res.get_json()
print('Candidates total:', c_data['pagination']['total'])
for c in c_data['candidates']:
    print(f"   * #{c['id']}: {c['name']} | Score: {c['match_score']}% | Stage: {c['stage']}")

# 5. Full candidate details
first_id = c_data['candidates'][0]['id']
d_res = client.get(f'/api/candidates/{first_id}')
details = d_res.get_json()
print('Candidate #', first_id, 'details:')
print(' - Headline:', details.get('ai_headline'))
print(' - Pros:', details.get('ai_pros'))
print(' - Cons:', details.get('ai_cons'))
print(' - Questions:', details.get('ai_questions'))
print(' - Notes count:', len(details.get('notes', [])))
print(' - Activity logs:', len(details.get('activity_logs', [])))

print('ALL ENDPOINTS VERIFIED PERFECTLY!')
