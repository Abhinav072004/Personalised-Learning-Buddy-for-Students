"""Orchestration: student state -> diagnosis -> plan -> validation, with versioning.

`current_plan()` is the single entry point. It fingerprints everything a plan
depends on (student profile, evidence, module progress, KB content). If the
fingerprint differs from the latest stored plan - because of new quiz evidence,
a goal change, a student override, or an admin/Adminer edit - a new plan
version is generated, validated, diffed against the previous one and stored
with a human-readable reason. Otherwise the stored plan is returned.
"""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .diagnose import diagnose
from .kb import KB, load_kb
from .mastery import skill_states
from .models import Evidence, Memory, ModuleProgress, Plan, Student
from .planner import build_plan
from .validator import validate


def student_dict(s: Student) -> dict:
    return {c.name: getattr(s, c.name) for c in s.__table__.columns if c.name != "created_at"}


def evidence_rows(db: Session, sid: str) -> list[dict]:
    rows = db.scalars(select(Evidence).where(Evidence.student_id == sid).order_by(Evidence.created_at, Evidence.id))
    return [{"id": e.id, "skill_id": e.skill_id, "source": e.source, "score": e.score, "detail": e.detail,
             "attempts": e.attempts, "time_spent_min": e.time_spent_min,
             "created_at": e.created_at.isoformat() if e.created_at else None} for e in rows]


def done_modules(db: Session, sid: str) -> set:
    return {m.module_id for m in db.scalars(select(ModuleProgress).where(ModuleProgress.student_id == sid))}


def pace_factor(ev: list[dict], kb: KB) -> float:
    """Learning-pace signal: if the student consistently needs more time/attempts than
    expected on exercises, schedule more time per module (and less if faster)."""
    ex = [e for e in ev if e["source"] in ("exercise", "assessment") and e["time_spent_min"]]
    if len(ex) < 3:
        return 1.0
    ratio = sum(e["time_spent_min"] / (2.0 * max(1, e["attempts"]) if e["source"] == "exercise" else 10.0) for e in ex[-8:]) / len(ex[-8:])
    attempts = sum(e["attempts"] for e in ex[-8:]) / len(ex[-8:])
    f = 1.0 + 0.15 * (ratio > 1.5) + 0.1 * (attempts > 2) - 0.1 * (ratio < 0.6)
    return round(f, 2)


def compute(db: Session, student: Student, kb: KB | None = None, extra_evidence: list[dict] | None = None,
            student_override: dict | None = None) -> dict:
    kb = kb or load_kb(db)
    sd = student_dict(student)
    if student_override:
        sd.update(student_override)
    ev = evidence_rows(db, student.id) + (extra_evidence or [])
    states = skill_states(kb, sd, ev)
    diag = diagnose(kb, sd, states)
    dm = done_modules(db, student.id)
    pf = pace_factor(ev, kb)
    plan = build_plan(kb, sd, states, diag, dm, pf)
    val = validate(kb, sd, plan, states)
    fp_src = json.dumps([sd, [(e["skill_id"], e["source"], e["score"], e["attempts"], e.get("time_spent_min")) for e in ev],
                         sorted(dm), kb.fingerprint], sort_keys=True, default=str)
    return {"kb": kb, "student": sd, "evidence": ev, "states": states, "diagnosis": diag, "plan": plan,
            "validation": val, "fingerprint": hashlib.sha256(fp_src.encode()).hexdigest()[:24]}


def plan_summary(plan: dict) -> dict:
    return {
        "courses": {str(s["semester"]): sorted(c["code"] for c in s["courses"] if c["code"]) for s in plan["semesters"]},
        "track_skills": sorted({it["skill"] for w in plan["learning_track"]["weeks"] for it in w["items"] if it.get("skill")}),
        "track_items": sorted({it.get("module") or it["title"] for w in plan["learning_track"]["weeks"] for it in w["items"]}),
        "remedial": sorted({it["title"] for w in plan["learning_track"]["weeks"] for it in w["items"] if it["type"] == "remedial"}),
        "deferred_skills": sorted({it["skill"] for it in plan["learning_track"]["deferred"] if it.get("skill")}),
        "readiness_projected": plan.get("readiness_projected"), "goal": (plan.get("goal") or {}).get("id"),
    }


