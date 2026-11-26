"""Load seed data (plain CSV/JSON in SEED_DIR) into the database.

    python -m app.seed            # load only if the database is empty
    python -m app.seed --reset    # drop everything and restore the original seed state

Inside docker:  docker compose exec backend python -m app.seed --reset
"""
import argparse
import csv
import json
import logging

from sqlalchemy import func, select

from . import config
from .db import engine, session_scope
from .models import (Base, Course, CourseSkill, Evidence, Goal, Minor, Module,
                     Prerequisite, Programme, Question, Resource, Rule, Skill,
                     Student)

log = logging.getLogger("seed")


def _csv(name):
    with open(config.SEED_DIR / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _json(name):
    with open(config.SEED_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _bool(v):
    return str(v).strip().lower() in ("1", "true", "yes")


def load_kb(db):
    for r in _csv("skills.csv"):
        db.add(Skill(**r))
    for r in _csv("courses.csv"):
        r["credits"] = int(r["credits"])
        r["semester"] = int(r["semester"] or 0)
        r["weekly_hours"] = int(r["weekly_hours"] or 0)
        db.add(Course(**r))
    db.flush()
    for r in _csv("prerequisites.csv"):
        db.add(Prerequisite(**r))
    for r in _csv("course_skills.csv"):
        db.add(CourseSkill(course_code=r["course_code"], skill_id=r["skill_id"], level=float(r["level"])))
    for r in _csv("resources.csv"):
        r["level"] = int(r["level"])
        r["est_hours"] = float(r["est_hours"])
        r["credit_eligible"] = _bool(r["credit_eligible"])
        db.add(Resource(**r))
    for r in _csv("modules.csv"):
        r["seq"] = int(r["seq"])
        r["level"] = int(r["level"])
        r["est_hours"] = float(r["est_hours"])
        db.add(Module(**r))
    for q in _json("questions.json"):
        db.add(Question(**q))
    for g in _json("goals.json"):
        db.add(Goal(**g))
    for p in _json("programmes.json"):
        db.add(Programme(**p))
    for m in _json("minors.json"):
        db.add(Minor(**m))
    for r in _json("rules.json"):
        db.add(Rule(**r))


def load_students(db):
    path = config.SEED_DIR / "students.json"
    if not path.exists():
        return
    for s in _json("students.json"):
        evidence = s.pop("evidence", [])
        db.add(Student(**s))
        db.flush()
        for e in evidence:
            db.add(Evidence(student_id=s["id"], **e))


def is_empty() -> bool:
    with session_scope() as db:
        return db.scalar(select(func.count()).select_from(Skill)) == 0


def init_db(reset: bool = False):
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    if reset or is_empty():
        with session_scope() as db:
            load_kb(db)
            db.flush()
            load_students(db)
        log.info("Seed data loaded from %s", config.SEED_DIR)
        return True
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop all data and reload the original seed")
    args = ap.parse_args()
    loaded = init_db(reset=args.reset)
    print("Database reset to seed state." if args.reset else ("Seed loaded." if loaded else "Database already populated."))
