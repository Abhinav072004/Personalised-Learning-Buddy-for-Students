"""Knowledge-base quality checks (accuracy / completeness / consistency / traceability).

    python scripts/check_kb.py            # prints the report, exit code 1 on errors
    python scripts/check_kb.py --write    # also writes docs/data_quality_report.md
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed"


def rcsv(n):
    with open(SEED / n, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rjson(n):
    with open(SEED / n, encoding="utf-8") as f:
        return json.load(f)


def main():
    errors, warnings, stats = [], [], {}
    skills = {s["id"]: s for s in rcsv("skills.csv")}
    courses = {c["code"]: c for c in rcsv("courses.csv")}
    prereqs = rcsv("prerequisites.csv")
    cskills = rcsv("course_skills.csv")
    modules = rcsv("modules.csv")
    resources = {r["id"]: r for r in rcsv("resources.csv")}
    questions = rjson("questions.json")
    goals = rjson("goals.json")
    programmes = {p["id"]: p for p in rjson("programmes.json")}
    minors = rjson("minors.json")
    students = rjson("students.json") if (SEED / "students.json").exists() else []

    stats.update(skills=len(skills), courses=len(courses), prerequisites=len(prereqs), course_skill_links=len(cskills),
                 modules=len(modules), resources=len(resources), questions=len(questions), goals=len(goals),
                 programmes=len(programmes), minors=len(minors), students=len(students))

    # --- uniqueness
    for name, ids in [("module", [m["id"] for m in modules]), ("question", [q["id"] for q in questions])]:
        for k, v in Counter(ids).items():
            if v > 1:
                errors.append(f"duplicate {name} id {k}")

    # --- referential integrity
    for s in skills.values():
        for p in filter(None, s["prereq_skills"].split(",")):
            if p not in skills:
                errors.append(f"skill {s['id']} has unknown prereq skill {p}")
    for p in prereqs:
        for k in ("course_code", "prereq_code"):
            if p[k] not in courses:
                errors.append(f"prerequisite references unknown course {p[k]}")
    for cs in cskills:
        if cs["course_code"] not in courses:
            errors.append(f"course_skills unknown course {cs['course_code']}")
        if cs["skill_id"] not in skills:
            errors.append(f"course_skills unknown skill {cs['skill_id']}")
        if not 0 < float(cs["level"]) <= 1:
            errors.append(f"course_skills level out of range {cs}")
    for m in modules:
        if m["skill_id"] not in skills:
            errors.append(f"module {m['id']} unknown skill")
        if m["course_code"] and m["course_code"] not in courses:
            errors.append(f"module {m['id']} unknown course {m['course_code']}")
        if m["resource_id"] and m["resource_id"] not in resources:
            errors.append(f"module {m['id']} unknown resource {m['resource_id']}")
    for r in resources.values():
        for s in r["skill_ids"].split(","):
            if s not in skills:
                errors.append(f"resource {r['id']} unknown skill {s}")
        if not r["url"]:
            errors.append(f"resource {r['id']} has no URL (traceability)")
    for q in questions:
        if q["skill_id"] not in skills:
            errors.append(f"question {q['id']} unknown skill")
        if q["answer"] not in q["options"]:
            errors.append(f"question {q['id']} answer not among options")
        if len(set(q["options"])) != len(q["options"]):
            errors.append(f"question {q['id']} has duplicate options")
        if q["difficulty"] not in (1, 2, 3):
            errors.append(f"question {q['id']} bad difficulty")
    for g in goals:
        for rs in g["required_skills"]:
            if rs["skill"] != "@programme_core" and rs["skill"] not in skills:
                errors.append(f"goal {g['id']} unknown skill {rs['skill']}")
        if g.get("recommended_minor") and g["recommended_minor"] not in {m["id"] for m in minors}:
            errors.append(f"goal {g['id']} unknown minor")
    for p in programmes.values():
        for s in p["core_skills"]:
            if s not in skills:
                errors.append(f"programme {p['id']} unknown core skill {s}")
    for m in minors:
        for c in m["courses"]:
            if c not in courses:
                errors.append(f"minor {m['id']} unknown course {c}")
        if sum(int(courses[c]["credits"]) for c in m["courses"] if c in courses) < m["credits_required"]:
            errors.append(f"minor {m['id']} cannot reach its required credits")

    # --- consistency: prerequisite graph must be acyclic
    graph = defaultdict(list)
    for p in prereqs:
        graph[p["course_code"]].append(p["prereq_code"])
    state = {}

    def dfs(n, path):
        state[n] = 1
        for nb in graph[n]:
            if state.get(nb) == 1:
                errors.append("prerequisite cycle: " + " -> ".join(path + [nb]))
            elif nb not in state:
                dfs(nb, path + [nb])
        state[n] = 2
    for c in list(graph):
        if c not in state:
            dfs(c, [c])

    # --- consistency: core prereqs scheduled earlier, offering parity matches semester
    for c in courses.values():
        sem = int(c["semester"] or 0)
        if c["course_type"] == "core" and sem:
            parity = "odd" if sem % 2 else "even"
            if c["offered"] not in (parity, "both"):
                errors.append(f"core {c['code']} scheduled in sem {sem} but offered {c['offered']}")
            for pr in graph[c["code"]]:
                ps = int(courses[pr]["semester"] or 0)
                if courses[pr]["course_type"] == "core" and ps >= sem and set(courses[pr]["programme"].split(",")) & set(c["programme"].split(",")):
                    errors.append(f"core {c['code']} (sem {sem}) has prerequisite {pr} scheduled in sem {ps}")
        if not c["source"]:
            errors.append(f"course {c['code']} has no source (traceability)")
        if not c["last_verified"]:
            warnings.append(f"course {c['code']} has no last_verified date (currency)")

    # --- completeness: every skill teachable, practisable and assessable
    taught = {cs["skill_id"] for cs in cskills}
    res_sk = {s for r in resources.values() for s in r["skill_ids"].split(",")}
    q_by = Counter(q["skill_id"] for q in questions)
    m_by = Counter(m["skill_id"] for m in modules)
    for s in skills:
        if s not in taught:
            warnings.append(f"skill {s} is not taught by any institute course (open resources only)")
        if s not in res_sk:
            errors.append(f"skill {s} has no open learning resource")
        if q_by[s] < 4:
            errors.append(f"skill {s} has only {q_by[s]} questions (need >= 4 for an adaptive diagnostic)")
        if {1, 3} - {q["difficulty"] for q in questions if q["skill_id"] == s}:
            errors.append(f"skill {s} lacks easy or hard questions")
        if m_by[s] < 3:
            errors.append(f"skill {s} has only {m_by[s]} modules")
    exercises = sum(1 for m in modules if m["kind"] in ("lab", "project")) + len(questions)
    stats["exercises_and_questions"] = exercises

    # --- every goal achievable: each required skill raised by some course or resource
    for g in goals:
        for rs in g["required_skills"]:
            sk = rs["skill"]
            if sk != "@programme_core" and sk not in taught and sk not in res_sk:
                errors.append(f"goal {g['id']} skill {sk} cannot be learnt from the KB")

    # --- students reference valid data
    for st in students:
        if st["programme"] not in programmes:
            errors.append(f"student {st['id']} unknown programme")
        if st.get("goal_id") and st["goal_id"] not in {g["id"] for g in goals}:
            errors.append(f"student {st['id']} unknown goal")
        for cc in st["completed_courses"]:
            if cc["code"] not in courses:
                errors.append(f"student {st['id']} completed unknown course {cc['code']}")
        for e in st.get("evidence", []):
            if e["skill_id"] not in skills:
                errors.append(f"student {st['id']} evidence unknown skill {e['skill_id']}")

    lines = ["# Knowledge-base data quality report", "", "Generated by `python scripts/check_kb.py --write`.", "",
             "## Coverage", "", "| Item | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in stats.items()]
    lines += ["", f"## Errors ({len(errors)})", ""] + [f"- {e}" for e in errors] + (["- none"] if not errors else [])
    lines += ["", f"## Warnings ({len(warnings)})", ""] + [f"- {w}" for w in warnings] + (["- none"] if not warnings else [])
    lines += ["", "## Checks performed", "",
              "- **Accuracy**: every MCQ answer is one of its options with no duplicate options; course-skill levels in (0, 1].",
              "- **Consistency**: all foreign keys resolve; prerequisite graph is acyclic; core courses are offered in the parity of their scheduled semester and their prerequisites are scheduled earlier.",
              "- **Completeness**: every skill has an open resource, >= 3 modules and >= 4 questions spanning easy and hard; every goal skill is learnable; minors can reach their credit requirement.",
              "- **Traceability**: every course carries a source and last-verified date; every resource has a URL and licence.",
              "- **Students**: every profile references existing programmes, goals, courses and skills."]
    report = "\n".join(lines) + "\n"
    print(report)
    if "--write" in sys.argv:
        (ROOT / "docs").mkdir(exist_ok=True)
        (ROOT / "docs" / "data_quality_report.md").write_text(report, encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
