# Product rationale

> **Team to complete:** sections marked **[SURVEY]** must be filled in from your own institute survey (see `docs/survey.md`). The hypotheses below are the starting point the product was designed around. Replace them with real findings and counts; do not submit them as survey results.

## 1. Target users and problem

**Users:** undergraduate (B.Tech) students, starting with Chemical and Mechanical Engineering, whose ambitions often differ from their branch: software, data, higher studies, GATE/PSU, civil services, startups, MBA/product.

**Problem:** the curriculum is one-size-fits-all, and academic rules (minors, CGPA cut-offs, online credit, prerequisites, credit limits) are navigated through seniors and notice boards. Students discover useful electives late, over-commit or under-commit, and cannot tell whether finishing a course means they are actually ready for their goal.

## 2. Survey findings **[SURVEY]**

Design hypotheses to validate:
1. Non-CS students discover relevant electives and minors late, mostly through seniors.
2. Students don't know if they are eligible for a minor or how close they are to a cut-off.
3. Students over-rely on course grades as a readiness signal.
4. Available weekly time varies widely (3–15 h), and plans that ignore it are abandoned.
5. Goals change, especially in years 2–3, and students want to know what they lose and keep.

## 3. Personas (from Appendix A, extended)

| Persona | Profile id | Goal | Key need |
|---|---|---|---|
| ChemE → software | S1024, P001 | Software role | Map open electives and the CS minor to software skills; sequence programming → DSA → DB/OS; projects and placement prep within credit limits |
| Mech → analytics | P005 | Data analytics | SQL + statistics + a portfolio project by end of year 3 |
| Higher studies | P002, E007 | MS/PhD | Protect CGPA, research methods and writing, UG project, GRE/TOEFL/GATE timeline |
| Civil services | P003 | UPSC | HSS electives that support the optional subject, weekly GS plan, protect CGPA |
| Founder | P004 | Startup | Entrepreneurship and product courses, MVP milestones, incubation cell (outside the buddy) |
| Edge cases | E001–E010 | various | Interest vs evidence conflict, backlog, CGPA just under the minor cut-off, changed goal, vague goal, final year, 3 h/week, already strong (no repeats), first year |

The 81 profiles (`data/seed/students.json`) vary programme, year (1–4), CGPA (≈5.5–9.5), completed courses, goals, hours (3–15), formats and pace, so the system cannot be hand-tuned to a few personas.

## 4. Prioritised requirements with acceptance criteria

| # | Priority | Requirement | Acceptance criteria (how we test) |
|---|---|---|---|
| R1 | Must | Every plan satisfies all academic and personal constraints | 15-check validator passes for 100% of profiles (evaluation report) |
| R2 | Must | Recommendations exist in the KB and cite course codes | `exists` check; UI shows codes; LLM is instructed to cite only fact-sheet codes |
| R3 | Must | Evidence-weighted diagnosis | Self-declared skills alone never reach "demonstrated"; grades alone yield "completed, not demonstrated" |
| R4 | Must | Short adaptive diagnostic | ≤ 12 questions; difficulty moves up/down per answer; only skills lacking tested evidence |
| R5 | Must | Plan adapts to scores, attempts, time, repeated misses, completion | Strong vs weak simulation differs; weak adds remedial prerequisites (80/80 profiles) |
| R6 | Must | Never assign mastered content | `no_mastered` check; intro modules skipped and listed with reasons |
| R7 | Must | Impossible requests are explained with the best valid option | Asking for CS203 without prerequisites returns reasons and alternative (test) |
| R8 | Must | Long-term memory across sessions | Overrides and summaries are visible in a new session (test) |
| R9 | Should | Interest vs evidence conflicts surfaced with goal reassessment | Mismatch alert plus goal-fit list (E001) |
| R10 | Should | Graceful LLM failure | Chat works with no key (offline mode) |
| R11 | Should | Admin data control, edits reflected immediately | Admin edit → new plan version (test) |
| R12 | Could | Learning-pace adaptation | Slow time and attempt signals scale scheduled hours |

## 5. Learning objectives (examples)

