"""Relational schema for the knowledge base, student state and memory.

Design notes
------------
* Knowledge-base tables (skills, courses, prerequisites, course_skills, modules,
  resources, questions, goals, minors, rules) are loaded from plain CSV/JSON
  seed files and carry `source` columns so every fact is traceable.
* Student state is *evidence based*: `evidence` rows are the single source of
  truth for what a student knows; `skill_states` is a derived cache that is
  recomputed whenever evidence or the knowledge base changes.
* Plans are versioned (`plans`), with the reason and the diff against the
  previous version, so the buddy can explain how a plan changed.
* Long-term memory = profile + evidence + plan versions + `memories`
  (decisions/facts) + `messages`, all keyed by student.
"""
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Knowledge base
# --------------------------------------------------------------------------
class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    # skills that should be learnt before this one (comma separated ids)
    prereq_skills: Mapped[str] = mapped_column(Text, default="")


class Course(Base):
    __tablename__ = "courses"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(64))
    credits: Mapped[int] = mapped_column(Integer)
    # odd | even | both
    offered: Mapped[str] = mapped_column(String(8))
    # core | dept_elective | open_elective | minor | online
    course_type: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16), default="offline")
    # programme the course is core for (blank = shared/open)
    programme: Mapped[str] = mapped_column(String(64), default="")
    # recommended semester for core courses (0 = any)
    semester: Mapped[int] = mapped_column(Integer, default=0)
    syllabus: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[str] = mapped_column(Text, default="")
    weekly_hours: Mapped[int] = mapped_column(Integer, default=0)  # self-study hours/week
    source: Mapped[str] = mapped_column(Text, default="")
    last_verified: Mapped[str] = mapped_column(String(16), default="")


class Prerequisite(Base):
    __tablename__ = "prerequisites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(ForeignKey("courses.code", ondelete="CASCADE"))
    prereq_code: Mapped[str] = mapped_column(ForeignKey("courses.code", ondelete="CASCADE"))
    min_grade: Mapped[str] = mapped_column(String(4), default="D")


class CourseSkill(Base):
    __tablename__ = "course_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(ForeignKey("courses.code", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    # proficiency the course brings the skill up to (0..1)
    level: Mapped[float] = mapped_column(Float)


class Module(Base):
    __tablename__ = "modules"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_code: Mapped[str] = mapped_column(String(32), default="")
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300))
    seq: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1 intro, 2 core, 3 advanced
    kind: Mapped[str] = mapped_column(String(32), default="lesson")  # lesson | lab | project
    est_hours: Mapped[float] = mapped_column(Float, default=1.0)
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    source: Mapped[str] = mapped_column(Text, default="")


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    provider: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    skill_ids: Mapped[str] = mapped_column(Text)  # comma separated
    format: Mapped[str] = mapped_column(String(32))  # video | text | course | practice
    level: Mapped[int] = mapped_column(Integer, default=1)
    est_hours: Mapped[float] = mapped_column(Float, default=2)
    license: Mapped[str] = mapped_column(String(64), default="")
    credit_eligible: Mapped[bool] = mapped_column(Boolean, default=False)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    difficulty: Mapped[int] = mapped_column(Integer)  # 1 easy, 2 medium, 3 hard
    kind: Mapped[str] = mapped_column(String(16))  # diagnostic | practice
    qtype: Mapped[str] = mapped_column(String(16))  # mcq | numeric
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(Text, default="")


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    # [{"skill": id, "target": 0..1, "importance": 1..3}]
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    # [{"title", "kind", "semester_offset" | "before_semester", "detail"}]
    milestones: Mapped[list] = mapped_column(JSON, default=list)
    mastery_criteria: Mapped[list] = mapped_column(JSON, default=list)
    recommended_minor: Mapped[str] = mapped_column(String(64), default="")
    protect_cgpa: Mapped[bool] = mapped_column(Boolean, default=False)


class Minor(Base):
    __tablename__ = "minors"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(64))
    min_cgpa: Mapped[float] = mapped_column(Float)
    credits_required: Mapped[int] = mapped_column(Integer)
    courses: Mapped[list] = mapped_column(JSON, default=list)
    excluded_programmes: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(Text, default="")


class Rule(Base):
    __tablename__ = "rules"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | list | float | int | str] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(Text, default="")


class Programme(Base):
    __tablename__ = "programmes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(64))
    total_credits: Mapped[int] = mapped_column(Integer)
    # {"5": {"dept_elective": 1, "open_elective": 1}, ...}
    elective_slots: Mapped[dict] = mapped_column(JSON, default=dict)
    # discipline skills a "core" goal (GATE, higher studies, core job) resolves to
    core_skills: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(Text, default="")


# --------------------------------------------------------------------------
# Students, evidence, plans, memory
# --------------------------------------------------------------------------
class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    programme: Mapped[str] = mapped_column(String(64))
    year: Mapped[int] = mapped_column(Integer)
    current_semester: Mapped[int] = mapped_column(Integer)  # semester being planned next
    cgpa: Mapped[float] = mapped_column(Float)
    # [{"code", "grade", "semester"}]; grade "F" = backlog
    completed_courses: Mapped[list] = mapped_column(JSON, default=list)
    goal_id: Mapped[str] = mapped_column(String(64), default="")
    goal_text: Mapped[str] = mapped_column(Text, default="")
    interests: Mapped[list] = mapped_column(JSON, default=list)
    # {"hours_per_week", "max_credits", "open_elective_slots", "not_together": [[a,b]],
    #  "excluded_courses": [], "pinned_courses": []}
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"formats": ["video", "practice"], "pace": "steady"}
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    persona: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(String(64))
    # grade | assessment | exercise | project | mock | self
    source: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float)  # 0..1
    detail: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    time_spent_min: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModuleProgress(Base):
    __tablename__ = "module_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="done")  # done | skipped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[dict] = mapped_column(JSON)
    diff: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Memory(Base):
    """Long-term memory items: decisions, stated facts, overrides, session summaries."""
    __tablename__ = "memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # decision | fact | summary | override
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    state: Mapped[dict] = mapped_column(JSON)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
