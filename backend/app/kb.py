"""In-memory snapshot of the knowledge base.

The KB is small (hundreds of rows), so it is re-read from the database on each
request. That keeps the buddy consistent with any edit made through the admin
API *or directly in Adminer*: there is no stale cache to invalidate. A content
hash (`fingerprint`) of the snapshot is folded into each plan's fingerprint, so
a KB edit automatically triggers re-planning.
"""
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (Course, CourseSkill, Goal, Minor, Module, Prerequisite,
                     Programme, Question, Resource, Rule, Skill)


def _row(o):
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


@dataclass
class KB:
    skills: dict
    courses: dict
    prereqs: dict  # course -> [prereq codes]
    course_skills: dict  # course -> {skill: level}
    skill_courses: dict  # skill -> {course: level}
    modules: dict
    modules_by_skill: dict
    resources: dict
    resources_by_skill: dict
    questions: dict
    questions_by_skill: dict
    goals: dict
    minors: dict
    rules: dict
    programmes: dict
    fingerprint: str = ""
    skill_prereqs: dict = field(default_factory=dict)

    # -- helpers ---------------------------------------------------------
    def rule(self, key, default=None):
        return self.rules.get(key, default)

    def grade_points(self, grade: str) -> float:
        return float(self.rule("grade_points", {}).get(grade, 0))

    def offered_in(self, code: str, semester: int) -> bool:
        off = self.courses[code]["offered"]
        return off == "both" or off == ("odd" if semester % 2 else "even")

    def goal_requirements(self, goal_id: str, programme: str) -> list[dict]:
        """Expand '@programme_core' into the programme's discipline skills."""
        g = self.goals.get(goal_id)
        if not g:
            return []
        out, seen = [], set()
        for r in g["required_skills"]:
            if r["skill"] == "@programme_core":
                for s in self.programmes.get(programme, {}).get("core_skills", []):
                    if s not in seen:
                        out.append({"skill": s, "target": r["target"], "importance": r["importance"]})
                        seen.add(s)
            elif r["skill"] not in seen and r["skill"] in self.skills:
                out.append(dict(r))
                seen.add(r["skill"])
        return out


def load_kb(db: Session) -> KB:
    skills = {s.id: _row(s) for s in db.scalars(select(Skill))}
    courses = {c.code: _row(c) for c in db.scalars(select(Course))}
    prereqs = defaultdict(list)
    for p in db.scalars(select(Prerequisite)):
        prereqs[p.course_code].append(p.prereq_code)
    course_skills, skill_courses = defaultdict(dict), defaultdict(dict)
    for cs in db.scalars(select(CourseSkill)):
        course_skills[cs.course_code][cs.skill_id] = cs.level
        skill_courses[cs.skill_id][cs.course_code] = cs.level
    modules = {m.id: _row(m) for m in db.scalars(select(Module))}
    mbs = defaultdict(list)
    for m in sorted(modules.values(), key=lambda m: (m["skill_id"], m["seq"])):
        mbs[m["skill_id"]].append(m)
    resources = {r.id: _row(r) for r in db.scalars(select(Resource))}
    rbs = defaultdict(list)
    for r in resources.values():
        for s in r["skill_ids"].split(","):
            rbs[s.strip()].append(r)
    questions = {q.id: _row(q) for q in db.scalars(select(Question))}
    qbs = defaultdict(list)
    for q in questions.values():
        qbs[q["skill_id"]].append(q)
    goals = {g.id: _row(g) for g in db.scalars(select(Goal))}
    minors = {m.id: _row(m) for m in db.scalars(select(Minor))}
    rules = {r.key: r.value for r in db.scalars(select(Rule))}
    programmes = {p.id: _row(p) for p in db.scalars(select(Programme))}
    skill_prereqs = {s: [p for p in v["prereq_skills"].split(",") if p] for s, v in skills.items()}

    blob = json.dumps([skills, courses, prereqs, course_skills, modules, resources, questions, goals, minors, rules, programmes],
                      sort_keys=True, default=str)
    fp = hashlib.sha256(blob.encode()).hexdigest()[:16]
    return KB(skills, courses, dict(prereqs), dict(course_skills), dict(skill_courses), modules, dict(mbs), resources,
              dict(rbs), questions, dict(qbs), goals, minors, rules, programmes, fp, skill_prereqs)
