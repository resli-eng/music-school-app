from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime
import os
import shutil
from typing import Optional

from database import (
    create_tables, get_db, User, StudentProfile, ParentProfile,
    PracticeLog, Assignment, StudentUpload, Message, SessionLocal
)

app = FastAPI(title="Music School App")
templates = Jinja2Templates(directory="templates")
os.makedirs("uploads", exist_ok=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

create_tables()

def seed_demo_data():
    db = SessionLocal()
    if db.query(User).count() > 0:
        db.close()
        return

    users_data = [
        {"email": "manager@school.com", "password": "admin123", "role": "manager", "full_name": "Alex Rivera (Manager)"},
        {"email": "coordinator@school.com", "password": "coord123", "role": "coordinator", "full_name": "Jordan Lee (Coordinator)"},
        {"email": "teacher@school.com", "password": "teach123", "role": "teacher", "full_name": "Ms. Emily Chen"},
        {"email": "student@school.com", "password": "student123", "role": "student", "full_name": "Liam Thompson"},
        {"email": "parent@school.com", "password": "parent123", "role": "parent", "full_name": "Sarah Thompson (Parent)"},
    ]

    for u in users_data:
        user = User(email=u["email"], password_hash=hash_password(u["password"]), role=u["role"], full_name=u["full_name"])
        db.add(user)
    db.commit()

    # Add demo student, parent, logs, etc. (same as before)
    db.close()

seed_demo_data()

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url=f"/dashboard/{user.role}")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})
    response = RedirectResponse(url=f"/dashboard/{user.role}", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")
    return response

# Add other routes (student_dashboard, teacher_dashboard, etc.) here if needed...
# For now, upload this and test login first.

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
