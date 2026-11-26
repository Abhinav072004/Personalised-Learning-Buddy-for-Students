import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import assessment, chat, config, llm
from .db import get_db
from .diagnose import match_goal
from .kb import load_kb
from .models import (Base, Course, CourseSkill, DiagnosticSession, Evidence, Goal, Memory, Message, Minor, Module,
                     ModuleProgress, Plan, Prerequisite, Programme, Question, Resource, Rule, Skill, Student)
from .seed import init_db
from .services import compute, current_plan, simulate

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app):
    for attempt in range(30):
        try:
            if init_db():
                log.info("Seeded database from %s", config.SEED_DIR)
            break
        except Exception as e:  # database container still starting
            import time
            log.warning("DB not ready (%s); retrying", e)
            time.sleep(2)
    yield


app = FastAPI(title="Personalised Learning Buddy", version="1.0.0", lifespan=lifespan)


def _student(db: Session, sid: str) -> Student:
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(404, f"student {sid} not found")
    return s


def _pct(x):
    return None if x is None else round(x, 3)


# ---------------------------------------------------------------- health
@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": config.llm_enabled(), "llm_model": config.LLM_MODEL}


@app.get("/api/metrics")
def metrics(db: Session = Depends(get_db)):
    """Engineering metrics (LLM calls, tokens, latency, failures) and product metrics."""
    students = db.scalars(select(Student)).all()
    plans = db.scalars(select(Plan)).all()
    fb = [m for m in db.scalars(select(Memory).where(Memory.kind == "feedback"))]
    ratings = [int(m.content.split("rating=")[1].split()[0]) for m in fb if "rating=" in m.content]
    progress = db.scalars(select(ModuleProgress)).all()
    active = {p.student_id for p in progress}
    return {"llm": llm.metrics(),
            "product": {"students": len(students), "plan_versions": len(plans),
                        "students_with_plan": len({p.student_id for p in plans}),
                        "students_following_plan": len(active), "modules_completed": len(progress),
                        "feedback_count": len(ratings), "avg_usefulness": round(sum(ratings) / len(ratings), 2) if ratings else None}}


# ---------------------------------------------------------------- knowledge base (read)
@app.get("/api/kb/summary")
def kb_summary(db: Session = Depends(get_db)):
    kb = load_kb(db)
    return {"skills": [{"id": k, "name": v["name"], "category": v["category"]} for k, v in kb.skills.items()],
            "goals": [{"id": k, "name": v["name"], "description": v["description"]} for k, v in kb.goals.items()],
            "programmes": [{"id": k, "name": v["name"]} for k, v in kb.programmes.items()],
            "courses": [{"code": k, "title": v["title"], "credits": v["credits"], "type": v["course_type"], "offered": v["offered"],
                         "programme": v["programme"], "semester": v["semester"], "skills": kb.course_skills.get(k, {}),
                         "prereqs": kb.prereqs.get(k, []), "source": v["source"]} for k, v in kb.courses.items()],
            "fingerprint": kb.fingerprint}


# ---------------------------------------------------------------- students
@app.get("/api/students")
def list_students(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "programme": s.programme, "year": s.year, "cgpa": s.cgpa, "goal_id": s.goal_id,
             "persona": s.persona} for s in db.scalars(select(Student).order_by(Student.id))]


