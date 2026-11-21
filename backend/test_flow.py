import os, json, tempfile
tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(tmp.name, 'legacy.db')
os.environ['ORGANIZATION_DATA_DIR'] = os.path.join(tmp.name, 'orgs')
os.environ['AUTH_DATABASE_PATH'] = os.path.join(tmp.name, 'accounts.db')
os.environ["GEMINI_API_KEY"] = ""
import app as A
c = A.app.test_client()
account={'organization':'Demo Test','organization_code':'demo-secret-code-123','email':'admin@example.com','name':'Admin','password':'password-at-least-12','designation':'admin','create_organization':True}
assert c.post('/api/auth/register',json=account).status_code == 201
assert c.post('/api/auth/login',json=account).status_code == 200
J = lambda r: r.get_json()

# 1. load demo twice -> no duplicates
print("load:", J(c.post("/api/demo/load")), J(c.post("/api/demo/load")))
print("meetings:", len(J(c.get("/api/meetings"))), "| tasks:", [(t["title"], t["owner"], t["deadline"], t["status"]) for t in J(c.get("/api/tasks"))])
# 2. conflict detected
cf = J(c.get("/api/conflicts"))
print("conflicts:", [(x["classification"], x["old"]["value"], x["new"]["value"], x["status"]) for x in cf])
print("decision statuses:", [(d["value"], d["status"]) for d in J(c.get("/api/decisions"))])
# 3. user not yet resolved -> old still active; resolve supersede
r = c.post(f"/api/conflicts/{cf[0]['id']}/resolve", json={"action": "supersede"})
print("resolve:", r.status_code, [(d["value"], d["status"]) for d in J(c.get("/api/decisions"))])
print("resolve again:", c.post(f"/api/conflicts/{cf[0]['id']}/resolve", json={"action": "keep"}).status_code)
# 4. unowned stays unowned
print("unowned:", [t["title"] for t in J(c.get("/api/tasks")) if t["owner"] == "Owner unclear"])
# 5. sync without approval blocked; approve; sync w/o github -> honest error
tid = [t for t in J(c.get("/api/tasks")) if t["title"].startswith("Prepare marketing")][0]["id"]
print("sync unapproved:", c.post(f"/api/tasks/{tid}/sync").status_code)
c.post(f"/api/tasks/{tid}/approve", json={"approved": True})
r = c.post(f"/api/tasks/{tid}/sync"); print("sync approved, no github:", r.status_code, J(r)["code"])
# 6. reminders / time
print("clock:", J(c.get("/api/reminders"))["clock"])
r = J(c.post("/api/demo/advance-time", json={"to_next_deadline": True})); print("jump:", r["message"], [n["title"] for n in r["notifications"]])
r = J(c.post("/api/demo/advance-time")); print("+2d:", r["message"], [(n["title"], n["state"]) for n in r["notifications"]])
# 7. digest + stats
d = J(c.get("/api/digest/Sarah")); print("digest:", d["source"], "|", d["summary"])
s = J(c.get("/api/dashboard/stats")); print("stats:", {k: s[k] for k in ("meetings","decisions","active_tasks","completed_tasks","open_conflicts","overdue_tasks")})
print("stages:", [(x["name"], x["status"]) for x in J(c.get("/api/meetings/2"))["stages"]])
# 8. non-demo meeting without key -> clear error
m = J(c.post("/api/meetings", json={"title":"x","date":"2026-11-21","transcript":"A: hi"}))
r = c.post(f"/api/meetings/{m['id']}/process"); print("no key:", r.status_code, J(r)["code"])
print("bad date:", c.post("/api/meetings", json={"title":"x","date":"bad","transcript":"y"}).status_code)

# 9. Mocked Gemini path (live-AI code path incl. comparison + validation)
os.environ["GEMINI_API_KEY"] = "fake"
def fake(prompt, schema=None):
    if schema is A.COMPARE_SCHEMA:
        return {"pairs": [{"new_id": "new_0", "old_id": 2, "classification": "updates", "explanation": "Launch moved."},
                          {"new_id": "new_9", "old_id": 1, "classification": "contradicts", "explanation": "bad id, must be dropped"}]}
    if schema is A.EXTRACT_SCHEMA:
        return {"summary":"s","key_points":[],"follow_ups":[],"speakers":["A"],
                "decisions":[{"topic":"Launch Date","value":"Dec 20","speaker":"A","quote":"hi"}],
                "tasks":[{"title":"Ship it","description":"d","owner":"unknown","deadline":"2026-12-18","priority":"high","quote":"hi"},
                         {"title":"Bad","description":"","owner":"X","deadline":"not-a-date","priority":"urgent","quote":"hi"}],"completed":[]}
A.gemini = fake
r = J(c.post(f"/api/meetings/{m['id']}/process"))
print("mock gemini:", r["source"], [(t["title"], t["owner"], t["deadline"], t["priority"]) for t in r["tasks"]], [(d["topic"], d["status"]) for d in r["decisions"]])
print("new conflicts:", [(x["classification"], x["status"]) for x in J(c.get("/api/conflicts"))])