- **Software:** by placement season (sem 7), solve medium DSA problems under time, build and deploy a full-stack project, and explain OS/DB fundamentals in interviews.
- **Analytics:** by end of year 3, score ≥ 70% on timed SQL and statistics sets and ship an end-to-end analytics project.
- **Higher studies:** by sem 7, produce a research proposal and a project report, with CGPA ≥ 8.0.
- **UPSC:** by graduation, complete NCERT-level GS foundations and score ≥ 55% on prelims mocks without hurting CGPA.

## 6. Learning journey

Onboarding (2 min: programme, year, CGPA, goal in own words, hours, formats, optional self-ratings)
→ adaptive diagnostic (≤ 12 questions)
→ overview (readiness, gaps with evidence, mismatches)
→ plan (semesters, reasons, checks, milestones; reject or request courses)
→ weekly learning track (lessons, resources, practice, checkpoints)
→ practice and checkpoints feed evidence
→ plan adapts (diff explained)
→ mocks and projects demonstrate goal-level mastery
→ chat at any point; history shows how the plan evolved.

## 7. Personalisation strategy and conflicting signals

- **Evidence reliability:** tested > project > exercise > grade > self-report (weights in `rules.json`). Recency matters: a new quiz outweighs an old grade.
- **Interest vs evidence:** interest decides the *goal* (the student's choice). Evidence decides the *path*, meaning which gaps to close first and how much remedial work. When they diverge strongly, the buddy names the gap, adds work to close it, and offers a data-based goal reassessment. It never silently overrides the student.
- **Preferences:** formats steer resource choice, and pace and observed time scale hours. Hard constraints (rules) always win over preferences. Student overrides (reject/request) win over recommendations when valid.
- **CGPA protection:** for goals that need CGPA (higher studies, UPSC, GATE), the buddy avoids overloads and states the trade-off.

## 8. Mastery criteria

A skill is **demonstrated** when mastery ≥ the goal's target with confidence ≥ 0.55 and at least one tested item. A goal is **ready** when every importance-3 skill is demonstrated and the goal's criteria (timed mocks, a project, mock interviews) are recorded as `mock` or `project` evidence.

## 9. Success metrics

| Metric | Definition | Where |
|---|---|---|
| Plan adherence | Share of students who complete planned modules for 4+ consecutive weeks | `module_progress` |
| Learning gain | Change in diagnostic scores between start and mid-semester checkpoint | `evidence` |
| Readiness gain | Change in goal readiness per semester | plans |
| Usefulness | Mean student rating of plans (1–5) | `/api/metrics` (feedback) |
| Override rate | Share of recommendations rejected (signals poor fit) | memories |
| Validity | % plans passing all checks (target 100%) | evaluation report |

## 10. Evaluation process

1. **Automated:** `scripts/evaluate.py` runs all 81 profiles. It checks every plan against the checklist (valid prerequisites, goal skills covered, no repeated content, constraints), checks re-run consistency, and runs strong vs weak adaptation. Results are in `docs/evaluation_report.md`.
2. **End-to-end tests:** `backend/tests/test_end_to_end.py` covers journeys (diagnostic → re-plan, overrides, infeasible requests, memory across sessions, injection, vague goals, admin edits).
3. **LLM answers:** with the configured model, run a fixed script of chat prompts per persona and check grounding (only KB course codes cited), clarifying questions for vague goals, and refusal of injections. **[Team: record results]**
4. **User testing [SURVEY]:** 5–10 students from different branches use the buddy for one week and rate usefulness and clarity of explanations.

## 11. Key trade-offs

| Trade-off | Decision |
|---|---|
| Extra electives for skill-building vs CGPA and core workload | Extra credits only within the student's stated headroom/cap. CGPA-sensitive goals avoid overload. Remaining work goes to the self-paced track, which respects hours. |
| Learning effectiveness vs time | Active practice first, intro material skipped when known, excess deferred rather than overloading weeks. |
| Content complexity | Modules are levelled 1–3. Struggling students get prerequisite refreshers and alternative explanations before harder material. |
| Diagnostic accuracy vs length | ≤ 6 skills × 2 adaptive questions, refined continuously by checkpoints and practice. |
| LLM flexibility vs reliability | LLM for language only. Rules, scheduling, grading and validation are deterministic and verifiable. |
