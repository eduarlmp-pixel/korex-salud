from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from templates_config import templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models, auth

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "dashboard", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)

    # Conteos generales
    total_docs = db.query(models.Documento).count()
    docs_aprobados = db.query(models.Documento).filter_by(estado="aprobado").count()
    docs_borrador = db.query(models.Documento).filter_by(estado="borrador").count()
    docs_revision = db.query(models.Documento).filter_by(estado="revision").count()

    total_auditorias = db.query(models.Auditoria).count()
    aud_cerradas = db.query(models.Auditoria).filter_by(estado="cerrada").count()
    aud_en_curso = db.query(models.Auditoria).filter_by(estado="en_curso").count()
    aud_planificadas = db.query(models.Auditoria).filter_by(estado="planificada").count()

    total_acciones = db.query(models.AccionMejora).count()
    acc_pendientes = db.query(models.AccionMejora).filter_by(estado="pendiente").count()
    acc_en_proceso = db.query(models.AccionMejora).filter_by(estado="en_proceso").count()
    acc_completadas = db.query(models.AccionMejora).filter_by(estado="completada").count()

    total_pqrs = db.query(models.PQRS).count()
    pqrs_abiertas = db.query(models.PQRS).filter_by(estado="abierta").count()
    pqrs_en_gestion = db.query(models.PQRS).filter_by(estado="en_gestion").count()

    riesgos_criticos = db.query(models.Riesgo).filter_by(nivel="critico").count()
    riesgos_altos = db.query(models.Riesgo).filter_by(nivel="alto").count()
    total_riesgos = db.query(models.Riesgo).count()

    total_empleados = db.query(models.Empleado).filter_by(activo=True).count()

    # Indicadores recientes con su última medición
    indicadores = db.query(models.Indicador).filter_by(activo=True).limit(6).all()
    inds_con_datos = []
    for ind in indicadores:
        ultima = db.query(models.MedicionIndicador).filter_by(
            indicador_id=ind.id).order_by(models.MedicionIndicador.fecha_registro.desc()).first()
        if ultima:
            cumple = ind.meta_minima <= ultima.valor <= ind.meta_maxima if ind.meta_minima is not None else True
            inds_con_datos.append({
                "nombre": ind.nombre, "valor": ultima.valor,
                "meta": ind.meta, "unidad": ind.unidad,
                "estado": "cumple" if cumple else "alerta",
                "periodo": ultima.periodo
            })

    # Acciones recientes
    acciones_recientes = db.query(models.AccionMejora).order_by(
        models.AccionMejora.creado_en.desc()).limit(5).all()

    # PQRS recientes
    pqrs_recientes = db.query(models.PQRS).order_by(
        models.PQRS.fecha_registro.desc()).limit(5).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
        "stats": {
            "total_docs": total_docs, "docs_aprobados": docs_aprobados,
            "docs_borrador": docs_borrador, "docs_revision": docs_revision,
            "total_auditorias": total_auditorias, "aud_cerradas": aud_cerradas,
            "aud_en_curso": aud_en_curso, "aud_planificadas": aud_planificadas,
            "total_acciones": total_acciones, "acc_pendientes": acc_pendientes,
            "acc_en_proceso": acc_en_proceso, "acc_completadas": acc_completadas,
            "total_pqrs": total_pqrs, "pqrs_abiertas": pqrs_abiertas,
            "pqrs_en_gestion": pqrs_en_gestion,
            "riesgos_criticos": riesgos_criticos, "riesgos_altos": riesgos_altos,
            "total_riesgos": total_riesgos, "total_empleados": total_empleados,
        },
        "indicadores": inds_con_datos,
        "acciones_recientes": acciones_recientes,
        "pqrs_recientes": pqrs_recientes,
    })
