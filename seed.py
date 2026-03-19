#!/usr/bin/env python3
"""
seed.py — Populate MongoDB sharded cluster with realistic test data
Usage: python seed.py [--students 10000] [--courses 100]
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient, InsertOne
from pymongo.errors import BulkWriteError

# ── Fake data pools ───────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Александр","Мария","Дмитрий","Анна","Иван","Екатерина",
    "Никита","Ольга","Артём","Наталья","Сергей","Татьяна",
    "Андрей","Юлия","Михаил","Елена","Павел","Ксения","Алексей","Светлана"
]
LAST_NAMES = [
    "Иванов","Смирнова","Кузнецов","Попова","Васильев","Новикова",
    "Петров","Морозова","Соколов","Волкова","Михайлов","Алексеева",
    "Федоров","Лебедева","Орлов","Козлова","Макаров","Новиков","Николаев","Захарова"
]
FACULTIES = ["ИТ", "Физика", "Математика", "Экономика", "Юриспруденция"]
TEACHERS  = ["Петров А.А.", "Сидорова М.В.", "Козлов Р.И.", "Белова С.Н.", "Жуков Д.К."]
COURSES_BY_FACULTY = {
    "ИТ":           ["Базы данных", "ОС", "Сети", "ML", "Алгоритмы", "Веб-разработка"],
    "Физика":       ["Механика", "Оптика", "Электродинамика", "Термодинамика"],
    "Математика":   ["Анализ", "Алгебра", "Теорвер", "Дискретная математика"],
    "Экономика":    ["Микроэкономика", "Макроэкономика", "Финансы", "Статистика"],
    "Юриспруденция":["Гражданское право", "УК", "Конституционное право", "Международное право"],
}
SEMESTERS = ["2023-Осень", "2024-Весна", "2024-Осень", "2025-Весна"]


def new_id():
    return str(uuid.uuid4())[:8]

def random_date(start_year=2000, end_year=2005):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def seed(n_students=10_000, n_enrollments_per_student=3):
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    db = client["university"]

    # ── Clear existing data ───────────────────────────────────────────────────
    print("Clearing old data...")
    db.students.delete_many({})
    db.courses.delete_many({})
    db.enrollments.delete_many({})

    # ── Insert courses ────────────────────────────────────────────────────────
    print("Inserting courses...")
    courses = []
    for faculty, course_names in COURSES_BY_FACULTY.items():
        for name in course_names:
            courses.append({
                "course_id":  new_id(),
                "name":       name,
                "faculty_id": faculty,
                "teacher":    random.choice(TEACHERS),
                "credits":    random.choice([3, 4, 5]),
                "created_at": datetime.utcnow()
            })
    db.courses.insert_many(courses)
    print(f"  {len(courses)} courses inserted")

    # ── Insert students in batches ────────────────────────────────────────────
    print(f"👨‍🎓 Inserting {n_students} students...")
    BATCH = 500
    total = 0
    student_ids = []

    for batch_start in range(0, n_students, BATCH):
        batch = []
        for _ in range(min(BATCH, n_students - batch_start)):
            faculty = random.choice(FACULTIES)
            sid = new_id()
            student_ids.append((sid, faculty))
            batch.append({
                "student_id": sid,
                "name":  f"{random.choice(LAST_NAMES)} {random.choice(FIRST_NAMES)}",
                "email": f"{sid}@university.ru",
                "group": f"{faculty[:2]}-{random.randint(1,4)}{random.randint(1,3)}",
                "faculty":    faculty,
                "year":       random.randint(1, 5),
                "birth_date": random_date(),
                "created_at": datetime.utcnow()
            })
        db.students.insert_many(batch)
        total += len(batch)
        print(f"  ... {total}/{n_students}", end="\r")

    print(f"\n  {total} students inserted")

    # ── Insert enrollments ────────────────────────────────────────────────────
    print(f"  Inserting enrollments (~{n_students * n_enrollments_per_student})...")
    total_enroll = 0
    BATCH = 500
    batch = []

    for sid, faculty in student_ids:
        faculty_courses = [c for c in courses if c["faculty_id"] == faculty]
        chosen = random.sample(faculty_courses, min(n_enrollments_per_student, len(faculty_courses)))
        for course in chosen:
            grade = random.randint(3, 10) if random.random() > 0.1 else None
            batch.append({
                "enrollment_id": new_id(),
                "student_id":    sid,
                "course_id":     course["course_id"],
                "student_name":  "",  # denormalized (simplified)
                "course_name":   course["name"],
                "semester":      random.choice(SEMESTERS),
                "grade":         grade,
                "enrolled_at":   datetime.utcnow()
            })
            if len(batch) >= BATCH:
                db.enrollments.insert_many(batch)
                total_enroll += len(batch)
                batch = []
                print(f"  ... {total_enroll}", end="\r")

    if batch:
        db.enrollments.insert_many(batch)
        total_enroll += len(batch)

    print(f"\n {total_enroll} enrollments inserted")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n Final counts:")
    print(f"  Students    : {db.students.count_documents({})}")
    print(f"  Courses     : {db.courses.count_documents({})}")
    print(f"  Enrollments : {db.enrollments.count_documents({})}")
    print("\n Seeding complete! Run: python load_test.py")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed university DB")
    parser.add_argument("--students", type=int, default=10_000)
    parser.add_argument("--enrollments", type=int, default=3,
                        help="Enrollments per student")
    args = parser.parse_args()
    seed(args.students, args.enrollments)
