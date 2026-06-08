# Music School Management App

A custom web application for your music school to track student practice, manage weekly assignments, enable teacher-student-parent communication, and give managers/coordinators oversight.

## Features (Current Version - MVP)

- **Role-based access** for: Manager, School Coordinator, Teacher, Student, Parent
- Students can log daily/weekly practice time and see running totals
- Teachers can create weekly assignments with descriptions, YouTube links, and file uploads
- Students can upload progress videos/files for teachers to review
- Parents can view their child's full dashboard (practice, assignments, uploads) and send messages to the teacher
- Basic calendar/schedule view
- Manager tools for user and permission management

## Tech Stack
- Python + FastAPI
- SQLite database (no external database needed)
- Jinja2 templates + Tailwind CSS
- File uploads stored locally

## How to Run (Very Easy)

### 1. Install Python (if you don't have it)
Make sure you have Python 3.10 or newer.

### 2. Install dependencies
Open terminal/command prompt in this folder and run:

```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python main.py
```

Or with uvicorn (recommended for development):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open in browser
Go to: **http://localhost:8000**

## Demo Login Accounts (for testing)

| Role                | Email                    | Password   | Notes |
|---------------------|--------------------------|------------|-------|
| Manager             | manager@school.com       | admin123   | Full access + Reports |
| Teacher             | teacher@school.com       | teach123   | Can create assignments |
| Student             | student@school.com       | student123 | Can log practice |
| Parent              | parent@school.com        | parent123  | Can view student dashboard |
| Coordinator         | coordinator@school.com   | coord123   | View + Reports access |

**New in this version:**
- Students and Parents can now **create their own accounts** at `/register`
- Managers & Coordinators have a full **Reports Dashboard** (`/manager/reports`) with:
  - Student-specific progress & homework reports
  - School-wide practice analytics
  - Per-teacher student progress overview

You can create more users from the registration page or Manager tools.

## Next Steps / Roadmap
We can add these features in future versions:
- Full recurring calendar with lesson scheduling
- Video recording directly in browser
- Better messaging system (chat-like)
- Reports and analytics (practice streaks, completion rates)
- Mobile-friendly improvements / PWA
- Email notifications
- Integration with existing tools (Google Calendar, etc.)

## Support
Tell me what you want to improve or add next and I'll update the app for you.

---

Built specifically for your music school. Let's make it perfect together.