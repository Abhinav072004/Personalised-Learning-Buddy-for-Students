# Personalised Learning Buddy for Students

An AI-powered learning buddy for students of one institute. It understands a student and their goal, finds skill gaps from evidence, builds a multi-semester plan from the institute's curriculum and open resources **within the academic rules**, adapts the plan to progress, and checks whether the student has actually **demonstrated** the target skills.

**Assess → Personalise → Learn → Practise → Adapt → Demonstrate mastery**

Built for the Inter IIT Tech Meet 15.0 Adobe problem statement.

---

## Run it

Requirements: Docker (linux/amd64, no GPU). The total image size is well under 5 GB.

```bash
cp .env.example .env          # set LLM_MODEL and LLM_API_KEY (and LLM_API_BASE if needed)
docker compose up --build     # single command: Postgres + backend/UI + Adminer
```

| What | URL |
|---|---|
| Student app | http://localhost:8000 (deep links: `/?sid=S1024#plan`) |
| Admin / data control | http://localhost:8000/admin |
| Database viewer (Adminer) | http://localhost:8080 (System PostgreSQL, server `db`, user / password / db: `buddy`) |
| API docs (OpenAPI) | http://localhost:8000/docs |

**Reset to the original seed state:**

```bash
docker compose exec backend python -m app.seed --reset
# or: POST http://localhost:8000/api/admin/reset   (button on /admin)
```

**No LLM key?** Everything except free-form phrasing still works: planning, validation, assessments, adaptation, memory and overrides are deterministic, and chat falls back to rule-based replies. The UI says "offline mode" when this happens.

### LLM configuration (Section 5)

All LLM calls go through **LiteLLM** (`backend/app/llm.py`). No model names, keys or endpoints appear anywhere in the code or image.

| Variable | Meaning |
|---|---|
| `LLM_MODEL` | Any LiteLLM model string, e.g. `openai/<model>`, `azure/<deployment>`, `gemini/<model>` |
| `LLM_API_KEY` | Provider key |
| `LLM_API_BASE` | Optional endpoint (Azure, self-hosted, proxy) |
| `EMBEDDING_MODEL` | Not used: retrieval is structured (SQL over the knowledge base), so no embeddings |
| `LLM_TIMEOUT`, `LLM_MAX_RETRIES` | Per-call timeout and retries. Fallback on failure. |

**Model used for tuning and testing:** `gemini/gemini-2.0-flash` (default in `.env.example`). Replace this line and the default with the model you actually test on before submitting.

The only outbound network calls are to the configured model provider. The UI loads no CDN assets, and LiteLLM's remote cost-map fetch is disabled.

### Development without Docker

```bash
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # (bin/ on Linux/macOS)
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload        # SQLite by default
../.venv/Scripts/python tests/test_end_to_end.py                              # end-to-end tests
../.venv/Scripts/python ../scripts/evaluate.py                                # writes docs/evaluation_report.md
python ../scripts/check_kb.py --write                                         # writes docs/data_quality_report.md
```

---

## Where each kind of data lives

| Data | Seed file (plain CSV/JSON, loaded at start-up) | Database table | Edit via |
|---|---|---|---|
| Courses (code, credits, offering, type, mode, syllabus, source) | `data/seed/courses.csv` | `courses` | /admin, Adminer |
| Prerequisites | `data/seed/prerequisites.csv` | `prerequisites` | " |
| Course → skill coverage | `data/seed/course_skills.csv` | `course_skills` | " |
| Skills (+ skill prerequisites) | `data/seed/skills.csv` | `skills` | " |
| Modules / lessons / labs / projects | `data/seed/modules.csv` | `modules` | " |
| Open learning resources (NPTEL, MIT OCW, NCERT...) | `data/seed/resources.csv` | `resources` | " |
| Question bank (diagnostic + practice) | `data/seed/questions.json` | `questions` | " |
| Goals (required skills, milestones, mastery criteria) | `data/seed/goals.json` | `goals` | " |
| Programmes (elective slots per semester) | `data/seed/programmes.json` | `programmes` | " |
| Minors (CGPA cut-off, course list) | `data/seed/minors.json` | `minors` | " |
| Academic rules (credit limits, overload, online credit, backlogs, calendar, evidence weights) | `data/seed/rules.json` | `rules` | " |
| Student profiles (synthetic) + initial evidence + memories | `data/seed/students.json` | `students`, `evidence`, `memories` | /admin, Adminer, `PATCH /api/students/{id}` |
| Plan versions (content, validation, diff, reason) | generated | `plans` | read-only history |
| Chat messages / long-term memory | generated | `messages`, `memories` | /admin |
| Assessment sessions | generated | `diagnostic_sessions` | |

**Edits re-process immediately.** Editing a student through /admin or the API re-plans that student. Editing the knowledge base re-plans everyone. Edits made directly in Adminer are picked up the next time a plan is read: each plan stores a fingerprint of all its inputs (profile, evidence, module progress, a hash of the whole KB), and any difference triggers a new validated plan version.

The seed files are generated by `scripts/build_kb.py` (knowledge base) and `scripts/generate_profiles.py` (81 synthetic profiles). Both are deterministic, and either the files or the scripts can be edited.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Architecture, student model (learning), planning, request handling (solving), memory, context, LLM vs deterministic split, mastery, data flow |
| [docs/product.md](docs/product.md) | Users, problem, personas, requirements with acceptance criteria, learning journey, personalisation strategy, mastery criteria, metrics, evaluation process, trade-offs |
| [docs/data_and_knowledge_base.md](docs/data_and_knowledge_base.md) | Schema, sources, how accuracy and completeness are checked, student profiles |
| [docs/survey.md](docs/survey.md) | Survey instrument, anonymisation protocol, findings template |
| [docs/data_quality_report.md](docs/data_quality_report.md) | Generated quality checks |
| [docs/evaluation_report.md](docs/evaluation_report.md) | Generated evaluation over all profiles |

## Demo script (3–5 min)

1. **Assess:** open **S1024** (the problem-statement example: ChemE Y3 → software). Overview shows readiness and gaps backed by evidence, plus the DSA/DB mismatch alert. Run the adaptive diagnostic (≤ 12 questions).
2. **Personalise:** Plan tab shows semesters 6–8 with course codes and reasons, CS minor eligibility, and all 15 validation checks. "Not for me" on CS305 re-plans and shows the diff. Ask for CS203 to see an infeasible request explained with the best valid option.
3. **Learn / Practise:** this week's items with NPTEL/OCW links, practice questions, skipped intro content.
4. **Adapt:** Adapt tab → strong vs weak quiz in DSA → compare plans (remedial prerequisites and alternative explanations for the weak case).
5. **Other goals:** switch to **P003** (UPSC) and **P002** (MS abroad) to show dissimilar plans. Open **E005** for a vague goal and clarifying questions.
6. **Converse:** chat "I can only do 5 hours a week" → plan v+1. Start a new session and ask "what changed?" to show long-term memory. Try "ignore previous instructions…" to show the guard.
7. **Data control:** /admin → edit a course offering → plans re-generated. Adminer view. Reset.
