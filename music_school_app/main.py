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
from fastapi import Cookie
from typing import Optional

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url=f"/dashboard/{user.role}")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    
    response = RedirectResponse(url=f"/dashboard/{user.role}", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")
    return response

# Dashboard routing
@app.get("/dashboard/{role}", response_class=HTMLResponse)
async def dashboard(
    role: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role != role:
        return RedirectResponse(url="/login")
    
    if role == "student":
        return await student_dashboard(request, user, db)
    elif role == "teacher":
        return await teacher_dashboard(request, user, db)
    elif role == "parent":
        return await parent_dashboard(request, user, db)
    elif role in ["manager", "coordinator", "admin"]:
        return await manager_dashboard(request, user, db)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Unknown role"})

async def student_dashboard(request: Request, user: User, db: Session):
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    
    # Get practice logs
    logs = db.query(PracticeLog).filter(PracticeLog.student_id == student.id).order_by(PracticeLog.date.desc()).all()
    total_minutes = sum(log.minutes for log in logs)
    total_hours = round(total_minutes / 60, 1)
    
    # Get assignments
    assignments = db.query(Assignment).filter(Assignment.student_id == student.id).order_by(Assignment.week_start.desc()).all()
    
    # Get uploads
    uploads = db.query(StudentUpload).filter(StudentUpload.student_id == student.id).order_by(StudentUpload.uploaded_at.desc()).all()
    
    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "user": user,
        "student": student,
        "logs": logs,
        "total_hours": total_hours,
        "assignments": assignments,
        "uploads": uploads
    })

