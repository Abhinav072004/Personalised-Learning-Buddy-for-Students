"""Deterministic multi-semester planner.

Plan = (1) courses for every remaining semester, (2) a week-by-week self-paced
learning track for the next semester (modules, open resources, practice,
checkpoints), (3) milestones beyond coursework (projects, internships, exams).

Course selection is a greedy, constraint-first search per semester:
  backlogs and missed cores are placed first (institute rule), then programme
  cores, then elective slots and optional extra credits are filled with the
  eligible course that closes the most *importance-weighted* goal-skill gap,
  plus a bonus for unlocking valuable later courses and for minor progress.
Hard constraints are enforced while choosing (offering parity, prerequisites,
credit limits, not-together pairs, rejected courses, online-credit caps, slot
counts), and the finished plan is re-checked independently by `validator.py`.
Nothing here calls the LLM.
"""
from collections import defaultdict

from .diagnose import backlogs, completed_codes
from .kb import KB

EXPECTED_ATTAINMENT = 0.85  # a planned course is assumed to bring its skills to 85% of the course level
OPEN_TYPES = {"open_elective", "minor", "online"}


def _season(sem: int) -> str:
    return "Jul-Nov (odd)" if sem % 2 else "Jan-Apr (even)"


def course_skill_gain(kb: KB, code: str, need: dict, projected: dict) -> tuple[float, list]:
    gain, parts = 0.0, []
    for s, lvl in kb.course_skills.get(code, {}).items():
        if s in need:
            tgt, imp = need[s]
            g = max(0.0, min(lvl * EXPECTED_ATTAINMENT, tgt) - projected[s])
            if g > 0.01:
                gain += imp * g
                parts.append((s, g, imp))
    return gain, parts


def course_blockers(kb: KB, student: dict, code: str, sem: int, taken_before: set, chosen: list, credits_left: int,
                    online_used: tuple[int, int]) -> list[str]:
    """Why `code` cannot be taken in `sem` given the plan so far ([] = feasible)."""
    if code not in kb.courses:
        return [f"{code} does not exist in the course catalogue"]
    c = kb.courses[code]
    why = []
    if code in taken_before or code in {x["code"] for x in chosen}:
        why.append(f"{code} is already completed or planned")
    if not kb.offered_in(code, sem):
        why.append(f"{code} is offered only in {c['offered']} semesters, not semester {sem}")
    missing = [p for p in kb.prereqs.get(code, []) if p not in taken_before]
    if missing:
        why.append(f"{code} needs {', '.join(missing)} completed first")
    if c["credits"] > credits_left:
        why.append(f"{code} ({c['credits']} cr) exceeds the {credits_left} credits left this semester")
    chosen_codes = {x["code"] for x in chosen}
    for a, b in student.get("constraints", {}).get("not_together", []):
        if (code == a and b in chosen_codes) or (code == b and a in chosen_codes):
            why.append(f"you asked not to take {a} and {b} in the same semester")
    if code in student.get("constraints", {}).get("excluded_courses", []):
        why.append(f"you rejected {code} earlier")
    if c["course_type"] == "online":
        oc = kb.rule("online_credit", {})
        if online_used[0] + 1 > oc.get("max_courses", 2) or online_used[1] + c["credits"] > oc.get("max_credits", 6):
            why.append(f"online-credit limit reached ({oc.get('max_courses', 2)} courses / {oc.get('max_credits', 6)} credits)")
    return why


