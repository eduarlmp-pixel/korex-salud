from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from database import engine
from datetime import datetime
import models
from templates_config import templates
from routers.auth_router import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.documentos import router as documentos_router
from routers.auditorias import router as auditorias_router
from routers.mejora import router as mejora_router
from routers.comites import router as comites_router
from routers.ambulancias import router as ambulancias_router
from routers.sst import router as sst_router
from routers.ambiental import router as ambiental_router
from routers.tecnovigilancia import router as tecno_router
from routers.infraestructura import sistemas_router, ambiente_router
from routers.seguridad_paciente import router as sp_router
from routers.usuarios import router as usuarios_router
from routers.perfil import router as perfil_router
from routers.otros import (
    riesgos_router, indicadores_router, talento_router, pqrs_router, flujos_router
)
import os
from dotenv import load_dotenv

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="QMS Salud", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(documentos_router)
app.include_router(auditorias_router)
app.include_router(mejora_router)
app.include_router(comites_router)
app.include_router(ambulancias_router)
app.include_router(sst_router)
app.include_router(ambiental_router)
app.include_router(tecno_router)
app.include_router(sistemas_router)
app.include_router(sp_router)
app.include_router(usuarios_router)
app.include_router(perfil_router)
app.include_router(ambiente_router)
app.include_router(riesgos_router)
app.include_router(indicadores_router)
app.include_router(talento_router)
app.include_router(pqrs_router)
app.include_router(flujos_router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    from database import SessionLocal
    import auth as auth_module
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")
    db = SessionLocal()
    try:
        current_user = await auth_module.get_current_user(request, db)
        if not current_user:
            return RedirectResponse(url="/login")
        stats = {
            "total_docs":        db.query(models.Documento).count(),
            "total_auditorias":  db.query(models.Auditoria).count(),
            "total_acciones":    db.query(models.AccionMejora).count(),
            "total_pqrs":        db.query(models.PQRS).count(),
            "pqrs_abiertas":     db.query(models.PQRS).filter_by(estado="abierta").count(),
            "total_riesgos":     db.query(models.Riesgo).filter_by(activo=True).count(),
            "riesgos_criticos":  db.query(models.Riesgo).filter_by(nivel="critico", activo=True).count(),
            "total_empleados":   db.query(models.Empleado).filter_by(activo=True).count(),
            "total_indicadores": db.query(models.Indicador).filter_by(activo=True).count(),
            "total_flujos":      db.query(models.FlujoTrabajo).filter_by(activo=True).count(),
            "total_comites":     db.query(models.Comite).filter_by(activo=True).count(),
            "total_ambulancias": db.query(models.Ambulancia).filter_by(activo=True).count(),
            "total_rondas": db.query(models.RondaSeguridad).count(),
            "total_equipos_bio": db.query(models.EquipoBiomedico).filter_by(activo=True).count(),
            "total_equipos_sis": db.query(models.EquipoSistemas).filter_by(activo=True).count(),
            "condiciones_inseguras": db.query(models.CondicionInsegura).filter_by(estado="abierta").count(),
            "pendientes_firma": db.query(models.FirmaActa).filter_by(valida=True, firma_imagen=None).count(),
        }
        return templates.TemplateResponse("home.html", {
            "request": request, "user": current_user, "stats": stats
        })
    finally:
        db.close()

@app.get("/login", response_class=HTMLResponse)
async def login_redirect():
    return RedirectResponse(url="/auth/login")
