"""Independent plan validator.

Re-checks a finished plan against the knowledge base and the student's
constraints without trusting the planner. Every plan shown to a student carries
this checklist, so any plan (including one edited by a student override or an
admin) is verifiable.
"""
from .diagnose import backlogs, completed_codes
from .kb import KB


def validate(kb: KB, student: dict, plan: dict, states: dict) -> dict:
    checks = []

    def check(cid, name, failures, warn=False):
        checks.append({"id": cid, "name": name, "passed": not failures, "severity": "warning" if warn else "error",
                       "details": failures[:10]})

    cons = student.get("constraints", {})
    done = completed_codes(kb, student)
    sems = plan["semesters"]
    by_sem = {s["semester"]: [c for c in s["courses"] if c["code"]] for s in sems}

    check("exists", "Every recommended course exists in the knowledge base (cited by code)",
          [f"{c['code']} not in catalogue" for cs in by_sem.values() for c in cs if c["code"] not in kb.courses])
    valid = {sem: [c for c in cs if c["code"] in kb.courses] for sem, cs in by_sem.items()}

    check("offering", "Each course is offered in the semester it is planned",
          [f"{c['code']} not offered in semester {sem}" for sem, cs in valid.items() for c in cs if not kb.offered_in(c["code"], sem)])

    fails, seen = [], set(done)
    for sem in sorted(valid):
        for c in valid[sem]:
            miss = [p for p in kb.prereqs.get(c["code"], []) if p not in seen]
            if miss and c["slot"] not in ("core", "backlog"):
                fails.append(f"semester {sem}: {c['code']} missing prerequisite {', '.join(miss)}")
        seen |= {c["code"] for c in valid[sem]}
    check("prereq", "All prerequisites are completed or planned in an earlier semester", fails)

    fails = []
    for s in sems:
        if s["total_credits"] > s["credit_limit"]:
            fails.append(f"semester {s['semester']}: {s['total_credits']} credits > limit {s['credit_limit']}")
    check("credits_max", "Credits per semester within the institute limit and the student's cap", fails)
    mn = kb.rule("min_credits_per_semester", 12)
    check("credits_min", f"At least {mn} credits per semester (warning only for final semesters)",
          [f"semester {s['semester']}: {s['total_credits']} credits" for s in sems[:-1] if s["total_credits"] < mn], warn=True)

    planned = [c["code"] for cs in valid.values() for c in cs]
    check("no_repeat", "No completed course is repeated and nothing is planned twice",
          [f"{c} already completed" for c in planned if c in done] +
          [f"{c} planned more than once" for c in set(planned) if planned.count(c) > 1])

    bl = backlogs(kb, student)
    fails = []
    for code in bl:
        first = next((s for s in sorted(valid) if kb.offered_in(code, s)), None)
        if first is None or code not in {c["code"] for c in valid.get(first, [])}:
            fails.append(f"backlog {code} not scheduled at its next offering (semester {first})")
    check("backlogs", "Backlogs re-registered at the next offering", fails)

    fails = []
    for a, b in cons.get("not_together", []):
        for sem, cs in valid.items():
            codes = {c["code"] for c in cs}
            if a in codes and b in codes:
                fails.append(f"{a} and {b} together in semester {sem}")
    check("not_together", "Student's 'not in the same semester' preferences respected", fails)

    check("excluded", "Courses the student rejected are not recommended",
          [f"{c} was rejected by the student" for c in planned if c in cons.get("excluded_courses", [])])

    if cons.get("open_elective_slots") is not None:
        n_open = sum(1 for s in sems for c in s["courses"] if c["slot"] == "open_elective")
        check("open_slots", "Open-elective slots used <= slots remaining",
              [f"{n_open} open-elective slots used, only {cons['open_elective_slots']} remain"] if n_open > cons["open_elective_slots"] else [])

    oc = kb.rule("online_credit", {"max_courses": 2, "max_credits": 6})
    online = [c for c in list(done) + planned if kb.courses[c]["course_type"] == "online"]
    check("online", "Online (NPTEL/SWAYAM) credit within institute limits",
          [f"{len(online)} online courses ({sum(kb.courses[c]['credits'] for c in online)} cr) exceed "
           f"{oc['max_courses']} courses / {oc['max_credits']} cr"]
          if len(online) > oc["max_courses"] or sum(kb.courses[c]["credits"] for c in online) > oc["max_credits"] else [])

    minor = plan.get("minor")
    fails = []
    if minor and not minor.get("eligible"):
        fails = [f"{c['code']} planned as a minor course but student is not eligible ({minor['reason']})"
                 for s in sems for c in s["courses"] if c["slot"] == "minor"]
    check("minor", "Minor courses only when the CGPA/programme eligibility rule is met", fails)

    # no already-mastered content
    fails = []
    th = kb.rule("mastery_thresholds", {"min_confidence": 0.55})
    for sem, cs in valid.items():
        for c in cs:
            if c["slot"] in ("core", "backlog"):
                continue
            sk = kb.course_skills.get(c["code"], {})
            if sk and all(states[s]["mastery"] >= lvl and states[s]["tested"] and states[s]["confidence"] >= th["min_confidence"]
                          for s, lvl in sk.items()):
                fails.append(f"{c['code']} only teaches skills already demonstrated")
    track = plan.get("learning_track") or {}
    for w in track.get("weeks", []):
        for it in w["items"]:
            s = it.get("skill")
            if it["type"] == "lesson" and s and states[s]["tested"] and states[s]["mastery"] >= 0.65 and \
                    kb.modules.get(it.get("module"), {}).get("level", 3) < 3:
                fails.append(f"week {w['week']}: introductory lesson '{it['title']}' for an already-strong skill")
    check("no_mastered", "No content the student has already mastered", fails)

    check("weekly_time", "Weekly self-study fits the student's available hours (exam weeks halved)",
          [f"week {w['week']}: {w['hours']}h > {w['capacity']}h" for w in track.get("weeks", []) if w["hours"] > w["capacity"] + 1e-6])

    goal = kb.goals.get(student.get("goal_id") or "")
    if goal:
        reqs = kb.goal_requirements(goal["id"], student["programme"])
        covered = {s for cs in valid.values() for c in cs for s in kb.course_skills.get(c["code"], {})}
        covered |= {it.get("skill") for w in track.get("weeks", []) for it in w["items"]}
        covered |= {it.get("skill") for it in track.get("deferred", [])}
        fails = [f"{r['skill']} gap has no course, module or deferred item" for r in reqs
                 if states[r["skill"]]["mastery"] < r["target"] and r["skill"] not in covered]
        check("goal_coverage", "Every goal-skill gap is addressed by a course, module or checkpoint", fails)

    errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
    return {"passed": not errors, "n_checks": len(checks), "n_failed": len(errors), "checks": checks}