class Onboard(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    programme: str
    year: int = Field(ge=1, le=4)
    cgpa: float = Field(ge=0, le=10)
    completed_courses: list[dict] = []
    goal_text: str = ""
    goal_id: str = ""
    interests: list[str] = []
    hours_per_week: float = Field(6, gt=0, le=60)
    max_credits: int | None = None
    formats: list[str] = ["video", "practice"]
    pace: str = "steady"
    self_ratings: dict[str, float] = {}


@app.post("/api/students")
def onboard(body: Onboard, db: Session = Depends(get_db)):
    kb = load_kb(db)
    if body.programme not in kb.programmes:
        raise HTTPException(400, "unknown programme")
    goal_id = body.goal_id if body.goal_id in kb.goals else ""
    candidates = []
    if not goal_id and body.goal_text:
        m = match_goal(kb, body.goal_text)
        candidates = [g for g, _ in m]
        if m and (len(m) == 1 or m[0][1] > m[1][1]):
            goal_id = m[0][0]
    completed = body.completed_courses
    if not completed:  # assume the programme's core courses so far are done (student can edit)
        completed = [{"code": c, "grade": "B", "semester": v["semester"]} for c, v in kb.courses.items()
                     if v["course_type"] == "core" and body.programme in v["programme"].split(",") and 0 < v["semester"] < 2 * body.year]
    for c in completed:
        if c.get("code") not in kb.courses:
            raise HTTPException(400, f"unknown course {c.get('code')}")
    sid = "U" + uuid.uuid4().hex[:6].upper()
    cons = {"hours_per_week": body.hours_per_week, "not_together": [], "excluded_courses": [], "pinned_courses": []}
    if body.max_credits:
        cons["max_credits"] = body.max_credits
    s = Student(id=sid, name=body.name, programme=body.programme, year=body.year, current_semester=2 * body.year,
                cgpa=body.cgpa, completed_courses=completed, goal_id=goal_id, goal_text=body.goal_text,
                interests=body.interests, constraints=cons, preferences={"formats": body.formats, "pace": body.pace},
                persona="Onboarded via UI")
    db.add(s)
    db.flush()
    for skill, val in body.self_ratings.items():
        if skill in kb.skills:
            db.add(Evidence(student_id=sid, skill_id=skill, source="self", score=max(0, min(1, val)), detail="Self-rating at onboarding"))
    db.add(Memory(student_id=sid, kind="fact", content=f"Onboarded: goal '{body.goal_text or goal_id}', {body.hours_per_week:g} h/week, prefers {', '.join(body.formats)}"))
    db.commit()
    return {"id": sid, "goal_id": goal_id, "goal_candidates": candidates}


@app.get("/api/students/{sid}")
def get_student(sid: str, db: Session = Depends(get_db)):
    s = _student(db, sid)
    return {c.name: getattr(s, c.name) for c in s.__table__.columns}


@app.patch("/api/students/{sid}")
def update_student(sid: str, patch: dict = Body(...), db: Session = Depends(get_db)):
    """Admin / profile edit. Any change re-plans immediately."""
    s = _student(db, sid)
    allowed = {"name", "programme", "year", "current_semester", "cgpa", "completed_courses", "goal_id", "goal_text",
               "interests", "constraints", "preferences", "persona"}
    kb = load_kb(db)
    for k, v in patch.items():
        if k not in allowed:
            raise HTTPException(400, f"field {k} not editable")
        if k == "goal_id" and v and v not in kb.goals:
            raise HTTPException(400, "unknown goal")
        setattr(s, k, v)
    db.add(Memory(student_id=sid, kind="decision", content=f"Profile edited: {', '.join(patch)}"))
    db.commit()
    res = current_plan(db, s, reason=f"Profile edited ({', '.join(patch)})")
    return {"ok": True, "plan_version": res["plan_record"].version}


@app.get("/api/students/{sid}/dashboard")
def dashboard(sid: str, db: Session = Depends(get_db)):
    s = _student(db, sid)
    res = current_plan(db, s)
    rec = res["plan_record"]
    kb = res["kb"]
    states = res["states"]
    skills = [{"skill": k, "name": kb.skills[k]["name"], "category": kb.skills[k]["category"], **{x: v[x] for x in
              ("mastery", "confidence", "tested", "struggling", "n_evidence", "sources", "evidence")}}
              for k, v in states.items() if v["n_evidence"]]
    done = {m.module_id for m in db.scalars(select(ModuleProgress).where(ModuleProgress.student_id == sid))}
    return {"student": res["student"], "diagnosis": res["diagnosis"], "plan": rec.content, "validation": rec.validation,
            "plan_version": rec.version, "plan_reason": rec.reason, "plan_diff": rec.diff, "skills": skills,
            "modules_done": sorted(done), "llm_configured": config.llm_enabled()}


@app.get("/api/students/{sid}/plans")
def plan_history(sid: str, db: Session = Depends(get_db)):
    _student(db, sid)
    rows = db.scalars(select(Plan).where(Plan.student_id == sid).order_by(Plan.version.desc()))
    return [{"version": p.version, "reason": p.reason, "created_at": p.created_at, "diff": p.diff,
             "passed": p.validation.get("passed"), "readiness_projected": p.content.get("readiness_projected")} for p in rows]


@app.get("/api/students/{sid}/plans/{version}")
def plan_version(sid: str, version: int, db: Session = Depends(get_db)):
    p = db.scalars(select(Plan).where(Plan.student_id == sid, Plan.version == version)).first()
    if not p:
        raise HTTPException(404, "no such plan version")
    return {"version": p.version, "reason": p.reason, "content": p.content, "validation": p.validation, "diff": p.diff}


class Override(BaseModel):
    type: str
    course: str | None = None
    courses: list[str] | None = None
    goal: str | None = None
    hours: float | None = None
    credits: int | None = None
    formats: list[str] | None = None


@app.post("/api/students/{sid}/override")
def override(sid: str, body: Override, db: Session = Depends(get_db)):
    """Student overrides from the plan UI (reject/ask for a course, change goal, hours...)."""
    s = _student(db, sid)
    kb = load_kb(db)
    a = {k: v for k, v in body.model_dump().items() if v is not None}
    if a.get("course") and a["course"] not in kb.courses:
        raise HTTPException(400, f"{a['course']} is not in the course catalogue")
    if a.get("goal") and a["goal"] not in kb.goals:
        raise HTTPException(400, "unknown goal")
    applied = chat.apply_actions(db, kb, s, [a])
    res = current_plan(db, s, reason="Student override: " + "; ".join(applied))
    rec = res["plan_record"]
    return {"applied": applied, "plan_version": rec.version, "diff": rec.diff, "infeasible": res["plan"].get("infeasible", []),
            "validation_passed": rec.validation["passed"]}


class Scenario(BaseModel):
    preset: str | None = None  # strong | weak
    skill: str | None = None
    evidence: list[dict] = []


@app.post("/api/students/{sid}/simulate")
def simulate_route(sid: str, body: Scenario, db: Session = Depends(get_db)):
    """Demonstrating adaptation: plan after a simulated strong vs weak mid-semester quiz (not saved)."""
    s = _student(db, sid)
    kb = load_kb(db)
    ev = list(body.evidence)
    skill = body.skill
    if body.preset:
        if not skill:
            reqs = kb.goal_requirements(s.goal_id or "", s.programme)
            skill = reqs[0]["skill"] if reqs else "prog_fund"
        if body.preset == "strong":
            ev += [{"skill_id": skill, "source": "assessment", "score": 0.92, "attempts": 1, "time_spent_min": 10, "detail": "Simulated mid-semester quiz 92%"},
                   {"skill_id": skill, "source": "exercise", "score": 1.0, "attempts": 1, "time_spent_min": 2, "detail": "Simulated exercise"}]
        else:
            ev += [{"skill_id": skill, "source": "assessment", "score": 0.22, "attempts": 3, "time_spent_min": 35, "detail": "Simulated mid-semester quiz 22%"},
                   {"skill_id": skill, "source": "exercise", "score": 0.0, "attempts": 3, "time_spent_min": 9, "detail": "Simulated exercise"},
                   {"skill_id": skill, "source": "exercise", "score": 0.0, "attempts": 2, "time_spent_min": 8, "detail": "Simulated exercise"}]
    for e in ev:
        if e.get("skill_id") not in kb.skills:
            raise HTTPException(400, "unknown skill in evidence")
        e.setdefault("attempts", 1)
        e.setdefault("time_spent_min", 0)
        e.setdefault("detail", "simulated")
    out = simulate(db, s, ev)
    pick = lambda r: {"plan": r["plan"], "validation": r["validation"], "readiness": r["diagnosis"]["readiness"]}
    return {"skill": skill, "evidence": ev, "before": pick(out["before"]), "after": pick(out["after"]), "diff": out["diff"]}


class EvidenceIn(BaseModel):
    skill_id: str
    source: str = Field(pattern="^(assessment|exercise|project|mock|grade|self)$")
    score: float = Field(ge=0, le=1)
    detail: str = ""
    attempts: int = 1
    time_spent_min: float = 0


@app.post("/api/students/{sid}/evidence")
def add_evidence(sid: str, body: EvidenceIn, db: Session = Depends(get_db)):
    """Record evidence (e.g. project checkpoint or mock interview graded by a mentor)."""
    s = _student(db, sid)
    if body.skill_id not in load_kb(db).skills:
        raise HTTPException(400, "unknown skill")
    db.add(Evidence(student_id=sid, **body.model_dump()))
    db.commit()
    res = current_plan(db, s, reason=f"New {body.source} evidence on {body.skill_id}")
    return {"plan_version": res["plan_record"].version, "diff": res["plan_record"].diff}


@app.post("/api/students/{sid}/modules/{mid}/complete")
def complete_module(sid: str, mid: str, db: Session = Depends(get_db)):
    s = _student(db, sid)
    if mid not in load_kb(db).modules:
        raise HTTPException(404, "unknown module")
    if not db.scalars(select(ModuleProgress).where(ModuleProgress.student_id == sid, ModuleProgress.module_id == mid)).first():
        db.add(ModuleProgress(student_id=sid, module_id=mid))
        db.commit()
    res = current_plan(db, s, reason=f"Module {mid} completed")
    return {"plan_version": res["plan_record"].version}


# ---------------------------------------------------------------- assessments
class StartAssessment(BaseModel):
    mode: str = Field("diagnostic", pattern="^(diagnostic|checkpoint|mock)$")
    skill: str | None = None


@app.post("/api/students/{sid}/assessments")
def start_assessment(sid: str, body: StartAssessment, db: Session = Depends(get_db)):
    s = _student(db, sid)
    res = compute(db, s)
    kb = res["kb"]
    if body.mode == "checkpoint" and body.skill not in kb.skills:
        raise HTTPException(400, "checkpoint needs a valid skill")
    out = assessment.start_session(db, kb, res["student"], res["states"], body.mode, body.skill)
    if not out["question"]:
        raise HTTPException(400, "no questions available")
    return out


class AnswerIn(BaseModel):
    question_id: str
    choice: str
    seconds: float = 0


@app.post("/api/assessments/{session_id}/answer")
def answer_assessment(session_id: str, body: AnswerIn, db: Session = Depends(get_db)):
    kb = load_kb(db)
    try:
        out = assessment.answer(db, kb, session_id, body.question_id, body.choice, body.seconds)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if out["finished"]:
        sess = db.get(DiagnosticSession, session_id)
        s = _student(db, sess.student_id)
        res = current_plan(db, s, reason=f"{sess.state['mode'].capitalize()} completed")
        out["plan_version"] = res["plan_record"].version
        out["plan_diff"] = res["plan_record"].diff
        out["summary"] = [{"skill": k, "name": kb.skills[k]["name"], "mastery": res["states"][k]["mastery"],
                           "status": next((g["status"] for g in res["diagnosis"]["gaps"] if g["skill"] == k), None)}
                          for k in sess.state["skills"]]
    return out


@app.get("/api/students/{sid}/practice")
def practice(sid: str, skill: str, db: Session = Depends(get_db)):
    s = _student(db, sid)
    res = compute(db, s)
    if skill not in res["kb"].skills:
        raise HTTPException(400, "unknown skill")
    q = assessment.next_practice(db, res["kb"], sid, skill, res["states"][skill]["mastery"])
    if not q:
        raise HTTPException(404, "no practice questions for this skill")
    return q


class PracticeAnswer(AnswerIn):
    attempts: int = 1


@app.post("/api/students/{sid}/practice/answer")
def practice_answer(sid: str, body: PracticeAnswer, db: Session = Depends(get_db)):
    s = _student(db, sid)
    kb = load_kb(db)
    if body.question_id not in kb.questions:
        raise HTTPException(400, "unknown question")
    out = assessment.answer_practice(db, kb, sid, body.question_id, body.choice, body.attempts, body.seconds)
    res = current_plan(db, s, reason=f"Practice on {kb.questions[body.question_id]['skill_id']}")
    st = res["states"][kb.questions[body.question_id]["skill_id"]]
    out.update(mastery=st["mastery"], confidence=st["confidence"], plan_version=res["plan_record"].version)
    return out


# ---------------------------------------------------------------- chat & memory
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


@app.post("/api/students/{sid}/chat")
def chat_route(sid: str, body: ChatIn, db: Session = Depends(get_db)):
    s = _student(db, sid)
    session_id = body.session_id or uuid.uuid4().hex[:12]
    out = chat.handle(db, load_kb(db), s, session_id, body.message)
    return {"session_id": session_id, **out}


@app.get("/api/students/{sid}/chat")
def chat_history(sid: str, session_id: str | None = None, db: Session = Depends(get_db)):
    q = select(Message).where(Message.student_id == sid)
    if session_id:
        q = q.where(Message.session_id == session_id)
    rows = db.scalars(q.order_by(Message.id.desc()).limit(60)).all()
    return [{"role": m.role, "content": m.content, "session_id": m.session_id, "meta": m.meta, "at": m.created_at} for m in reversed(rows)]


@app.get("/api/students/{sid}/memory")
def memory(sid: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Memory).where(Memory.student_id == sid).order_by(Memory.id.desc()).limit(50))
    return [{"kind": m.kind, "content": m.content, "at": m.created_at} for m in rows]


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    target: str = "plan"
    comment: str = Field("", max_length=500)


