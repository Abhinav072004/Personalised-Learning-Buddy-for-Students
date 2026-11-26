"""Diagnosis: where the student stands against their goal (deterministic).

Produces strengths, weaknesses, per-skill gaps (with evidence and its
reliability), goal readiness, interest-vs-evidence mismatches, alternative
goals ranked by fit, and the academic constraints that bound the plan.
"""
import re

from .kb import KB
from .mastery import TESTED, passed, status_for

SKILL_ALIASES = {
    "ml": ["machine learning", "ml", "ai", "deep learning"], "data_analysis": ["data", "analytics", "data science", "pandas"],
    "web_dev": ["web", "frontend", "backend", "full stack"], "dsa": ["dsa", "algorithms", "competitive programming", "coding"],
    "prog_fund": ["coding", "programming", "python"], "polity_governance": ["polity", "constitution"],
    "economics": ["economy", "economics"], "entrepreneurship": ["startups", "startup", "entrepreneurship"],
    "product_mgmt": ["product"], "research_methods": ["research"], "process_control": ["control systems", "control"],
    "history_society": ["history"], "databases": ["sql", "databases"], "numerical_methods": ["simulation"],
}


def match_goal(kb: KB, text: str) -> list[tuple[str, int]]:
    """Keyword match of free-text ambition to KB goals -> [(goal_id, hits)] best first."""
    t = f" {text.lower()} "
    scores = []
    for gid, g in kb.goals.items():
        hits = sum(1 for k in g["keywords"] if re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", t))
        if hits:
            scores.append((gid, hits))
    return sorted(scores, key=lambda x: -x[1])


def readiness(kb: KB, reqs: list[dict], states: dict) -> float:
    tot = sum(r["importance"] for r in reqs) or 1
    return round(sum(r["importance"] * min(1.0, states[r["skill"]]["mastery"] / r["target"]) for r in reqs) / tot, 3)


def completed_codes(kb: KB, student: dict) -> set[str]:
    return {c["code"] for c in student["completed_courses"] if passed(kb, c["grade"])}


def backlogs(kb: KB, student: dict) -> list[str]:
    done = completed_codes(kb, student)
    return sorted({c["code"] for c in student["completed_courses"] if not passed(kb, c["grade"]) and c["code"] not in done})


def minor_status(kb: KB, student: dict, goal: dict | None) -> dict | None:
    if not goal or not goal.get("recommended_minor"):
        return None
    m = kb.minors.get(goal["recommended_minor"])
    if not m:
        return None
    done = completed_codes(kb, student)
    earned = sum(kb.courses[c]["credits"] for c in m["courses"] if c in done)
    res = {"id": m["id"], "name": m["name"], "min_cgpa": m["min_cgpa"], "credits_required": m["credits_required"],
           "credits_earned": earned, "cgpa": student["cgpa"]}
    if student["programme"] in m["excluded_programmes"]:
        res.update(eligible=False, reason=f"{m['name']} is not open to {student['programme']} students")
    elif student["cgpa"] >= m["min_cgpa"]:
        res.update(eligible=True, reason=f"CGPA {student['cgpa']} meets the {m['min_cgpa']} cut-off")
    else:
        credits_done = sum(kb.courses[c["code"]]["credits"] for c in student["completed_courses"] if c["code"] in kb.courses)
        next_load = 20
        need = (m["min_cgpa"] * (credits_done + next_load) - student["cgpa"] * credits_done) / next_load
        res.update(eligible=False, near_cutoff=student["cgpa"] >= m["min_cgpa"] - 0.3,
                   sgpa_needed=round(need, 2),
                   reason=(f"CGPA {student['cgpa']} is below the {m['min_cgpa']} cut-off. An SGPA of about "
                           f"{need:.2f} over ~{next_load} credits next semester would make you eligible"
                           if need <= 10 else f"CGPA {student['cgpa']} is below the {m['min_cgpa']} cut-off and cannot reach it next semester")
                   + "; until then the plan takes the same courses as open electives so nothing is lost.")
    return res


def diagnose(kb: KB, student: dict, states: dict) -> dict:
    goal = kb.goals.get(student.get("goal_id") or "")
    reqs = kb.goal_requirements(goal["id"], student["programme"]) if goal else []
    gaps = []
    for r in reqs:
        st = states[r["skill"]]
        status = status_for(kb, st, r["target"])
        gaps.append({
            "skill": r["skill"], "name": kb.skills[r["skill"]]["name"], "target": r["target"], "importance": r["importance"],
            "mastery": st["mastery"], "confidence": st["confidence"], "gap": round(max(0.0, r["target"] - st["mastery"]), 3),
            "status": status, "struggling": st["struggling"], "tested": st["tested"], "evidence": st["evidence"],
        })
    gaps.sort(key=lambda g: (-g["importance"] * g["gap"], g["skill"]))

    # strengths / weaknesses across all skills with evidence
    with_ev = {s: v for s, v in states.items() if v["n_evidence"]}
    strengths = sorted([s for s, v in with_ev.items() if v["mastery"] >= 0.65], key=lambda s: -with_ev[s]["mastery"])[:6]
    weaknesses = sorted([s for s, v in with_ev.items() if v["mastery"] < 0.4 and v["tested"]], key=lambda s: with_ev[s]["mastery"])[:6]

    # interest/goal vs evidence mismatches
    mismatches = []
    for g in gaps:
        strong_low = [e for e in g["evidence"] if e["source"] in TESTED | {"grade"} and e["score"] < 0.45]
        if g["importance"] >= 2 and strong_low and g["status"] in ("gap", "in_progress"):
            mismatches.append({"skill": g["skill"], "kind": "goal_vs_evidence",
                               "message": f"Your goal needs {g['name']} (target {int(g['target']*100)}%), but "
                                          f"{strong_low[-1]['detail'] or strong_low[-1]['source']} shows {int(strong_low[-1]['score']*100)}%. "
                                          "The plan adds work to close this gap; check whether the goal still fits after the next checkpoint."})
    interest_text = " ".join(student.get("interests", [])).lower()
    for skill, aliases in SKILL_ALIASES.items():
        if any(a in interest_text for a in aliases):
            st = states[skill]
            tested_scores = [e["score"] for e in st["evidence"] if e["source"] in TESTED]
            if tested_scores and max(tested_scores) < 0.45:
                mismatches.append({"skill": skill, "kind": "interest_vs_evidence",
                                   "message": f"You listed an interest in {kb.skills[skill]['name']}, but tested evidence so far is "
                                              f"{int(max(tested_scores)*100)}%. Interest is a good start; it needs backing with practice."})
    seen = set()
    mismatches = [m for m in mismatches if not (m["skill"] in seen or seen.add(m["skill"]))]

    # alternative goals by current fit (helps when interest and evidence diverge)
    fits = []
    for gid in kb.goals:
        rq = kb.goal_requirements(gid, student["programme"])
        fits.append({"goal": gid, "name": kb.goals[gid]["name"], "readiness": readiness(kb, rq, states)})
    fits.sort(key=lambda x: -x["readiness"])

    remaining = list(range(student["current_semester"], int(kb.rule("total_semesters", 8)) + 1))
    cons = student.get("constraints", {})
    overload = kb.rule("overload", {})
    credit_limit = overload.get("max_credits", 28) if student["cgpa"] >= overload.get("min_cgpa", 99) else kb.rule("max_credits_per_semester", 24)
    if cons.get("max_credits"):
        credit_limit = min(credit_limit, cons["max_credits"])

    goal_matches = match_goal(kb, student.get("goal_text", "")) if not goal else []
    return {
        "goal": {"id": goal["id"], "name": goal["name"]} if goal else None,
        "goal_text": student.get("goal_text", ""),
        "goal_is_vague": goal is None,
        "goal_candidates": [{"goal": g, "name": kb.goals[g]["name"]} for g, _ in goal_matches[:3]],
        "readiness": readiness(kb, reqs, states) if reqs else None,
        "gaps": gaps,
        "strengths": [{"skill": s, "name": kb.skills[s]["name"], "mastery": states[s]["mastery"]} for s in strengths],
        "weaknesses": [{"skill": s, "name": kb.skills[s]["name"], "mastery": states[s]["mastery"]} for s in weaknesses],
        "mismatches": mismatches,
        "goal_fit": fits[:4],
        "constraints": {
            "remaining_semesters": remaining, "credit_limit": credit_limit, "hours_per_week": cons.get("hours_per_week", 6),
            "open_elective_slots": cons.get("open_elective_slots"), "extra_credit_headroom": cons.get("extra_credit_headroom", 0),
            "not_together": cons.get("not_together", []), "excluded_courses": cons.get("excluded_courses", []),
            "backlogs": backlogs(kb, student),
        },
        "minor": minor_status(kb, student, goal),
        "mastery_criteria": goal["mastery_criteria"] if goal else [],
    }