def build_plan(kb: KB, student: dict, states: dict, diag: dict, done_modules: set | None = None,
               pace_factor: float = 1.0) -> dict:
    done_modules = done_modules or set()
    goal = kb.goals.get(student.get("goal_id") or "")
    reqs = kb.goal_requirements(goal["id"], student["programme"]) if goal else []
    need = {r["skill"]: (r["target"], r["importance"]) for r in reqs}
    projected = {s: v["mastery"] for s, v in states.items()}
    cons = student.get("constraints", {})
    prog = kb.programmes[student["programme"]]
    taken = completed_codes(kb, student)
    pending_backlogs = backlogs(kb, student)
    credit_limit = diag["constraints"]["credit_limit"]
    open_left = cons.get("open_elective_slots")  # None = programme default
    headroom = cons.get("extra_credit_headroom", 0) or 0
    online_done = [c for c in taken if kb.courses[c]["course_type"] == "online"]
    online_used = [len(online_done), sum(kb.courses[c]["credits"] for c in online_done)]
    minor = diag.get("minor")
    minor_courses = set(kb.minors[minor["id"]]["courses"]) if minor else set()
    pursue_minor = bool(minor and (minor.get("eligible") or minor.get("near_cutoff")))
    minor_credits = minor["credits_earned"] if minor else 0
    pinned = [p for p in cons.get("pinned_courses", []) if p not in taken]
    infeasible, semesters, notes_global = [], [], []

    th = kb.rule("mastery_thresholds", {"min_confidence": 0.55})

    def already_mastered(code):
        sk = kb.course_skills.get(code, {})
        return bool(sk) and all(states[x]["mastery"] >= lvl and states[x]["tested"]
                                and states[x]["confidence"] >= th["min_confidence"] for x, lvl in sk.items())

    def value(code, sem_courses_after):
        g, parts = course_skill_gain(kb, code, need, projected)
        # enabling value: unlocks a later course that closes gaps
        unlock = 0.0
        for d, pres in kb.prereqs.items():
            if code in pres and d not in taken:
                dg, _ = course_skill_gain(kb, d, need, projected)
                unlock = max(unlock, 0.35 * dg)
        bonus = 0.15 if (pursue_minor and code in minor_courses and minor_credits < minor["credits_required"]) else 0.0
        return g + unlock + bonus, parts, unlock

    def reason_for(code, parts, unlock, slot):
        bits = []
        for s, g, imp in sorted(parts, key=lambda p: -p[1] * p[2]):
            tgt = need[s][0]
            bits.append(f"raises {kb.skills[s]['name']} towards {int(tgt*100)}% (now {int(projected[s]*100)}%, "
                        f"{'high' if imp == 3 else 'medium' if imp == 2 else 'low'} priority for your goal)")
        if unlock > 0:
            later = [d for d, pres in kb.prereqs.items() if code in pres and d not in taken]
            bits.append("unlocks " + ", ".join(sorted(later)[:3]))
        if pursue_minor and code in minor_courses:
            bits.append(f"counts towards the {minor['name']}")
        if slot == "backlog":
            bits = ["backlog: institute rules require re-registering at the next offering, before new electives"]
        if slot == "core":
            bits = ["programme core course"] + bits
        return "; ".join(bits) if bits else "fills an elective slot"

    for sem in diag["constraints"]["remaining_semesters"]:
        chosen, notes = [], []
        taken_before = set(taken)
        limit = credit_limit

        def add(code, slot, why):
            c = kb.courses[code]
            chosen.append({"code": code, "title": c["title"], "credits": c["credits"], "type": c["course_type"],
                           "mode": c["mode"], "slot": slot, "reason": why,
                           "skills": sorted(kb.course_skills.get(code, {}), key=lambda s: -kb.course_skills[code][s])})

        def credits_left():
            return limit - sum(x["credits"] for x in chosen)

        # 1. backlogs and missed cores
        for code in list(pending_backlogs):
            if kb.offered_in(code, sem):
                add(code, "backlog", reason_for(code, [], 0, "backlog"))
                pending_backlogs.remove(code)
        for code, c in kb.courses.items():
            if (c["course_type"] == "core" and student["programme"] in c["programme"].split(",")
                    and 0 < c["semester"] <= sem and code not in taken and code not in {x["code"] for x in chosen}
                    and kb.offered_in(code, sem)):
                add(code, "core", reason_for(code, course_skill_gain(kb, code, need, projected)[1], 0, "core"))
        # 2. elective slots
        slots = dict(prog["elective_slots"].get(str(sem), {}))
        n_open = slots.get("open_elective", 0)
        if open_left is not None:
            n_open = min(n_open, open_left)
        n_dept = slots.get("dept_elective", 0)
        extra_budget = headroom if sem == student["current_semester"] else 0

        def candidates(kind):
            out = []
            for code, c in kb.courses.items():
                if kind == "dept" and not (c["course_type"] == "dept_elective" and student["programme"] in c["programme"].split(",")):
                    continue
                if kind in ("open", "extra") and c["course_type"] not in OPEN_TYPES:
                    continue
                cl = credits_left() if kind != "extra" else min(credits_left(), extra_budget_left[0])
                if course_blockers(kb, student, code, sem, taken_before, chosen, cl, tuple(online_used)):
                    continue
                if code not in pinned and already_mastered(code):
                    continue  # never assign content the student has already demonstrated
                v, parts, unlock = value(code, chosen)
                if code in pinned:
                    v += 100
                if v > 0.02:
                    out.append((v, code, parts, unlock))
            return sorted(out, key=lambda x: (-x[0], x[1]))

        extra_budget_left = [extra_budget]

        def place(kind, slot_name):
            cands = candidates(kind)
            if not cands:
                return False
            v, code, parts, unlock = cands[0]
            add(code, slot_name, ("you asked for this course; " if code in pinned else "") + reason_for(code, parts, unlock, slot_name))
            if code in pinned:
                pinned.remove(code)
            nonlocal_update(code, parts)
            return True

        def nonlocal_update(code, parts):
            nonlocal minor_credits
            for s, lvl in kb.course_skills.get(code, {}).items():
                projected[s] = max(projected[s], lvl * EXPECTED_ATTAINMENT)
            if kb.courses[code]["course_type"] == "online":
                online_used[0] += 1
                online_used[1] += kb.courses[code]["credits"]
            if code in minor_courses:
                minor_credits += kb.courses[code]["credits"]

        def combo_value(combo):
            """Value of taking several courses together: overlapping skills are counted once."""
            proj = dict(projected)
            total = 0.0
            for v, code, parts, unlock in sorted(combo, key=lambda c: -c[0]):
                g, _ = course_skill_gain(kb, code, need, proj)
                single, _ = course_skill_gain(kb, code, need, projected)
                total += g + (v - single)  # keep unlock / minor / pin bonuses
                for sk, lvl in kb.course_skills.get(code, {}).items():
                    proj[sk] = max(proj[sk], lvl * EXPECTED_ATTAINMENT)
            return total

        for _ in range(n_dept):
            if not place("dept", "dept_elective"):
                chosen.append({"code": None, "title": "Department elective of your choice", "credits": 3, "type": "dept_elective",
                               "slot": "dept_elective", "reason": "no remaining department elective adds to your goal; pick by interest",
                               "skills": [], "mode": "offline"})
        used_open = 0
        if n_open and extra_budget_left[0] > 0 and not pinned:
            # joint choice of open-slot courses and headroom courses (exact search over top candidates)
            from itertools import combinations
            cands = candidates("open")[:8]
            best, best_v = None, 0.0
            for k in range(1, min(len(cands), n_open + 3) + 1):
                for combo in combinations(cands, k):
                    codes = [c[1] for c in combo]
                    if any(a in codes and b in codes for a, b in cons.get("not_together", [])):
                        continue
                    n_on = sum(1 for c in codes if kb.courses[c]["course_type"] == "online")
                    if online_used[0] + n_on > kb.rule("online_credit", {}).get("max_courses", 2):
                        continue
                    srt = sorted(combo, key=lambda c: -kb.courses[c[1]]["credits"])
                    slot_part, extra_part = srt[:n_open], srt[n_open:]
                    ex_cr = sum(kb.courses[c[1]]["credits"] for c in extra_part)
                    tot_cr = sum(kb.courses[c]["credits"] for c in codes)
                    if ex_cr > extra_budget_left[0] or tot_cr > credits_left():
                        continue
                    v = combo_value(combo)
                    if v > best_v + 1e-9:
                        best, best_v = (slot_part, extra_part), v
            if best:
                for v, code, parts, unlock in best[0]:
                    add(code, "open_elective", reason_for(code, parts, unlock, "open_elective"))
                    used_open += 1
                for v, code, parts, unlock in best[1]:
                    add(code, "extra", reason_for(code, parts, unlock, "extra") + " (uses your extra-credit headroom)")
                    extra_budget_left[0] -= kb.courses[code]["credits"]
                for v, code, parts, unlock in best[0] + best[1]:
                    nonlocal_update(code, parts)
                extra_budget_left[0] = 0
        for _ in range(n_open - used_open):
            if place("open", "open_elective"):
                used_open += 1
        if open_left is not None:
            open_left -= used_open
        # free open slots that could not be filled usefully are left for the student's choice
        for _ in range(n_open - used_open):
            chosen.append({"code": None, "title": "Open elective of your choice", "credits": 3, "type": "open_elective",
                           "slot": "open_elective", "reason": "no remaining course adds to your goal; choose by interest or to protect CGPA",
                           "skills": [], "mode": "offline"})
            if open_left is not None:
                open_left -= 1
        # 3. extra credits: next-semester headroom, or one extra minor course per later semester
        if extra_budget_left[0] > 0:
            # small exact knapsack over the best candidates: maximise value within the credit headroom
            cands = candidates("extra")[:8]
            best, best_v = (), 0.0
            from itertools import combinations
            for k in range(1, min(3, len(cands)) + 1):
                for combo in combinations(cands, k):
                    cr = sum(kb.courses[c[1]]["credits"] for c in combo)
                    codes = {c[1] for c in combo}
                    if cr > extra_budget_left[0]:
                        continue
                    if any(a in codes and b in codes for a, b in cons.get("not_together", [])):
                        continue
                    n_on = sum(1 for c in codes if kb.courses[c]["course_type"] == "online")
                    if n_on and online_used[0] + n_on > kb.rule("online_credit", {}).get("max_courses", 2):
                        continue
                    v = combo_value(combo)
                    if v > best_v + 1e-9:
                        best, best_v = combo, v
            for v, code, parts, unlock in best:
                add(code, "extra", reason_for(code, parts, unlock, "extra") + " (uses your extra-credit headroom)")
                extra_budget_left[0] -= kb.courses[code]["credits"]
                nonlocal_update(code, parts)
        if (sem != student["current_semester"] and pursue_minor and minor.get("eligible")
                and minor_credits < minor["credits_required"]):
            extra_budget_left[0] = 4
            cands = [c for c in candidates("extra") if c[1] in minor_courses]
            if cands:
                v, code, parts, unlock = cands[0]
                add(code, "minor", reason_for(code, parts, unlock, "minor"))
                nonlocal_update(code, parts)
        for x in chosen:
            if x["code"]:
                taken.add(x["code"])
        total = sum(x["credits"] for x in chosen)
        semesters.append({"semester": sem, "season": _season(sem), "courses": chosen, "total_credits": total,
                          "credit_limit": limit, "notes": notes})

    for code in pinned:
        # still unplaced: explain and offer the best valid alternative
        sem0 = student["current_semester"]
        why = course_blockers(kb, student, code, sem0, completed_codes(kb, student), [], credit_limit, tuple(online_used))
        alt = None
        if code in kb.courses:
            skills = set(kb.course_skills.get(code, {}))
            alts = [c for c in kb.courses if c != code and skills & set(kb.course_skills.get(c, {}))
                    and not course_blockers(kb, student, c, sem0, completed_codes(kb, student), [], credit_limit, tuple(online_used))]
            alts.sort(key=lambda c: -sum(kb.course_skills[c].get(k, 0) for k in skills))
            alt = alts[0] if alts else None
            covered = [(x["code"], sem_["semester"]) for sem_ in semesters for x in sem_["courses"]
                       if x["code"] and skills & set(kb.course_skills.get(x["code"], {}))]
        else:
            covered = []
        msg = f"{code} cannot be scheduled: {'; '.join(why) or 'no free slot or credits remain'}."
        if alt:
            msg += f" Best valid option: {alt} ({kb.courses[alt]['title']})."
        elif covered:
            msg += " Your plan already builds the same skills through " + ", ".join(f"{c} (semester {s_})" for c, s_ in covered[:3]) + "."
        infeasible.append({"course": code, "reasons": why or ["no free slot or credits remain in any semester"],
                           "alternative": alt, "covered_by": covered[:3], "message": msg})

    if minor:
        if minor.get("eligible"):
            notes_global.append(f"{minor['name']}: eligible; plan reaches {minor_credits}/{minor['credits_required']} minor credits.")
        else:
            notes_global.append(minor["reason"])

    track = build_learning_track(kb, student, states, need, semesters[0] if semesters else None, done_modules, pace_factor)
    for s, v in track["skill_gain"].items():
        projected[s] = max(projected[s], v)
    milestones = []
    if goal:
        for m in goal["milestones"]:
            if m["semester"] >= student["current_semester"]:
                milestones.append({**m, "status": "planned"})
            else:
                milestones.append({**m, "semester": student["current_semester"], "status": "catch-up (was due earlier)"})
        milestones.append({"title": "Mid-semester checkpoint: re-take adaptive diagnostic on goal skills", "kind": "assessment",
                           "semester": student["current_semester"], "status": "planned", "week": 8})
    proj_ready = None
    if reqs:
        tot = sum(r["importance"] for r in reqs)
        proj_ready = round(sum(r["importance"] * min(1.0, projected[r["skill"]] / r["target"]) for r in reqs) / tot, 3)

    return {
        "student_id": student["id"], "goal": {"id": goal["id"], "name": goal["name"]} if goal else None,
        "semesters": semesters, "learning_track": track, "milestones": milestones,
        "minor": minor, "infeasible": infeasible, "notes": notes_global,
        "readiness_now": diag.get("readiness"), "readiness_projected": proj_ready,
        "mismatches": diag.get("mismatches", []),
        "skills": [{"skill": g["skill"], "name": g["name"], "mastery": g["mastery"], "target": g["target"], "status": g["status"]}
                   for g in diag.get("gaps", [])],
        "mastery_criteria": goal["mastery_criteria"] if goal else [],
    }