async def teacher_dashboard(request: Request, user: User, db: Session):
    # Get students assigned to this teacher
    students = db.query(StudentProfile).filter(StudentProfile.teacher_id == user.id).all()
    
    # Get recent assignments created by this teacher
    assignments = db.query(Assignment).filter(Assignment.teacher_id == user.id).order_by(Assignment.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("teacher_dashboard.html", {
        "request": request,
        "user": user,
        "students": students,
        "assignments": assignments
    })

async def parent_dashboard(request: Request, user: User, db: Session):
    # For demo, assume parent is linked to the demo student
    student = db.query(StudentProfile).first()  # In real app we'd have proper linking
    
    if not student:
        return templates.TemplateResponse("parent_dashboard.html", {
            "request": request, "user": user, "student": None, "error": "No student linked yet"
        })
    
    logs = db.query(PracticeLog).filter(PracticeLog.student_id == student.id).order_by(PracticeLog.date.desc()).all()
    total_minutes = sum(log.minutes for log in logs)
    total_hours = round(total_minutes / 60, 1)
    
    assignments = db.query(Assignment).filter(Assignment.student_id == student.id).order_by(Assignment.week_start.desc()).all()
    uploads = db.query(StudentUpload).filter(StudentUpload.student_id == student.id).order_by(StudentUpload.uploaded_at.desc()).all()
    
    # Messages between parent and teacher
    messages = db.query(Message).filter(
        (Message.sender_id == user.id) | (Message.recipient_id == user.id)
    ).order_by(Message.created_at.desc()).limit(20).all()
    
    return templates.TemplateResponse("parent_dashboard.html", {
        "request": request,
        "user": user,
        "student": student,
        "logs": logs,
        "total_hours": total_hours,
        "assignments": assignments,
        "uploads": uploads,
        "messages": messages
    })

async def manager_dashboard(request: Request, user: User, db: Session):
    total_users = db.query(User).count()
    total_students = db.query(StudentProfile).count()
    total_practice_logs = db.query(PracticeLog).count()
    
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("manager_dashboard.html", {
        "request": request,
        "user": user,
        "total_users": total_users,
        "total_students": total_students,
        "total_practice_logs": total_practice_logs,
        "recent_users": recent_users
    })

# Student: Log practice time
@app.post("/student/log-practice")
async def log_practice(
    request: Request,
    date: str = Form(...),
    minutes: int = Form(...),
    notes: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    log = PracticeLog(
        student_id=student.id,
        date=date,
        minutes=minutes,
        notes=notes
    )
    db.add(log)
    db.commit()
    
    return RedirectResponse(url="/dashboard/student", status_code=303)

# Teacher: Create assignment
@app.post("/teacher/create-assignment")
async def create_assignment(
    request: Request,
    student_id: int = Form(...),
    week_start: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    youtube_links: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    assignment = Assignment(
        teacher_id=user.id,
        student_id=student_id,
        week_start=week_start,
        title=title,
        description=description,
        youtube_links=youtube_links
    )
    db.add(assignment)
    db.commit()
    
    return RedirectResponse(url="/dashboard/teacher", status_code=303)

# Student/Parent: Upload progress file
@app.post("/upload-progress")
async def upload_progress(
    request: Request,
    assignment_id: Optional[int] = Form(None),
    description: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role not in ["student", "parent"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not student and user.role == "parent":
        # For demo parent, use first student
        student = db.query(StudentProfile).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = f"uploads/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    upload = StudentUpload(
        student_id=student.id,
        assignment_id=assignment_id,
        file_path=file_path,
        description=description
    )
    db.add(upload)
    db.commit()
    
    return RedirectResponse(url=f"/dashboard/{user.role}", status_code=303)

# Parent: Send message to teacher
@app.post("/parent/send-message")
async def send_message(
    request: Request,
    content: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role != "parent":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # For demo: send to the teacher of the first student
    student = db.query(StudentProfile).first()
    if student and student.teacher_id:
        teacher = db.query(User).filter(User.id == student.teacher_id).first()
        if teacher:
            msg = Message(
                sender_id=user.id,
                recipient_id=teacher.id,
                student_id=student.id,
                content=content
            )
            db.add(msg)
            db.commit()
    
    return RedirectResponse(url="/dashboard/parent", status_code=303)

# Simple API endpoint for future mobile use
@app.get("/api/student/{student_id}/practice-total")
async def get_practice_total(student_id: int, db: Session = Depends(get_db)):
    logs = db.query(PracticeLog).filter(PracticeLog.student_id == student_id).all()
    total = sum(log.minutes for log in logs)
    return {"student_id": student_id, "total_minutes": total, "total_hours": round(total / 60, 1)}


# ==================== REGISTRATION ====================
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    students = db.query(StudentProfile).all()
    return templates.TemplateResponse("register.html", {
        "request": request,
        "students": students
    })


@app.post("/register")
async def register_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    lesson_day: str = Form(""),
    link_student_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        students = db.query(StudentProfile).all()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "students": students,
            "error": "An account with this email already exists."
        })

    # Create user
    new_user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if role == "student":
        student_profile = StudentProfile(
            user_id=new_user.id,
            lesson_day=lesson_day if lesson_day else "To be scheduled"
        )
        db.add(student_profile)
        db.commit()

    elif role == "parent":
        parent_profile = ParentProfile(user_id=new_user.id)
        db.add(parent_profile)
        db.commit()

        # Optional linking
        if link_student_id:
            # In a more advanced version we would have a proper join table.
            # For now we just note it in the profile or handle via messages.
            pass

    # Auto-login after registration
    response = RedirectResponse(url=f"/dashboard/{role}", status_code=303)
    response.set_cookie(key="user_id", value=str(new_user.id), httponly=True)
    return response


# ==================== REPORTS (Manager & Coordinator) ====================
@app.get("/manager/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role not in ["manager", "coordinator", "admin"]:
        return RedirectResponse(url="/login")

    all_students = db.query(StudentProfile).all()
    teachers = db.query(User).filter(User.role == "teacher").all()

    # School-wide stats
    total_students = len(all_students)
    all_logs = db.query(PracticeLog).all()
    total_minutes = sum(log.minutes for log in all_logs)
    total_hours = round(total_minutes / 60, 1)
    avg_hours = round(total_hours / total_students, 1) if total_students > 0 else 0
    total_assignments = db.query(Assignment).count()

    # Top students by practice
    student_totals = {}
    for log in all_logs:
        sid = log.student_id
        if sid not in student_totals:
            student_totals[sid] = {"minutes": 0, "sessions": 0, "name": ""}
        student_totals[sid]["minutes"] += log.minutes
        student_totals[sid]["sessions"] += 1

    # Get names
    for sid in student_totals:
        sp = db.query(StudentProfile).filter(StudentProfile.id == sid).first()
        if sp:
            student_totals[sid]["name"] = sp.user.full_name

    top_students = sorted(
        [{"name": v["name"], "hours": round(v["minutes"]/60,1), "sessions": v["sessions"]} 
         for v in student_totals.values() if v["name"]],
        key=lambda x: x["hours"], reverse=True
    )[:5]

    school_wide = {
        "total_students": total_students,
        "total_hours": total_hours,
        "avg_hours": avg_hours,
        "total_assignments": total_assignments,
        "top_students": top_students
    }

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "all_students": all_students,
        "teachers": teachers,
        "school_wide": school_wide,
        "student_report": None,
        "teacher_report": None
    })


@app.get("/manager/student-report", response_class=HTMLResponse)
async def student_specific_report(
    request: Request,
    student_id: int,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role not in ["manager", "coordinator", "admin"]:
        return RedirectResponse(url="/login")

    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404)

    logs = db.query(PracticeLog).filter(PracticeLog.student_id == student_id).order_by(PracticeLog.date.desc()).all()
    total_minutes = sum(l.minutes for l in logs)
    assignments = db.query(Assignment).filter(Assignment.student_id == student_id).order_by(Assignment.week_start.desc()).all()

    student_report = {
        "student": student,
        "logs": logs,
        "total_hours": round(total_minutes / 60, 1),
        "assignments": assignments
    }

    all_students = db.query(StudentProfile).all()
    teachers = db.query(User).filter(User.role == "teacher").all()

    # School-wide for the sidebar stats
    school_wide = {"total_students": len(all_students), "total_hours": 0, "avg_hours": 0, "total_assignments": 0, "top_students": []}

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "all_students": all_students,
        "teachers": teachers,
        "school_wide": school_wide,
        "student_report": student_report,
        "teacher_report": None
    })


