"""Generate synthetic, anonymised student profiles -> data/seed/students.json.

Deterministic (fixed random seed) so re-runs give identical data. No real student
records are used: names are synthetic, grades are sampled around a target CGPA
and the stored CGPA is *recomputed* from the sampled grades so every profile is
internally consistent.

Hand-written personas cover Appendix A of the problem statement and the edge
cases called out in Section 4 (backlogs, changing goals, interest that
conflicts with evidence, students near eligibility cut-offs, vague goals,
very little free time). The rest are sampled to vary year, branch, CGPA,
completed courses, goals, available time and learning preferences.

    python scripts/generate_profiles.py
"""
import csv
import json
import random
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
rng = random.Random(2026)

courses = {c["code"]: c for c in csv.DictReader(open(SEED / "courses.csv", encoding="utf-8"))}
programmes = {p["id"]: p for p in json.load(open(SEED / "programmes.json", encoding="utf-8"))}
GP = {"A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5, "D": 4, "F": 0}
LETTERS = [(9.5, "A"), (8.5, "A-"), (7.5, "B"), (6.5, "B-"), (5.5, "C"), (4.6, "C-"), (3.8, "D")]

FIRST = ["Aarav", "Diya", "Kabir", "Ananya", "Rohan", "Isha", "Arjun", "Meera", "Vihaan", "Saanvi", "Aditya", "Riya",
         "Krishna", "Tara", "Ishaan", "Nisha", "Dev", "Pooja", "Yash", "Sneha", "Karthik", "Lakshmi", "Faizan", "Zoya",
         "Harpreet", "Simran", "Rahul", "Neha", "Siddharth", "Aisha", "Varun", "Priya", "Manav", "Kavya", "Omkar", "Bhavna"]
INITIALS = "ABCDEGHIJKMNPRSTVY"


def letter(gp: float) -> str:
    for cut, l in LETTERS:
        if gp >= cut:
            return l
    return "F"


def core_courses(prog: str, upto_sem: int):
    out = []
    for c in courses.values():
        if c["course_type"] == "core" and prog in c["programme"].split(",") and 0 < int(c["semester"]) <= upto_sem:
            out.append((c["code"], int(c["semester"])))
    return sorted(out, key=lambda x: (x[1], x[0]))


def cgpa_of(completed):
    tot = sum(int(courses[c["code"]]["credits"]) for c in completed)
    pts = sum(GP[c["grade"]] * int(courses[c["code"]]["credits"]) for c in completed)
    return round(pts / tot, 2) if tot else 0.0


def make(sid, name, prog, year, target_cgpa, goal_id, goal_text="", interests=(), hours=8, extra_courses=(),
         grade_overrides=None, evidence=(), constraints=None, preferences=None, persona="", backlog=None, spread=0.9,
         tol=None):
    """year Y => completed semesters 1..2Y-1, next (planned) semester = 2Y (even, Jan-Apr)."""
    done_upto = 2 * year - 1
    completed = []
    for code, sem in core_courses(prog, done_upto):
        g = letter(rng.gauss(target_cgpa, spread))
        completed.append({"code": code, "grade": g, "semester": sem})
    for code, sem in extra_courses:
        completed.append({"code": code, "grade": letter(rng.gauss(target_cgpa, spread)), "semester": sem})
    for c in completed:
        if grade_overrides and c["code"] in grade_overrides:
            c["grade"] = grade_overrides[c["code"]]
        elif c["grade"] == "F" and (not backlog or c["code"] not in backlog):
            c["grade"] = "D"  # only explicit edge cases carry backlogs
    if backlog:
        for c in completed:
            if c["code"] in backlog:
                c["grade"] = "F"
    if tol:  # nudge free grades one letter at a time until CGPA is within tol of the target
        order = list(GP)
        free = [c for c in completed if c["grade"] != "F" and not (grade_overrides and c["code"] in grade_overrides)]
        for _ in range(200):
            diff = target_cgpa - cgpa_of(completed)
            if abs(diff) <= tol or not free:
                break
            c = rng.choice(free)
            i = order.index(c["grade"])
            if diff > 0 and i > 0:
                c["grade"] = order[i - 1]
            elif diff < 0 and i < len(order) - 2:
                c["grade"] = order[i + 1]
    cons = {"hours_per_week": hours, "not_together": [], "excluded_courses": [], "pinned_courses": []}
    cons.update(constraints or {})
    return {
        "id": sid, "name": name, "programme": prog, "year": year, "current_semester": 2 * year,
        "cgpa": cgpa_of(completed), "completed_courses": completed, "goal_id": goal_id, "goal_text": goal_text,
        "interests": list(interests), "constraints": cons,
        "preferences": preferences or {"formats": ["video", "practice"], "pace": "steady"},
        "persona": persona, "evidence": list(evidence),
    }


def ev(skill, source, score, detail="", attempts=1, minutes=0):
    return {"skill_id": skill, "source": source, "score": score, "detail": detail, "attempts": attempts, "time_spent_min": minutes}


students = []

# --- S1024: the worked example from Section 4 of the problem statement
students.append(make(
    "S1024", "Student S1024", "CHE", 3, 7.8, "software_engineer", "Software engineering role after graduation",
    interests=["machine learning"], hours=8,
    grade_overrides={"CS101": "B"},
    evidence=[ev("prog_fund", "assessment", .78, "Diagnostic: programming fundamentals 78%"),
              ev("discrete_math", "assessment", .55, "Diagnostic: discrete maths 55%"),
              ev("dsa", "assessment", .32, "Diagnostic: data structures & algos 32%"),
              ev("databases", "assessment", .10, "Diagnostic: databases 10%"),
              ev("ml", "self", .6, "Self-declared interest in machine learning")],
    constraints={"open_elective_slots": 2, "extra_credit_headroom": 6, "not_together": [["CS201", "CS102"]]},
    preferences={"formats": ["video", "practice"], "pace": "steady", "notes": "short videos, hands-on coding problems"},
    tol=0.05, persona="Problem-statement example: ChE Year 3 aiming for software; weak DSA and databases"))

# --- Appendix A personas
students.append(make("P001", "Aarav S.", "CHE", 2, 8.1, "software_engineer", "Software / IT role after graduation",
                     interests=["coding", "web"], hours=10,
                     evidence=[ev("prog_fund", "self", .7, "Self-declared: comfortable with Python")],
                     persona="Appendix A: 2nd-year ChE student targeting a software role"))
students.append(make("P002", "Diya R.", "ME", 3, 8.9, "higher_studies", "MS in robotics/controls abroad",
                     interests=["control systems", "research"], hours=10,
                     persona="Appendix A: higher studies (MS abroad), protect CGPA, research project, GRE/TOEFL timeline"))
students.append(make("P003", "Kabir N.", "CHE", 2, 7.2, "upsc_cse", "UPSC civil services (IAS)",
                     interests=["polity", "history"], hours=12,
                     evidence=[ev("polity_governance", "self", .5, "Self-declared: read Laxmikanth partly")],
                     persona="Appendix A: UPSC aspirant; HSS electives supporting optional subject; protect CGPA"))
students.append(make("P004", "Ananya T.", "ME", 2, 7.6, "startup_founder", "Build and launch a hardware startup",
                     interests=["startups", "product"], hours=9,
                     persona="Appendix A: interested in a startup; entrepreneurship and product courses; incubation cell"))
students.append(make("P005", "Rohan M.", "ME", 2, 7.4, "data_analyst", "Data analytics role by end of third year",
                     interests=["analytics", "sql"], hours=7,
                     persona="PM example persona: 2nd-year ME student aiming for a data-analytics role"))

# --- edge cases
students.append(make("E001", "Isha P.", "CHE", 3, 7.6, "data_analyst", "Data science",
                     interests=["data science", "ml"], hours=8,
                     grade_overrides={"MA102": "D", "MA201": "C-"},
                     evidence=[ev("ml", "self", .8, "Self-declared: strong interest and some Kaggle notebooks"),
                               ev("linear_algebra", "assessment", .3, "Diagnostic: linear algebra 30%")],
                     persona="Edge case: interest (data science) conflicts with evidence (weak linear algebra)"))
students.append(make("E002", "Arjun V.", "ME", 3, 6.4, "core_engineer", "Core mechanical design job",
                     hours=10, backlog=["ME203"],
                     persona="Edge case: backlog in a core course (Fluid Mechanics) that must be cleared"))
students.append(make("E003", "Meera J.", "CHE", 2, 7.45, "software_engineer", "Software role; wants the CS minor",
                     hours=9, spread=0.3, grade_overrides={"CS101": "A-"}, tol=0.04,
                     persona="Edge case: CGPA just below the CS-minor cut-off (7.5)"))
students.append(make("E004", "Vihaan K.", "ME", 3, 8.3, "data_analyst", "Switched from GATE prep to data analytics",
                     interests=["data"], hours=8,
                     evidence=[ev("thermodynamics", "assessment", .8, "GATE mock: thermodynamics 80%"),
                               ev("aptitude", "mock", .72, "GATE mock: general aptitude 72%")],
                     persona="Edge case: changing goals (was gate_core, now data analytics)"))
students.append(make("E005", "Saanvi B.", "CHE", 2, 7.9, "", "I just want a good job after college",
                     hours=8, persona="Edge case: vague goal; buddy must ask clarifying questions"))
students.append(make("E006", "Aditya G.", "ME", 4, 7.0, "software_engineer", "Software role, placement season soon",
                     hours=15, extra_courses=[("CS102", 5), ("DS201", 6)],
                     persona="Edge case: final-year student with one semester left"))
students.append(make("E007", "Riya D.", "CHE", 3, 9.2, "higher_studies", "PhD in catalysis",
                     hours=6, evidence=[ev("research_methods", "project", .7, "Summer research project report")],
                     persona="Edge case: high CGPA, overload-eligible, research evidence already present"))
students.append(make("E008", "Krishna L.", "ME", 2, 6.9, "software_engineer", "Software role",
                     hours=3, persona="Edge case: only 3 hours/week available"))
students.append(make("E009", "Tara F.", "CHE", 3, 8.0, "software_engineer", "Software role",
                     hours=10, extra_courses=[("CS102", 4), ("CS202", 5)],
                     evidence=[ev("dsa", "assessment", .85, "Timed DSA test 85%"), ev("prog_fund", "assessment", .9, "Coding test 90%")],
                     constraints={"excluded_courses": ["CS303"]},
                     persona="Edge case: already strong in DSA (must not repeat content); rejected Software Engineering course"))
students.append(make("E010", "Ishaan Q.", "ME", 1, 8.4, "gate_core", "GATE for IIT M.Tech",
                     hours=6, persona="Edge case: first-year student planning far ahead"))

# --- sampled population
GOAL_MIX = ["software_engineer"] * 6 + ["data_analyst"] * 5 + ["higher_studies"] * 4 + ["gate_core"] * 3 + \
           ["upsc_cse"] * 2 + ["startup_founder"] * 2 + ["core_engineer"] * 3 + ["product_mba"] * 2
GOAL_TEXT = {"software_engineer": "Software developer role", "data_analyst": "Data analyst / data scientist",
             "higher_studies": "MS or PhD", "gate_core": "Crack GATE", "upsc_cse": "Civil services",
             "startup_founder": "Start my own company", "core_engineer": "Core company job", "product_mba": "MBA / product manager"}
INTEREST = {"software_engineer": ["coding", "web", "competitive programming"], "data_analyst": ["data", "ml", "statistics"],
            "higher_studies": ["research", "simulation"], "gate_core": ["core subjects"], "upsc_cse": ["polity", "economy"],
            "startup_founder": ["startups", "product"], "core_engineer": ["design", "plants"], "product_mba": ["product", "business"]}
ELECTIVE_POOL = {"software_engineer": ["CS102", "CS202", "DS201"], "data_analyst": ["DS201", "CS102"],
                 "higher_studies": ["HS205", "RM301"], "gate_core": [], "upsc_cse": ["HS201", "HS203"],
                 "startup_founder": ["MS201", "HS201"], "core_engineer": [], "product_mba": ["MS201", "HS201"]}
FORMATS = [["video"], ["text"], ["practice"], ["video", "practice"], ["text", "practice"], ["video", "text"]]
SKILL_FOR_GOAL = {"software_engineer": ["prog_fund", "dsa", "databases"], "data_analyst": ["prob_stats", "data_analysis", "databases"],
                  "higher_studies": ["research_methods", "linear_algebra"], "gate_core": ["calculus", "aptitude"],
                  "upsc_cse": ["polity_governance", "economics"], "startup_founder": ["entrepreneurship", "business_fundamentals"],
                  "core_engineer": ["numerical_methods", "aptitude"], "product_mba": ["aptitude", "product_mgmt"]}

used = set()
for i in range(65):
    sid = f"S{2001 + i}"
    prog = rng.choice(["CHE", "ME"])
    year = rng.choice([1, 2, 2, 3, 3, 3, 4])
    goal = rng.choice(GOAL_MIX)
    target = round(min(9.6, max(5.6, rng.gauss(7.6, 0.9))), 2)
    while True:
        name = f"{rng.choice(FIRST)} {rng.choice(INITIALS)}."
        if name not in used:
            used.add(name)
            break
    extra = []
    done = 2 * year - 1
    pool = [c for c in ELECTIVE_POOL[goal]]
    for sem in range(4, done + 1):
        if pool and rng.random() < 0.6:
            code = pool.pop(0)
            # respect prerequisites of the sampled elective
            if code in ("CS202", "DS201", "CS102") or code.startswith(("HS", "MS")) or code == "RM301":
                if code == "RM301" and done < 4:
                    continue
                extra.append((code, sem))
    evidence = []
    for sk in SKILL_FOR_GOAL[goal]:
        r = rng.random()
        if r < 0.35:
            evidence.append(ev(sk, "self", round(rng.uniform(0.4, 0.85), 2), "Self-declared at onboarding"))
        elif r < 0.6:
            evidence.append(ev(sk, "assessment", round(rng.uniform(0.15, 0.9), 2), "Earlier diagnostic quiz",
                               attempts=rng.randint(1, 3), minutes=rng.randint(5, 25)))
    backlog = None
    if rng.random() < 0.07 and year >= 2:
        cands = [c for c, s in core_courses(prog, done) if s >= 3]
        if cands:
            backlog = [rng.choice(cands)]
    cons = {}
    if rng.random() < 0.3:
        cons["extra_credit_headroom"] = rng.choice([3, 4, 6])
    if rng.random() < 0.2:
        cons["max_credits"] = rng.choice([18, 20, 22])
    if rng.random() < 0.15:
        cons["not_together"] = [rng.sample(["CS102", "CS201", "CS204", "DS201", "HS201", "MS201"], 2)]
    students.append(make(
        sid, name, prog, year, target, goal, GOAL_TEXT[goal], interests=rng.sample(INTEREST[goal], 1 + (len(INTEREST[goal]) > 1)),
        hours=rng.choice([4, 5, 6, 8, 8, 10, 12, 15]), extra_courses=extra, evidence=evidence,
        constraints=cons, backlog=backlog,
        preferences={"formats": rng.choice(FORMATS), "pace": rng.choice(["slow", "steady", "fast"])},
        persona=f"Sampled: {programmes[prog]['name']} year {year}, goal {goal}"))

# long-term memory carried over from earlier (simulated) sessions
for st in students:
    if st["id"] == "E004":
        st["memories"] = [{"kind": "decision", "content": "Semester 5: goal changed from gate_core (GATE / M.Tech) to data_analyst after an analytics internship. Keep GATE as a fallback."}]
    if st["id"] == "E009":
        st["memories"] = [{"kind": "override", "content": "Student rejected CS303 Software Engineering (prefers learning via own team project)."}]

with open(SEED / "students.json", "w", encoding="utf-8") as f:
    json.dump(students, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"wrote {len(students)} students")
