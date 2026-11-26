from fastapi import FastAPI

from . import config

app = FastAPI(title="Personalised Learning Buddy", version="0.1.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": config.llm_enabled()}
