"""Cubby — AI Front Desk. FastAPI app: serves /api/* and the built frontend
from one process (single deployable, one URL).

Startup wires the two seams (Retriever, Store) as singletons on app.state.
M0.0 boots with a keyword retriever and in-memory store — no ML deps, no API
key required just to start.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.config import CONFIG
from backend.core.retrieval.chunker import chunk_handbook
from backend.core.retrieval.index import KeywordRetriever
from backend.core.security.auth import require_auth
from backend.core.security.cost_guard import enforce_cost_limits
from backend.core.store.repo import InMemoryStore
from backend.routers import ask as ask_router
from backend.routers import auth as auth_router
from backend.routers import compliance as compliance_router
from backend.routers import forms as forms_router

_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    entries = chunk_handbook()
    app.state.retriever = KeywordRetriever(entries)
    app.state.store = InMemoryStore()
    app.state.handbook = entries
    yield


app = FastAPI(title="Cubby — AI Front Desk", lifespan=lifespan)

# Access gate: enforced server-side via require_auth on every guarded router
# below — never client-side-only. Unguarded: /api/auth (the entry point) and
# /api/health (non-sensitive; platform health checks need it open). Cost
# guard: only the two LLM-calling routers pay the daily/per-minute caps —
# /compliance is pure CRUD and costs nothing to call.
app.include_router(auth_router.router)
app.include_router(
    ask_router.router,
    dependencies=[Depends(require_auth), Depends(enforce_cost_limits)],
)
app.include_router(compliance_router.router, dependencies=[Depends(require_auth)])
app.include_router(
    forms_router.router,
    dependencies=[Depends(require_auth), Depends(enforce_cost_limits)],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "Cubby",
        "center": CONFIG.center_name,
        "town": CONFIG.center_town,
        "handbook_sections": len(app.state.handbook),
        "children": len(app.state.store.list_children()),
        "questions": len(app.state.store.list_questions()),
        "answer_model": CONFIG.answer_model,
        "vision_model": CONFIG.vision_model,
    }


# --- Frontend ---
# Real Vite app is built to frontend/dist (M0.1). Until then, a static
# two-tab placeholder so the app boots and both surfaces are visible.
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def placeholder() -> str:
        return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=375, initial-scale=1">
<title>Cubby — {CONFIG.center_name}</title>
<style>
 body{{font-family:system-ui;margin:0;background:#fdf6f0;color:#26333a}}
 header{{background:#0f766e;color:#fff;padding:16px 20px}}
 header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;opacity:.85;font-size:13px}}
 nav{{display:flex;gap:8px;padding:12px 20px;background:#fff;border-bottom:1px solid #eadfd6}}
 nav button{{flex:1;padding:10px;border:0;border-radius:10px;background:#f2e7de;font-weight:600}}
 nav button.active{{background:#f97362;color:#fff}}
 main{{padding:20px;max-width:600px;margin:0 auto}}
 .card{{background:#fff;border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:12px}}
 code{{background:#f2e7de;padding:1px 5px;border-radius:5px}}
</style></head><body>
<header><h1>🧸 Cubby</h1><p>{CONFIG.center_name} · {CONFIG.center_town}</p></header>
<nav><button class=active id=tp>Parent</button><button id=to>Operator</button></nav>
<main>
 <div class=card id=body></div>
 <div class=card><b>M0.0 — scaffold.</b> Backend boots; two-tab shell renders;
   <code>/api/health</code> is live. Grounded chat, form validation, and the
   compliance dashboard arrive in M0.1–M0.3.</div>
</main>
<script>
 const body=document.getElementById('body');
 const parent="<b>Parent</b><br>Ask a question, or see your child's health-report reminder. (M0.1)";
 const oper="<b>Operator</b><br>Scan a health form, view the compliance dashboard, and the questions &amp; gaps log. (M0.2+)";
 const tp=document.getElementById('tp'), to=document.getElementById('to');
 function set(a){{body.innerHTML=a===tp?parent:oper;tp.classList.toggle('active',a===tp);to.classList.toggle('active',a===to);}}
 tp.onclick=()=>set(tp); to.onclick=()=>set(to); set(tp);
 fetch('/api/health').then(r=>r.json()).then(d=>{{
   body.innerHTML+="<br><br><small>health: "+d.handbook_sections+" sections · "+d.children+" children · "+d.questions+" logged questions</small>";
 }});
</script>
</body></html>"""
