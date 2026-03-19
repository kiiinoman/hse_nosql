"""
load_test.py — Locust load test for MongoDB sharded cluster
Install: pip install locust pymongo
Run:     locust -f load_test.py --headless -u 50 -r 10 --run-time 60s

Or with web UI: locust -f load_test.py
Then open: http://localhost:8089
"""

import random
import time
import uuid
from locust import User, task, between, events
from pymongo import MongoClient


# ── MongoDB client (shared per worker) ───────────────────────────────────────

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    return _client["university"]


# ── Custom Locust User for MongoDB ────────────────────────────────────────────

class MongoUser(User):
    """
    Each simulated user performs MongoDB operations directly.
    We manually record response times so Locust can display stats.
    """
    wait_time = between(0.05, 0.3)
    db = None

    def on_start(self):
        self.db = get_db()
        # Cache a list of student IDs for read operations
        self._student_ids = []
        self._refresh_ids()

    def _refresh_ids(self):
        ids = [s["student_id"] for s in self.db.students.find({}, {"student_id": 1}).limit(500)]
        if ids:
            self._student_ids = ids

    def _run(self, name, fn):
        start = time.perf_counter()
        try:
            result = fn()
            elapsed = int((time.perf_counter() - start) * 1000)
            events.request.fire(
                request_type="MongoDB",
                name=name,
                response_time=elapsed,
                response_length=0,
                exception=None,
            )
            return result
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            events.request.fire(
                request_type="MongoDB",
                name=name,
                response_time=elapsed,
                response_length=0,
                exception=e,
            )

    # ── Read operations (60% of traffic) ─────────────────────────────────────

    @task(4)
    def find_student_by_id(self):
        if not self._student_ids:
            return
        sid = random.choice(self._student_ids)
        self._run("find_student_by_id",
                  lambda: self.db.students.find_one({"student_id": sid}))

    @task(3)
    def list_students_by_faculty(self):
        faculty = random.choice(["ИТ", "Физика", "Математика", "Экономика", "Юриспруденция"])
        self._run("list_students_by_faculty",
                  lambda: list(self.db.students.find({"faculty": faculty}).limit(20)))

    @task(2)
    def get_student_grades(self):
        if not self._student_ids:
            return
        sid = random.choice(self._student_ids)
        self._run("get_student_grades",
                  lambda: list(self.db.enrollments.find({"student_id": sid})))

    @task(1)
    def count_students(self):
        self._run("count_students",
                  lambda: self.db.students.count_documents({}))

    # ── Write operations (30% of traffic) ────────────────────────────────────

    @task(2)
    def insert_student(self):
        sid = str(uuid.uuid4())[:8]
        doc = {
            "student_id": sid,
            "name":       f"Load Test {sid}",
            "email":      f"{sid}@loadtest.ru",
            "group":      "ИТ-11",
            "faculty":    "ИТ",
            "year":       1,
        }
        self._run("insert_student",
                  lambda: self.db.students.insert_one(doc))
        self._student_ids.append(sid)

    @task(1)
    def update_student_year(self):
        if not self._student_ids:
            return
        sid = random.choice(self._student_ids)
        year = random.randint(1, 5)
        self._run("update_student_year",
                  lambda: self.db.students.update_one(
                      {"student_id": sid},
                      {"$set": {"year": year}}
                  ))

    # ── Aggregation (10% of traffic) ──────────────────────────────────────────

    @task(1)
    def avg_grade_by_faculty(self):
        self._run("avg_grade_by_faculty", lambda: list(
            self.db.enrollments.aggregate([
                {"$match": {"grade": {"$ne": None}}},
                {"$group": {"_id": "$course_name", "avg": {"$avg": "$grade"}}},
                {"$limit": 5}
            ])
        ))
