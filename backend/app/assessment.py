"""Assessments: adaptive diagnostic, checkpoint quizzes, timed mocks and practice.

* Diagnostic (short, adaptive): only the goal skills that lack recent tested
  evidence, at most 6 skills x 2 questions. Each skill starts at medium
  difficulty; a correct answer moves up to hard, a wrong one down to easy.
  Two answers map to a score: (right, right)=0.9, (right, wrong)=0.6,
  (wrong, right)=0.4, (wrong, wrong)=0.15.
* Checkpoint quiz: 3 questions (easy, medium, hard) on one skill; score is the
  difficulty-weighted share correct (weights 1, 1.5, 2).
* Timed mock: 2 questions on each of the top goal skills with a time limit;
  produces `mock` evidence (used for goal-level mastery criteria).
* Practice: one question at a time at a difficulty matched to the current
  mastery estimate; each answer is `exercise` evidence carrying attempts and time.

Grading is deterministic (MCQ answer keys), so results are reproducible.
"""
import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb import KB
from .models import DiagnosticSession, Evidence

PAIR_SCORE = {(True, True): 0.9, (True, False): 0.6, (False, True): 0.4, (False, False): 0.15}
D_WEIGHT = {1: 1.0, 2: 1.5, 3: 2.0}


def seen_questions(db: Session, sid: str) -> set:
    seen = set()
    for e in db.scalars(select(Evidence).where(Evidence.student_id == sid)):
        for tok in (e.detail or "").split():
            if tok.startswith("q=") and tok[2:]:
                seen.update(tok[2:].split(","))
    for s in db.scalars(select(DiagnosticSession).where(DiagnosticSession.student_id == sid)):
        for v in s.state.get("per_skill", {}).values():
            seen.update(v.get("asked", []))
    return seen


def pick_question(kb: KB, skill: str, difficulty: int, exclude: set, rng: random.Random) -> dict | None:
    pool = kb.questions_by_skill.get(skill, [])
    for d in (difficulty, *sorted({1, 2, 3} - {difficulty}, key=lambda x: abs(x - difficulty))):
        cands = [q for q in pool if q["difficulty"] == d and q["id"] not in exclude]
        if cands:
            return rng.choice(sorted(cands, key=lambda q: q["id"]))
    cands = [q for q in pool if q["id"] not in exclude] or pool  # recycle if the bank is exhausted
    return rng.choice(sorted(cands, key=lambda q: q["id"])) if cands else None


def public_question(q: dict) -> dict:
    return {"id": q["id"], "skill": q["skill_id"], "difficulty": q["difficulty"], "prompt": q["prompt"], "options": q["options"]}


def start_session(db: Session, kb: KB, student: dict, states: dict, mode: str = "diagnostic", skill: str | None = None) -> dict:
    goal_reqs = kb.goal_requirements(student.get("goal_id") or "", student["programme"])
    if mode == "checkpoint":
        skills, per, limit = [skill], 3, None
    elif mode == "mock":
        skills = [r["skill"] for r in sorted(goal_reqs, key=lambda r: -r["importance"])][:4]
        per, limit = 2, 12
    else:
        reqs = sorted(goal_reqs, key=lambda r: (-r["importance"], states[r["skill"]]["confidence"]))
        skills = [r["skill"] for r in reqs if not (states[r["skill"]]["tested"] and states[r["skill"]]["confidence"] > 0.8)][:6]
        if not skills:  # no goal yet or all well-evidenced: broad screening
            skills = ["prog_fund", "prob_stats", "aptitude", "tech_writing", "economics"]
        per, limit = 2, None
    skills = [s for s in skills if s in kb.skills and kb.questions_by_skill.get(s)]
    sess = DiagnosticSession(id=uuid.uuid4().hex[:12], student_id=student["id"],
                             state={"mode": mode, "skills": skills, "idx": 0, "per_skill_n": per, "time_limit_min": limit,
                                    "per_skill": {s: {"asked": [], "results": []} for s in skills}, "current": None})
    db.add(sess)
    db.flush()
    q = _next_question(db, kb, sess)
    db.commit()
    return {"session_id": sess.id, "mode": mode, "skills": [{"id": s, "name": kb.skills[s]["name"]} for s in skills],
            "total_questions": len(skills) * per, "time_limit_min": limit, "question": q}