@app.post("/api/students/{sid}/feedback")
def feedback(sid: str, body: FeedbackIn, db: Session = Depends(get_db)):
    _student(db, sid)
    db.add(Memory(student_id=sid, kind="feedback", content=f"rating={body.rating} target={body.target} {body.comment}".strip()))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- admin (data control)
TABLES = {m.__tablename__: m for m in (Student, Evidence, Course, Prerequisite, CourseSkill, Skill, Module, Resource,
                                        Question, Goal, Minor, Rule, Programme, Plan, Memory)}
KB_TABLES = {"courses", "prerequisites", "course_skills", "skills", "modules", "resources", "questions", "goals", "minors",
             "rules", "programmes"}


def _row(o):
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


def _replan_all(db: Session, reason: str) -> int:
    kb = load_kb(db)
    n = 0
    for s in db.scalars(select(Student)):
        res = compute(db, s, kb=kb)
        from .services import latest_plan, diff_plans
        last = latest_plan(db, s.id)
        if last and last.fingerprint != res["fingerprint"]:
            diff = diff_plans(last.content, res["plan"])
            if diff["changes"] == ["No material change."]:
                last.fingerprint, last.content, last.validation = res["fingerprint"], res["plan"], res["validation"]
                continue
            db.add(Plan(student_id=s.id, version=last.version + 1, fingerprint=res["fingerprint"], reason=reason,
                        content=res["plan"], validation=res["validation"], diff=diff))
            n += 1
    db.commit()
    return n