def diff_plans(old: dict | None, new: dict) -> dict:
    if not old:
        return {"first_version": True, "changes": ["First plan created."]}
    a, b = plan_summary(old), plan_summary(new)
    changes, out = [], {"added_courses": {}, "removed_courses": {}}
    before = {x["skill"]: x for x in old.get("skills", [])}
    for x in new.get("skills", []):
        b0 = before.get(x["skill"])
        if b0 and (abs(b0["mastery"] - x["mastery"]) >= 0.05 or b0["status"] != x["status"]):
            changes.append(f"{x['name']}: {_pct(b0['mastery'])} ({b0['status'].replace('_', ' ')}) -> "
                           f"{_pct(x['mastery'])} ({x['status'].replace('_', ' ')})")
    for sem in sorted(set(a["courses"]) | set(b["courses"]), key=int):
        add = sorted(set(b["courses"].get(sem, [])) - set(a["courses"].get(sem, [])))
        rem = sorted(set(a["courses"].get(sem, [])) - set(b["courses"].get(sem, [])))
        if add:
            out["added_courses"][sem] = add
            changes.append(f"Semester {sem}: added {', '.join(add)}")
        if rem:
            out["removed_courses"][sem] = rem
            changes.append(f"Semester {sem}: removed {', '.join(rem)}")
    sa, sb = set(a["track_skills"]), set(b["track_skills"])
    if sb - sa:
        changes.append("Learning track now covers " + ", ".join(sorted(sb - sa)))
    moved = (sa - sb) & set(b["deferred_skills"])
    if moved:
        changes.append("Moved to next semester to fit your weekly hours: " + ", ".join(sorted(moved)))
    if (sa - sb) - moved:
        changes.append("Dropped from learning track (demonstrated or no longer needed): " + ", ".join(sorted((sa - sb) - moved)))
    ia, ib = set(a["track_items"]), set(b["track_items"])
    if len(ia - ib) or len(ib - ia):
        changes.append(f"Learning track: {len(ib - ia)} items added, {len(ia - ib)} items removed")
    ra, rb = set(a["remedial"]), set(b["remedial"])
    if rb - ra:
        changes.append("Extra support added: " + "; ".join(sorted(rb - ra)))
    if a["goal"] != b["goal"]:
        changes.append(f"Goal changed from {a['goal']} to {b['goal']}")
    if a["readiness_projected"] != b["readiness_projected"]:
        changes.append(f"Projected goal readiness {_pct(a['readiness_projected'])} -> {_pct(b['readiness_projected'])}")
    out["changes"] = changes or ["No material change."]
    return out


def _pct(x):
    return "n/a" if x is None else f"{round(x * 100)}%"


def latest_plan(db: Session, sid: str) -> Plan | None:
    return db.scalars(select(Plan).where(Plan.student_id == sid).order_by(Plan.version.desc()).limit(1)).first()


def current_plan(db: Session, student: Student, reason: str = "") -> dict:
    """Return the up-to-date plan, creating a new version if anything it depends on changed."""
    res = compute(db, student)
    last = latest_plan(db, student.id)
    if last and last.fingerprint == res["fingerprint"]:
        res["plan_record"] = last
        return res
    diff = diff_plans(last.content if last else None, res["plan"])
    if last and diff.get("changes") == ["No material change."]:
        # inputs changed but the plan did not: refresh silently instead of creating a new version
        last.fingerprint, last.content, last.validation = res["fingerprint"], res["plan"], res["validation"]
        db.commit()
        res["plan_record"] = last
        return res
    if not reason:
        reason = "Initial plan" if not last else infer_reason(db, student.id, last)
    rec = Plan(student_id=student.id, version=(last.version + 1) if last else 1, fingerprint=res["fingerprint"],
               reason=reason, content=res["plan"], validation=res["validation"], diff=diff)
    db.add(rec)
    if last:
        db.add(Memory(student_id=student.id, kind="decision",
                      content=f"Plan v{rec.version}: {reason}. " + " | ".join(diff.get("changes", [])[:4])))
    db.commit()
    res["plan_record"] = rec
    return res


def infer_reason(db: Session, sid: str, last: Plan) -> str:
    newer = [e for e in db.scalars(select(Evidence).where(Evidence.student_id == sid)) if e.created_at and last.created_at
             and e.created_at.replace(tzinfo=None) > last.created_at.replace(tzinfo=None)]
    if newer:
        skills = sorted({e.skill_id for e in newer})
        return f"New evidence on {', '.join(skills[:4])}"
    return "Profile, constraints or knowledge base changed"


def simulate(db: Session, student: Student, scenario: list[dict]) -> dict:
    """What-if: plan after hypothetical evidence (e.g. strong vs weak mid-semester quiz). Not persisted."""
    base = compute(db, student)
    after = compute(db, student, kb=base["kb"], extra_evidence=[dict(e, detail=e.get("detail", "simulated")) for e in scenario])
    return {"before": base, "after": after, "diff": diff_plans(base["plan"], after["plan"])}