def _next_question(db: Session, kb: KB, sess: DiagnosticSession) -> dict | None:
    st = dict(sess.state)
    rng = random.Random(f"{sess.id}-{st['idx']}-{sum(len(v['asked']) for v in st['per_skill'].values())}")
    while st["idx"] < len(st["skills"]):
        s = st["skills"][st["idx"]]
        ps = st["per_skill"][s]
        if len(ps["results"]) >= st["per_skill_n"]:
            st["idx"] += 1
            continue
        if st["mode"] == "checkpoint":
            d = [1, 2, 3][len(ps["results"])]
        elif not ps["results"]:
            d = 2
        else:
            d = min(3, ps["results"][-1][0] + 1) if ps["results"][-1][1] else max(1, ps["results"][-1][0] - 1)
        q = pick_question(kb, s, d, seen_questions(db, sess.student_id) | set(ps["asked"]), rng)
        if not q:
            st["idx"] += 1
            continue
        ps["asked"].append(q["id"])
        st["current"] = q["id"]
        sess.state = st
        return public_question(q)
    st["current"] = None
    sess.state = st
    return None


def _skill_score(mode: str, results: list) -> float:
    if mode in ("diagnostic", "mock") and len(results) == 2:
        return PAIR_SCORE[(results[0][1], results[1][1])]
    tot = sum(D_WEIGHT[d] for d, _ in results) or 1
    return max(0.05, min(0.95, sum(D_WEIGHT[d] for d, c in results if c) / tot))


def answer(db: Session, kb: KB, session_id: str, qid: str, choice: str, seconds: float = 0) -> dict:
    sess = db.get(DiagnosticSession, session_id)
    if not sess or sess.finished:
        raise ValueError("session not found or already finished")
    st = dict(sess.state)
    if st.get("current") != qid:
        raise ValueError("unexpected question id")
    q = kb.questions[qid]
    correct = choice.strip() == q["answer"].strip()
    s = q["skill_id"]
    ps = st["per_skill"][s]
    ps["results"].append([q["difficulty"], correct])
    ps.setdefault("seconds", []).append(seconds)
    sess.state = st
    recorded = None
    if len(ps["results"]) >= st["per_skill_n"]:
        score = _skill_score(st["mode"], ps["results"])
        src = {"diagnostic": "assessment", "checkpoint": "assessment", "mock": "mock"}[st["mode"]]
        marks = " ".join(f"{'easy' if d == 1 else 'medium' if d == 2 else 'hard'}:{'right' if c else 'wrong'}" for d, c in ps["results"])
        label = {"diagnostic": "Adaptive diagnostic", "checkpoint": "Checkpoint quiz", "mock": "Timed mock"}[st["mode"]]
        db.add(Evidence(student_id=sess.student_id, skill_id=s, source=src, score=round(score, 2),
                        detail=f"{label}: {kb.skills[s]['name']} ({marks}) q={','.join(ps['asked'])}",
                        attempts=1, time_spent_min=round(sum(ps["seconds"]) / 60, 1)))
        recorded = {"skill": s, "score": round(score, 2), "source": src}
    nxt = _next_question(db, kb, sess)
    if nxt is None:
        sess.finished = True
    db.commit()
    return {"correct": correct, "correct_answer": q["answer"], "explanation": q["explanation"], "recorded": recorded,
            "next_question": nxt, "finished": sess.finished,
            "results": {k: v["results"] for k, v in st["per_skill"].items()} if sess.finished else None}


# ---------------------------------------------------------------- practice
def next_practice(db: Session, kb: KB, sid: str, skill: str, mastery: float) -> dict | None:
    d = 1 if mastery < 0.4 else 2 if mastery < 0.7 else 3
    rng = random.Random(f"{sid}-{skill}-{len(seen_questions(db, sid))}")
    q = pick_question(kb, skill, d, seen_questions(db, sid), rng)
    return public_question(q) if q else None


def answer_practice(db: Session, kb: KB, sid: str, qid: str, choice: str, attempts: int = 1, seconds: float = 0) -> dict:
    q = kb.questions[qid]
    correct = choice.strip() == q["answer"].strip()
    db.add(Evidence(student_id=sid, skill_id=q["skill_id"], source="exercise", score=1.0 if correct else 0.0,
                    detail=f"Practice {qid} ({'right' if correct else 'wrong'}) q={qid}", attempts=max(1, attempts),
                    time_spent_min=round(seconds / 60, 2)))
    db.commit()
    return {"correct": correct, "correct_answer": q["answer"], "explanation": q["explanation"]}