@app.get("/api/admin/tables")
def admin_tables():
    return sorted(TABLES)


@app.get("/api/admin/tables/{name}")
def admin_list(name: str, limit: int = 500, db: Session = Depends(get_db)):
    if name not in TABLES:
        raise HTTPException(404, "unknown table")
    return [_row(r) for r in db.scalars(select(TABLES[name]).limit(limit))]


@app.put("/api/admin/tables/{name}/{pk}")
def admin_update(name: str, pk: str, values: dict = Body(...), db: Session = Depends(get_db)):
    """Edit any row. KB edits re-plan every student that has a plan; student/evidence edits re-plan that student."""
    if name not in TABLES:
        raise HTTPException(404, "unknown table")
    model = TABLES[name]
    pkcol = sa_inspect(model).primary_key[0]
    key = int(pk) if pkcol.type.python_type is int else pk
    row = db.get(model, key)
    if not row:
        raise HTTPException(404, "row not found")
    cols = {c.name for c in model.__table__.columns}
    for k, v in values.items():
        if k not in cols or k == pkcol.name:
            raise HTTPException(400, f"column {k} not editable")
        setattr(row, k, v)
    db.commit()
    return {"ok": True, **_after_edit(db, name, row)}


@app.post("/api/admin/tables/{name}")
def admin_create(name: str, values: dict = Body(...), db: Session = Depends(get_db)):
    if name not in TABLES:
        raise HTTPException(404, "unknown table")
    row = TABLES[name](**values)
    db.add(row)
    db.commit()
    return {"ok": True, **_after_edit(db, name, row)}


