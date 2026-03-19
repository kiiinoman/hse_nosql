#!/usr/bin/env python3
"""
University Database CLI
Connects to MongoDB sharded cluster via mongos (localhost:27017)
"""

import sys
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import uuid

# ── Connection ────────────────────────────────────────────────────────────────

def get_db():
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        return client["university"]
    except ConnectionFailure:
        print(" Cannot connect to MongoDB. Is docker compose running?")
        sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────

def new_id():
    return str(uuid.uuid4())[:8]

def separator():
    print("─" * 50)

def print_student(s):
    print(f"  ID      : {s['student_id']}")
    print(f"  Name    : {s['name']}")
    print(f"  Email   : {s['email']}")
    print(f"  Group   : {s.get('group', '—')}")
    print(f"  Faculty : {s.get('faculty', '—')}")
    print(f"  Year    : {s.get('year', '—')}")

def print_course(c):
    print(f"  ID      : {c['course_id']}")
    print(f"  Name    : {c['name']}")
    print(f"  Faculty : {c.get('faculty_id', '—')}")
    print(f"  Credits : {c.get('credits', '—')}")
    print(f"  Teacher : {c.get('teacher', '—')}")

# ── Student operations ────────────────────────────────────────────────────────

def add_student(db):
    print("\n Add new student")
    separator()
    name    = input("Full name    : ").strip()
    email   = input("Email        : ").strip()
    group   = input("Group        : ").strip()
    faculty = input("Faculty      : ").strip()
    year    = input("Study year   : ").strip()

    if not name or not email:
        print("Name and email are required.")
        return

    student = {
        "student_id": new_id(),
        "name":       name,
        "email":      email,
        "group":      group,
        "faculty":    faculty,
        "year":       int(year) if year.isdigit() else 1,
        "created_at": datetime.utcnow()
    }
    try:
        db.students.insert_one(student)
        print(f"\n Student added! ID: {student['student_id']}")
    except DuplicateKeyError:
        print(" Email already exists.")

def get_student(db):
    print("\n Find student")
    separator()
    query = input("Enter student ID or email: ").strip()
    s = db.students.find_one({"$or": [{"student_id": query}, {"email": query}]})
    if s:
        print()
        print_student(s)
    else:
        print(" Student not found.")

def list_students(db):
    print("\n List students")
    separator()
    faculty = input("Filter by faculty (leave blank for all): ").strip()
    group   = input("Filter by group   (leave blank for all): ").strip()
    limit_s = input("Limit (default 20): ").strip()
    limit   = int(limit_s) if limit_s.isdigit() else 20

    query = {}
    if faculty:
        query["faculty"] = faculty
    if group:
        query["group"] = group

    students = list(db.students.find(query).limit(limit))
    print(f"\n  Found: {len(students)} student(s)\n")
    for s in students:
        print(f"  [{s['student_id']}] {s['name']} — {s.get('group','?')} / {s.get('faculty','?')}")

def delete_student(db):
    print("\n🗑️  Delete student")
    separator()
    sid = input("Student ID: ").strip()
    result = db.students.delete_one({"student_id": sid})
    if result.deleted_count:
        db.enrollments.delete_many({"student_id": sid})
        print(" Student and their enrollments deleted.")
    else:
        print(" Student not found.")

# ── Course operations ─────────────────────────────────────────────────────────

def add_course(db):
    print("\n Add new course")
    separator()
    name      = input("Course name : ").strip()
    faculty   = input("Faculty     : ").strip()
    teacher   = input("Teacher     : ").strip()
    credits_s = input("Credits     : ").strip()

    course = {
        "course_id": new_id(),
        "name":      name,
        "faculty_id": faculty,
        "teacher":   teacher,
        "credits":   int(credits_s) if credits_s.isdigit() else 3,
        "created_at": datetime.utcnow()
    }
    db.courses.insert_one(course)
    print(f"\n Course added! ID: {course['course_id']}")

def list_courses(db):
    print("\n List courses")
    separator()
    faculty = input("Filter by faculty (leave blank for all): ").strip()
    query = {"faculty_id": faculty} if faculty else {}
    courses = list(db.courses.find(query).limit(30))
    print(f"\n  Found: {len(courses)} course(s)\n")
    for c in courses:
        print(f"  [{c['course_id']}] {c['name']} — {c.get('faculty_id','?')} ({c.get('credits','?')} cr.)")

