from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./music_school.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # manager, coordinator, teacher, student, parent, admin
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    parent_profile = relationship("ParentProfile", back_populates="user", uselist=False)


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_day = Column(String)  # e.g. "Monday 4:00 PM"
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Fixed: explicitly specify which foreign key to use
    user = relationship("User", back_populates="student_profile", foreign_keys=[user_id])
    
    practice_logs = relationship("PracticeLog", back_populates="student")
    assignments = relationship("Assignment", back_populates="student")
    parent_links = relationship("ParentStudentLink", back_populates="student")


class ParentProfile(Base):
    __tablename__ = "parent_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="parent_profile")
    student_links = relationship("ParentStudentLink", back_populates="parent")


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parent_profiles.id"))
    student_id = Column(Integer, ForeignKey("student_profiles.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parent = relationship("ParentProfile", back_populates="student_links")
    student = relationship("StudentProfile", back_populates="parent_links")


class PracticeLog(Base):
    __tablename__ = "practice_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"))
    date = Column(String)  # YYYY-MM-DD
    minutes = Column(Integer)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("StudentProfile", back_populates="practice_logs")


class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("student_profiles.id"))
    week_start = Column(String)
    title = Column(String)
    description = Column(Text)
    youtube_links = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("StudentProfile", back_populates="assignments")
    uploads = relationship("StudentUpload", back_populates="assignment")


class StudentUpload(Base):
    __tablename__ = "student_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"))
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    file_path = Column(String)
    description = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    assignment = relationship("Assignment", back_populates="uploads")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== DATABASE FUNCTIONS ====================

def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()