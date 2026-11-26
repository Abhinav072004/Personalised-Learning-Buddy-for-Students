"""Student model: estimate per-skill mastery from evidence, weighted by reliability.

Evidence sources and default reliability (rule `evidence_reliability`):
    assessment 1.0 | mock 1.0 | project 0.9 | exercise 0.8 | grade 0.6 | self 0.2

* Course grades are converted into evidence for every skill the course teaches:
  score = course_level * grade_points / 10 (a course can only take a skill as far
  as its own level). A grade alone never "demonstrates" a skill.
* Each evidence item's weight = reliability * recency decay (newest = 1, then
  0.85, 0.72 ...) * attempt penalty for exercises answered after several tries.
* Estimate = weighted mean with a weak novice prior (0.2, weight 0.3);
  confidence = 1 - exp(-sum(weights)).
* Status against a target:
    demonstrated  - estimate >= target, confidence >= min_confidence and at least
                    one *tested* evidence item (assessment / exercise / project / mock)
    completed_not_demonstrated - estimate >= target from grades/self-report only
    in_progress   - estimate >= 60% of target
    gap           - otherwise
  plus a `struggling` flag when recent tested evidence is repeatedly low.

This is what separates "the student completed the course" from "the student
demonstrated the required level of proficiency".
"""
import math
from collections import defaultdict

from .kb import KB

TESTED = {"assessment", "exercise", "project", "mock"}
PRIOR, PRIOR_W, DECAY = 0.2, 0.3, 0.85


def passed(kb: KB, grade: str) -> bool:
    return grade != "F" and kb.grade_points(grade) >= kb.grade_points(kb.rule("pass_grade", "D"))


def grade_evidence(kb: KB, student: dict) -> list[dict]:
    out = []
    for cc in student["completed_courses"]:
        gp = kb.grade_points(cc["grade"])
        for skill, level in kb.course_skills.get(cc["code"], {}).items():
            out.append({"skill_id": skill, "source": "grade", "score": round(level * gp / 10, 3),
                        "detail": f"{cc['code']} grade {cc['grade']}", "attempts": 1, "time_spent_min": 0,
                        "order": cc.get("semester", 0) * 1e-6})
    return out


def all_evidence(kb: KB, student: dict, evidence_rows: list[dict]) -> dict[str, list[dict]]:
    """Grades + stored evidence, grouped by skill, oldest first."""
    by = defaultdict(list)
    for e in grade_evidence(kb, student):
        by[e["skill_id"]].append(e)
    for i, e in enumerate(evidence_rows):
        e = dict(e)
        e.setdefault("order", 1 + i)
        by[e["skill_id"]].append(e)
    for s in by:
        by[s].sort(key=lambda e: e["order"])
    return by


def estimate(kb: KB, items: list[dict]) -> dict:
    rel = kb.rule("evidence_reliability", {})
    num, den, tested, low_recent = PRIOR * PRIOR_W, PRIOR_W, False, 0
    sources = defaultdict(int)
    # newest first for recency decay
    for rank, e in enumerate(reversed(items)):
        w = float(rel.get(e["source"], 0.3)) * (DECAY ** rank)
        score = float(e["score"])
        if e["source"] == "exercise" and e.get("attempts", 1) > 1:
            score *= max(0.5, 1 - 0.15 * (e["attempts"] - 1))
        num += w * score
        den += w
        sources[e["source"]] += 1
        if e["source"] in TESTED:
            tested = True
            if rank < 4 and score < 0.5:
                low_recent += 1
    w_sum = den - PRIOR_W
    return {"mastery": round(num / den, 3), "confidence": round(1 - math.exp(-w_sum), 3), "tested": tested,
            "struggling": low_recent >= 2, "n_evidence": len(items), "sources": dict(sources)}


def status_for(kb: KB, est: dict, target: float) -> str:
    th = kb.rule("mastery_thresholds", {"min_confidence": 0.55, "require_tested_evidence": True})
    if est["mastery"] >= target:
        if est["tested"] and est["confidence"] >= th["min_confidence"]:
            return "demonstrated"
        return "completed_not_demonstrated"
    if est["mastery"] >= 0.6 * target:
        return "in_progress"
    return "gap"


def skill_states(kb: KB, student: dict, evidence_rows: list[dict]) -> dict[str, dict]:
    by = all_evidence(kb, student, evidence_rows)
    states = {}
    for s in kb.skills:
        est = estimate(kb, by.get(s, []))
        est["evidence"] = [{k: e[k] for k in ("source", "score", "detail")} for e in by.get(s, [])][-6:]
        states[s] = est
    return states