# ── Enrollment operations ─────────────────────────────────────────────────────

def enroll_student(db):
    print("\n  Enroll student in course")
    separator()
    sid      = input("Student ID : ").strip()
    cid      = input("Course ID  : ").strip()
    semester = input("Semester   : ").strip()

    student = db.students.find_one({"student_id": sid})
    course  = db.courses.find_one({"course_id": cid})

    if not student:
        print("Student not found.")
        return
    if not course:
        print("Course not found.")
        return

    enrollment = {
        "enrollment_id": new_id(),
        "student_id":    sid,
        "course_id":     cid,
        "student_name":  student["name"],
        "course_name":   course["name"],
        "semester":      semester,
        "grade":         None,
        "enrolled_at":   datetime.utcnow()
    }
    db.enrollments.insert_one(enrollment)
    print(f"{student['name']} enrolled in {course['name']}!")

def set_grade(db):
    print("\n🎓 Set grade")
    separator()
    sid   = input("Student ID : ").strip()
    cid   = input("Course ID  : ").strip()
    grade = input("Grade (1–10): ").strip()

    result = db.enrollments.update_one(
        {"student_id": sid, "course_id": cid},
        {"$set": {"grade": int(grade) if grade.isdigit() else grade,
                  "graded_at": datetime.utcnow()}}
    )
    if result.modified_count:
        print("Grade saved.")
    else:
        print("Enrollment not found.")

def get_grades(db):
    print("\n Student grades")
    separator()
    sid = input("Student ID: ").strip()
    student = db.students.find_one({"student_id": sid})
    if not student:
        print("Student not found.")
        return
    enrollments = list(db.enrollments.find({"student_id": sid}))
    print(f"\n  Student: {student['name']}")
    print(f"  Enrollments: {len(enrollments)}\n")
    for e in enrollments:
        grade = e.get("grade", "—")
        print(f"  {e.get('course_name','?'):30s}  Sem: {e.get('semester','?'):6s}  Grade: {grade}")

# ── Stats ─────────────────────────────────────────────────────────────────────

def show_stats(db):
    print("\nDatabase statistics")
    separator()
    n_students   = db.students.count_documents({})
    n_courses    = db.courses.count_documents({})
    n_enrollments = db.enrollments.count_documents({})

    print(f"  Students    : {n_students}")
    print(f"  Courses     : {n_courses}")
    print(f"  Enrollments : {n_enrollments}")

    # Shard distribution info
    print("\n  Shard distribution:")
    try:
        stats = db.command("collStats", "students")
        shards = stats.get("shards", {})
        for shard_name, shard_info in shards.items():
            count = shard_info.get("count", "?")
            print(f"    {shard_name}: {count} documents")
    except Exception:
        print("    (run as admin to see shard distribution)")

# ── Main menu ─────────────────────────────────────────────────────────────────

MENU = """
╔══════════════════════════════════╗
║      University DB — CLI         ║
╠══════════════════════════════════╣
║  Students                        ║
║   1. Add student                 ║
║   2. Find student                ║
║   3. List students               ║
║   4. Delete student              ║
╠══════════════════════════════════╣
║  Courses                         ║
║   5. Add course                  ║
║   6. List courses                ║
╠══════════════════════════════════╣
║  Enrollments                     ║
║   7. Enroll student              ║
║   8. Set grade                   ║
║   9. View student grades         ║
╠══════════════════════════════════╣
║   s. Statistics                  ║
║   q. Quit                        ║
╚══════════════════════════════════╝
"""

ACTIONS = {
    "1": add_student,
    "2": get_student,
    "3": list_students,
    "4": delete_student,
    "5": add_course,
    "6": list_courses,
    "7": enroll_student,
    "8": set_grade,
    "9": get_grades,
    "s": show_stats,
}

def main():
    db = get_db()
    print("Connected to MongoDB sharded cluster (mongos:27017)")
    while True:
        print(MENU)
        choice = input("Choose: ").strip().lower()
        if choice == "q":
            print("Bye!")
            break
        action = ACTIONS.get(choice)
        if action:
            action(db)
        else:
            print("Unknown option.")
        print()

if __name__ == "__main__":
    main()
