# Personalised Learning Buddy for Students

AI-powered learning buddy for an institute's students: **Assess → Personalise → Learn → Practise → Adapt → Demonstrate Mastery**.
Built for the Inter IIT Tech Meet 15.0 Adobe problem statement.

> Work in progress. The full README (run steps, data guide, architecture) is filled in as milestones land.

## Quick start

```bash
cp .env.example .env      # set LLM_MODEL / LLM_API_KEY
docker compose up --build
```

- App: http://localhost:8000
- Adminer (DB viewer): http://localhost:8080 (server `db`, user/password/db `buddy`)
