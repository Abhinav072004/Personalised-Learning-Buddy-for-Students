# Data and knowledge base

## Scope

Two programmes in depth, as the problem statement recommends: **B.Tech Chemical Engineering** and **B.Tech Mechanical Engineering**. Plus the courses they draw on: first-year common courses, a CSE minor, HSS and management open electives, research methodology, and credit-eligible NPTEL courses.

| Item | Count |
|---|---|
| Courses | 57 |
| Skills | 36 |
| Modules / lessons / labs / projects | 196 |
| Open learning resources | 61 |
| Assessment and practice questions (MCQ) | 148 (+35 labs/projects = 183 exercises) |
| Goals | 8 |
| Minors | 3 |
| Academic rules | 13 |
| Student profiles (synthetic) | 81 |

See `docs/data_quality_report.md` for the generated counts and checks.

## Schema (reasoning-oriented)

- `courses(code, title, department, credits, offered odd/even/both, course_type core|dept_elective|open_elective|minor|online, mode, programme, semester, weekly_hours, syllabus, objectives, source, last_verified)`
- `prerequisites(course → prereq, min_grade)`: an acyclic graph, checked
- `course_skills(course, skill, level 0..1)`: how far a course takes a skill (skill coverage)
- `skills(id, category, prereq_skills)`: the skill graph used to order learning and pick remedial content
- `modules(skill, course, level 1–3, kind lesson|lab|project, est_hours, resource)`
- `resources(provider, url, skills, format, level, hours, licence, credit_eligible)`
- `questions(skill, difficulty 1–3, options, answer, explanation, source)`
- `goals(required_skills[{skill|@programme_core, target, importance}], milestones, mastery_criteria, recommended_minor, protect_cgpa)`
- `programmes(elective_slots per semester, core_skills)`, `minors(min_cgpa, credits_required, courses, excluded_programmes)`, `rules(key → JSON value, description, source)`

Prerequisites, eligibility (CGPA cut-offs, overload, online credit, minors) and skill coverage are all first-class data, so every check is a query, not a prompt.

## Sources

| Data | Source | Status |
|---|---|---|
| Course catalogue, credits, offerings, prerequisites, programme structure, minors, credit and overload rules | **Illustrative**, modelled on a typical IIT B.Tech structure | **Team must replace and verify against the institute's official academic handbook / curriculum PDFs and set `source` + `last_verified` per row** |
| Online credit rule | UGC (Credit Framework for Online Learning Courses through SWAYAM) Regulations, 2021, plus institute policy | verify institute-specific limits |
| Open resources | MIT OpenCourseWare, NPTEL, Khan Academy, NCERT, LearnChemE, Harvard CS50, OSTEP, MDN, The Odin Project, Kaggle Learn, Google MLCC, Y Combinator Startup School, Purdue OWL, FreeCAD | URLs and licences in `resources.csv`. Some NPTEL entries link to the NPTEL catalogue rather than a course id. Pin exact course ids when verifying. |
| Questions | Authored by the team from standard syllabus content | each checked for a single correct answer |
| Student profiles | Synthetic (`scripts/generate_profiles.py`, fixed seed); no real student records | anonymised by construction |

## How accuracy and completeness are checked

`python scripts/check_kb.py --write` runs on every change and is enforced in development:

- **Accuracy:** every MCQ answer is one of its options, with no duplicate options and valid difficulty. Course-skill levels are in (0, 1].
- **Consistency:** all references resolve. The prerequisite graph is acyclic. Core courses are offered in their semester's parity and their prerequisites are scheduled earlier. Minors can reach their credit requirement.
- **Completeness:** every skill has ≥ 1 open resource, ≥ 3 modules and ≥ 4 questions spanning easy to hard. Every goal skill is learnable.
- **Currency and traceability:** every course has `source` and `last_verified`. Every resource has a URL and licence.
- **Profiles:** every student references existing programmes, goals, courses and skills, and the stored CGPA is recomputed from the grades.

Manual checks the team should run when importing real institute data: cross-check codes, credits and prerequisites against two sources (handbook and department page), confirm the current semester's offerings with the academic office, and record the date in `last_verified`.

## Data ethics

Only public institute information, openly licensed content and synthetic profiles are used. Survey responses must be anonymised (see `docs/survey.md`). No real grades or personal details are stored without consent.
