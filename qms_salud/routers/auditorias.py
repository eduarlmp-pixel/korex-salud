from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_config import templates
from sqlalchemy.orm import Session
from database import get_db
import models, auth
from datetime import datetime

router = APIRouter(prefix="/auditorias", tags=["auditorias"])

@router.get("", response_class=HTMLResponse)
async def lista_auditorias(request: Request, estado: str = "", db: Session = Depends(get_db),
                            current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "auditorias", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    query = db.query(models.Auditoria)
    if estado:
        query = query.filter(models.Auditoria.estado == estado)
    auditorias = query.order_by(models.Auditoria.creado_en.desc()).all()
    return templates.TemplateResponse("auditorias/lista.html", {
        "request": request, "user": current_user,
        "auditorias": auditorias, "filtro_estado": estado,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/nueva", response_class=HTMLResponse)
async def nueva_auditoria_form(request: Request, db: Session = Depends(get_db),
                                current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "auditorias", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    usuarios = db.query(models.Usuario).filter_by(activo=True).all()
    return templates.TemplateResponse("auditorias/form.html", {
        "request": request, "user": current_user, "usuarios": usuarios, "auditoria": None,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/nueva")
async def crear_auditoria(
    request: Request,
    codigo: str = Form(...), titulo: str = Form(...),
    tipo: str = Form("interna"), proceso_auditado: str = Form(...),
    lider_id: int = Form(...), norma_referencia: str = Form(""),
    fecha_inicio: str = Form(""), fecha_fin: str = Form(""),
    objetivo: str = Form(""), alcance: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "auditorias", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    aud = models.Auditoria(
        codigo=codigo, titulo=titulo, tipo=tipo,
        proceso_auditado=proceso_auditado, lider_id=lider_id,
        norma_referencia=norma_referencia, objetivo=objetivo, alcance=alcance,
        fecha_inicio=datetime.fromisoformat(fecha_inicio) if fecha_inicio else None,
        fecha_fin=datetime.fromisoformat(fecha_fin) if fecha_fin else None,
    )
    db.add(aud)
    db.commit()
    return RedirectResponse(url="/auditorias", status_code=302)

@router.get("/{aud_id}", response_class=HTMLResponse)
async def detalle_auditoria(aud_id: int, request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "auditorias", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    aud = db.query(models.Auditoria).filter_by(id=aud_id).first()
    if not aud:
        raise HTTPException(status_code=404)
    hallazgos = db.query(models.Hallazgo).filter_by(auditoria_id=aud_id).all()
    checklists = db.query(models.ChecklistAuditoria).filter_by(auditoria_id=aud_id).all()
    return templates.TemplateResponse("auditorias/detalle.html", {
        "request": request, "user": current_user,
        "auditoria": aud, "hallazgos": hallazgos, "checklists": checklists,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/{aud_id}/hallazgo")
async def agregar_hallazgo(
    aud_id: int,
    tipo: str = Form("observacion"),
    descripcion: str = Form(...),
    proceso: str = Form(""),
    criterio: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    h = models.Hallazgo(
        auditoria_id=aud_id, tipo=tipo, descripcion=descripcion,
        proceso=proceso, criterio=criterio
    )
    db.add(h)
    db.commit()
    return RedirectResponse(url=f"/auditorias/{aud_id}", status_code=302)

@router.post("/{aud_id}/cambiar-estado")
async def cambiar_estado_auditoria(
    aud_id: int, estado: str = Form(...),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    aud = db.query(models.Auditoria).filter_by(id=aud_id).first()
    if aud:
        aud.estado = estado
        db.commit()
    return RedirectResponse(url=f"/auditorias/{aud_id}", status_code=302)