@app.delete("/api/admin/tables/{name}/{pk}")
def admin_delete(name: str, pk: str, db: Session = Depends(get_db)):
    if name not in TABLES:
        raise HTTPException(404, "unknown table")
    model = TABLES[name]
    pkcol = sa_inspect(model).primary_key[0]
    row = db.get(model, int(pk) if pkcol.type.python_type is int else pk)
    if not row:
        raise HTTPException(404, "row not found")
    sid = getattr(row, "student_id", None)
    db.delete(row)
    db.commit()
    if name in KB_TABLES:
        return {"ok": True, "replanned": _replan_all(db, f"Knowledge base edited ({name})")}
    if sid and db.get(Student, sid):
        current_plan(db, db.get(Student, sid), reason=f"Admin edit ({name})")
    return {"ok": True}


def _after_edit(db: Session, name: str, row) -> dict:
    if name in KB_TABLES:
        return {"replanned": _replan_all(db, f"Knowledge base edited ({name})")}
    sid = row.id if name == "students" else getattr(row, "student_id", None)
    if sid and name != "plans" and db.get(Student, sid):
        res = current_plan(db, db.get(Student, sid), reason=f"Admin edit ({name})")
        return {"plan_version": res["plan_record"].version}
    return {}


@app.post("/api/admin/reset")
def admin_reset():
    init_db(reset=True)
    return {"ok": True, "message": "Database restored to the original seed state."}


# ---------------------------------------------------------------- frontend
if config.FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(config.FRONTEND_DIR / "index.html")

    @app.get("/admin")
    def admin_page():
        return FileResponse(config.FRONTEND_DIR / "admin.html")
