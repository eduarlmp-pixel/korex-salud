# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack
- **Backend:** FastAPI 0.111 + Uvicorn
- **DB:** SQLite via SQLAlchemy 2.0.30 (stable; use `--pre` only if on Python 3.14)
- **Auth:** JWT (python-jose HS256) + passlib/bcrypt, stored as HttpOnly cookie `access_token`
- **Templates:** Jinja2 server-side rendering — no JS framework, no JSON API endpoints
- **Python:** 3.10+ recommended

## Running the project
```bash
# Windows
venv\Scripts\activate

# First time only
pip install -r requirements.txt
pip install bcrypt==4.0.1   # passlib requires this exact version
pip install qrcode Pillow
python seed.py              # creates DB + demo user admin@qms.co / admin123

# Start server
uvicorn main:app --reload --port 8000
```

Known install errors:
| Error | Fix |
|-------|-----|
| `TypeError: __firstlineno__` | `pip install sqlalchemy --pre --upgrade` (Python 3.14 only) |
| `ValueError password > 72 bytes` | `pip install bcrypt==4.0.1` |
| `ModuleNotFoundError: qrcode` | `pip install qrcode Pillow` |

## Architecture

### Entry point
`main.py` registers all routers, mounts `/static`, creates DB tables on startup (`Base.metadata.create_all`), and serves the home dashboard at `/`. There is no migration framework configured — schema changes require dropping and recreating the DB or running raw SQL.

### Multi-router files
Two files export more than one router and must be included accordingly in `main.py`:
- `routers/infraestructura.py` → `sistemas_router` (prefix `/sistemas`) + `ambiente_router` (prefix `/ambiente-fisico`)
- `routers/otros.py` → `riesgos_router`, `indicadores_router`, `talento_router`, `pqrs_router`, `flujos_router`

### Auth pattern
Every handler must manually guard:
```python
current_user = Depends(auth.get_current_user)
if not current_user: return RedirectResponse(url="/login")
```
`auth.get_current_user` reads the `access_token` cookie, decodes the JWT, and queries the user. There is no middleware-level auth — each endpoint is responsible.

### Router convention
```python
router = APIRouter(prefix="/mi-modulo", tags=["mi-modulo"])

@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    items = db.query(models.MiModelo).filter_by(activo=True).all()
    return templates.TemplateResponse("mi-modulo/lista.html",
        {"request": request, "user": current_user, "items": items})

@router.post("/{id}/editar")          # Both GET and POST needed for edit forms
async def editar_post(...): ...
```

### Model conventions
All models live in `models.py` (single file, ~850 lines). Key patterns:
- **Soft deletes**: use `activo = Column(Boolean, default=True)` — never hard-delete; filter with `.filter_by(activo=True)`
- **Audit trail**: `creado_en`, `creado_por` on every model; `modificado_en` where updates happen
- **Relationships**: bidirectional `back_populates` everywhere — watch for N+1 queries on list views
- **Signatures**: stored as base64 `Text` fields (e.g., `firma_conductor`, `firma_tecnico`)

### Templates
`templates_config.py` creates the shared `Jinja2Templates` instance and adds `now` as a global (usable as `{{ now() }}` in templates).

Template skeleton:
```html
{% extends "base.html" %}
{% set active_page = "mi_modulo" %}
{% block title %}Mi Módulo — QMS Salud{% endblock %}
{% block page_title %}Mi Módulo{% endblock %}
{% block topbar_actions %}<a href="/mi-modulo/nuevo" class="btn btn-primary">+ Nuevo</a>{% endblock %}
{% block content %}{% endblock %}
{% block extra_js %}<script></script>{% endblock %}
```

### Available CSS classes (main.css)
**Layout:** `.layout`, `.sidebar`, `.main`, `.page`, `.topbar`  
**Cards:** `.card`, `.card-header`, `.card-title`  
**Grids:** `.grid-2`, `.grid-3`, `.home-grid`, `.stats-grid`  
**Stat cards:** `.stat-card .blue|green|yellow|red|teal|purple`  
**Buttons:** `.btn .btn-primary|secondary|danger|success|sm|icon`  
**Badges:** `.badge .badge-green|yellow|red|blue|orange|purple|teal|gray`  
**Forms:** `.form-group`, `.form-label`, `.form-control`, `.form-row`, `.form-row-3`  
**Tables:** `.table-wrap > table`  
**Alerts:** `.alert .alert-success|danger|warning|info`  
**Progress:** `.progress > .progress-bar.green|yellow|red|blue`  
**Misc:** `.page-header`, `.detail-section-title`, `.empty-state`, `.divider`

### Signature canvas (standard pattern)
```html
<canvas id="firmaCanvas" width="340" height="140"
  style="border:1.5px solid var(--border);border-radius:8px;background:#fff;
  cursor:crosshair;touch-action:none;width:100%;display:block;"></canvas>
<input type="hidden" name="firma_campo" id="firmaInput">
```
Copy the JS from `templates/ambulancias/preoperacional.html` — it handles mouse + touch drawing and serializes to base64 into the hidden input.

### Downloadable reports (HTML)
```python
return Response(content=html, media_type="text/html",
    headers={"Content-Disposition": f"attachment; filename=reporte_{id}.html"})

def get_logo_b64():
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""
```

## User roles
| Role | Access |
|------|--------|
| admin | Full access + user management |
| calidad | Document approval |
| auditor | Audits module |
| gestor | Create/edit in assigned modules |
| consultor | Read-only |

Role is stored on `Usuario.rol`; the `PermisoUsuario` model for granular per-module permissions exists in the DB but is not yet wired to router-level enforcement.

## Adding a new module (checklist)
1. Add models to `models.py`
2. Create `routers/mi_modulo.py`
3. Create `templates/mi_modulo/` with needed templates
4. Import and register router in `main.py`
5. Add sidebar link in `templates/base.html`
6. Add tile in `templates/home.html`
7. Add stats query in the `@app.get("/")` handler in `main.py` if needed
8. Run `python seed.py` if new tables were added

## Environment (.env)
```
SECRET_KEY=qms-salud-secret-key-2024
DATABASE_URL=sqlite:///./qms_salud.db
ACCESS_TOKEN_EXPIRE_MINUTES=480
```
