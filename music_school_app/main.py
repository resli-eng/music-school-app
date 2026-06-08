from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
import shutil
from typing import Optional

from database import (
    create_tables, get_db, User, StudentProfile, ParentProfile,
    PracticeLog, Assignment, StudentUpload, Message, SessionLocal
)

# Setup
app = FastAPI(title="Music School App")
templates = Jinja2Templates(directory="templates")

# Create uploads folder
os.makedirs("uploads", exist_ok=True)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    # Bcrypt has a 72-byte limit - truncate if necessary
    password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# Create tables on startup
create_tables()

# Seed demo data if database is empty
def seed_demo_data():
    db = SessionLocal()
    if db.query(User).count() > 0:
        db.close()
        return

    # Create demo users
    users_data = [
        {"email": "manager@school.com", "password": "admin123", "role": "manager", "full_name": "Alex Rivera (Manager)"},
        {"email": "coordinator@school.com", "password": "coord123", "role": "coordinator", "full_name": "Jordan Lee (Coordinator)"},
        {"email": "teacher@school.com", "password": "teach123", "role": "teacher", "full_name": "Ms. Emily Chen"},
        {"email": "student@school.com", "password": "student123", "role": "student", "full_name": "Liam Thompson"},
        {"email": "parent@school.com", "password": "parent123", "role": "parent", "full_name": "Sarah Thompson (Parent)"},
    ]

    for u in users_data:
        user = User(
            email=u["email"],
            password_hash=hash_password(u["password"]),
            role=u["role"],
            full_name=u["full_name"]
        )
        db.add(user)
    db.commit()

    # Get created users
    manager = db.query(User).filter(User.email == "manager@school.com").first()
    teacher = db.query(User).filter(User.email == "teacher@school.com").first()
    student_user = db.query(User).filter(User.email == "student@school.com").first()
    parent_user = db.query(User).filter(User.email == "parent@school.com").first()

    # Create student profile
    student_profile = StudentProfile(
        user_id=student_user.id,
        lesson_day="Monday 4:30 PM",
        teacher_id=teacher.id
    )
    db.add(student_profile)
    db.commit()

    # Create parent profile
    parent_profile = ParentProfile(user_id=parent_user.id)
    db.add(parent_profile)
    db.commit()

    # Add some sample practice logs
    logs = [
        PracticeLog(student_id=student_profile.id, date="2026-06-01", minutes=45, notes="Scales and song review"),
        PracticeLog(student_id=student_profile.id, date="2026-06-03", minutes=30, notes="New piece - first section"),
        PracticeLog(student_id=student_profile.id, date="2026-06-05", minutes=60, notes="Good session today!"),
    ]
    for log in logs:
        db.add(log)
    db.commit()

    # Sample assignment
    assignment = Assignment(
        teacher_id=teacher.id,
        student_id=student_profile.id,
        week_start="2026-06-08",
        title="Week of June 8 - Technique Focus",
        description="Practice the C major scale hands together. Work on the new song 'River Flows in You' - focus on measures 1-16. Record yourself once this week.",
        youtube_links="https://www.youtube.com/watch?v=example1,https://www.youtube.com/watch?v=example2"
    )
    db.add(assignment)
    db.commit()

    db.close()
    print("Demo data seeded successfully!")

seed_demo_data()

# Dependency to get current user (simplified session-based for MVP)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

# Routes
@app.get("/",