@app.get("/manager/teacher-report", response_class=HTMLResponse)
async def teacher_student_report(
    request: Request,
    teacher_id: int,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user or user.role not in ["manager", "coordinator", "admin"]:
        return RedirectResponse(url="/login")

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404)

    students = db.query(StudentProfile).filter(StudentProfile.teacher_id == teacher_id).all()

    students_data = []
    for sp in students:
        logs = db.query(PracticeLog).filter(PracticeLog.student_id == sp.id).all()
        total_min = sum(l.minutes for l in logs)
        assignments_count = db.query(Assignment).filter(Assignment.student_id == sp.id).count()
        last_log = db.query(PracticeLog).filter(PracticeLog.student_id == sp.id).order_by(PracticeLog.date.desc()).first()

        students_data.append({
            "name": sp.user.full_name,
            "lesson_day": sp.lesson_day,
            "total_hours": round(total_min / 60, 1),
            "assignment_count": assignments_count,
            "last_practice": last_log.date if last_log else None
        })

    teacher_report = {
        "teacher_name": teacher.full_name,
        "students_data": students_data
    }

    all_students = db.query(StudentProfile).all()
    teachers = db.query(User).filter(User.role == "teacher").all()
    school_wide = {"total_students": len(all_students), "total_hours": 0, "avg_hours": 0, "total_assignments": 0, "top_students": []}

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "all_students": all_students,
        "teachers": teachers,
        "school_wide": school_wide,
        "student_report": None,
        "teacher_report": teacher_report
    })


if __name__ == "__main__":
    import uvicorn
    print("\n🎵 Music School App starting...")
    print("Open your browser and go to: http://localhost:8000")
    print("Demo logins are in the README.md file\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)