def _topo(kb: KB, skills: list[str]) -> list[str]:
    order, seen = [], set()

    def visit(s):
        if s in seen:
            return
        seen.add(s)
        for p in kb.skill_prereqs.get(s, []):
            if p in skills:
                visit(p)
        order.append(s)
    for s in skills:
        visit(s)
    return order


def _pick_resource(kb: KB, skill: str, level: int, formats: list[str], default_id: str):
    res = kb.resources_by_skill.get(skill, [])
    if not res:
        return kb.resources.get(default_id)
    return sorted(res, key=lambda r: (r["format"] not in formats, abs(r["level"] - level), r["id"]))[0]


def build_learning_track(kb: KB, student: dict, states: dict, need: dict, next_sem: dict | None, done_modules: set,
                         pace_factor: float) -> dict:
    cons = student.get("constraints", {})
    prefs = student.get("preferences", {})
    formats = prefs.get("formats", [])
    pace = {"slow": 1.25, "steady": 1.0, "fast": 0.85}.get(prefs.get("pace", "steady"), 1.0) * pace_factor
    cal = kb.rule("semester_calendar", {"weeks": 16, "midsem_week": 8, "endsem_weeks": [15, 16], "exam_week_capacity": 0.5})
    hpw = float(cons.get("hours_per_week", 6))
    course_skills_next = defaultdict(list)
    if next_sem:
        for c in next_sem["courses"]:
            if c["code"]:
                for s in kb.course_skills.get(c["code"], {}):
                    course_skills_next[s].append(c["code"])

    gap_skills = [s for s, (tgt, imp) in need.items() if states[s]["mastery"] < tgt or not states[s]["tested"]]
    gap_skills.sort(key=lambda s: -(need[s][1] * max(0.05, need[s][0] - states[s]["mastery"])))
    ordered = _topo(kb, gap_skills)
    items, skipped, skill_gain = [], [], {}

    for s in ordered:
        tgt, imp = need[s]
        st = states[s]
        m = st["mastery"]
        if m >= tgt and not st["tested"]:
            # likely known but never tested: verify instead of re-teaching
            items.append({"type": "assessment", "skill": s, "title": f"Checkpoint quiz: {kb.skills[s]['name']} (verify, no re-teaching)",
                          "hours": 0.5, "why": "Grades/self-report suggest you know this; a short quiz confirms it so you can skip the lessons."})
            continue
        mods = [x for x in kb.modules_by_skill.get(s, []) if x["id"] not in done_modules]
        min_level = 3 if m >= 0.65 else 2 if m >= 0.4 else 1
        for x in kb.modules_by_skill.get(s, []):
            if x["level"] < min_level and x["kind"] == "lesson":
                skipped.append({"module": x["id"], "title": x["title"], "why": f"skipped: your {kb.skills[s]['name']} level ({int(m*100)}%) is past this introductory material"})
        mods = [x for x in mods if x["level"] >= min_level or x["kind"] != "lesson"]
        if course_skills_next.get(s):
            codes = ", ".join(course_skills_next[s])
            mods = [x for x in mods if x["kind"] != "lesson"]
            note = f"lessons are covered by {codes} this semester; only active practice is added"
        else:
            note = ""
        if st["struggling"]:
            for p in kb.skill_prereqs.get(s, []):
                if states[p]["mastery"] < 0.6:
                    for x in kb.modules_by_skill.get(p, [])[:2]:
                        if x["id"] not in done_modules:
                            r = _pick_resource(kb, p, x["level"], formats, x["resource_id"])
                            items.append({"type": "remedial", "skill": p, "module": x["id"], "title": f"Refresher: {x['title']}",
                                          "hours": round(x["est_hours"] * pace, 1), "resource": _res(r),
                                          "why": f"Repeated low scores in {kb.skills[s]['name']}; strengthening the prerequisite {kb.skills[p]['name']} first."})
            r = _pick_resource(kb, s, 1, formats, "")
            items.append({"type": "remedial", "skill": s, "title": f"Alternative explanation: {r['title'] if r else kb.skills[s]['name']}",
                          "hours": round(2 * pace, 1), "resource": _res(r),
                          "why": "You have missed this topic repeatedly, so a different explanation and extra worked examples are added."})
        for x in mods:
            r = kb.resources.get(x["resource_id"]) if x["kind"] != "lesson" else _pick_resource(kb, s, x["level"], formats, x["resource_id"])
            items.append({"type": "practice" if x["kind"] in ("lab", "project") else "lesson", "skill": s, "module": x["id"],
                          "title": x["title"], "hours": round(x["est_hours"] * pace, 1), "resource": _res(r),
                          "why": note or f"closes the {kb.skills[s]['name']} gap ({int(m*100)}% -> {int(tgt*100)}%)"})
        items.append({"type": "assessment", "skill": s, "title": f"Checkpoint quiz: {kb.skills[s]['name']}", "hours": 0.5,
                      "why": "tested evidence decides whether the skill is demonstrated"})
        skill_gain[s] = min(tgt, max(m, tgt * 0.9))

    # pack into weeks; exam weeks have reduced capacity; long items are split
    weeks = []
    for w in range(1, cal["weeks"] + 1):
        cap = hpw * (cal["exam_week_capacity"] if (w == cal["midsem_week"] or w in cal["endsem_weeks"]) else 1.0)
        weeks.append({"week": w, "capacity": round(cap, 1), "hours": 0.0, "items": []})
    deferred = []
    wi = 0
    for it in items:
        remaining = it["hours"]
        part = 1
        placed_any = False
        while remaining > 1e-6 and wi < len(weeks):
            free = weeks[wi]["capacity"] - weeks[wi]["hours"]
            if free < 0.25:
                wi += 1
                continue
            h = round(min(free, remaining), 2)
            piece = dict(it, hours=h)
            if h < remaining or part > 1:
                piece["title"] = f"{it['title']} (part {part})"
            weeks[wi]["items"].append(piece)
            weeks[wi]["hours"] = round(weeks[wi]["hours"] + h, 2)
            remaining = round(remaining - h, 2)
            part += 1
            placed_any = True
        if remaining > 1e-6:
            deferred.append(dict(it, hours=remaining, partially_scheduled=placed_any))
            if it.get("skill") in skill_gain and not placed_any:
                skill_gain.pop(it["skill"], None)
    total = round(sum(w["hours"] for w in weeks), 1)
    return {"semester": next_sem["semester"] if next_sem else None, "hours_per_week": hpw, "pace_factor": round(pace, 2),
            "weeks": weeks, "deferred": deferred, "skipped": skipped, "total_hours": total, "skill_gain": skill_gain}


def _res(r):
    if not r:
        return None
    return {"id": r["id"], "title": r["title"], "provider": r["provider"], "url": r["url"], "format": r["format"], "license": r["license"]}
