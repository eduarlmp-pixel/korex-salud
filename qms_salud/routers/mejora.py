from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from templates_config import templates
from sqlalchemy.orm import Session
from database import get_db
import models, auth
from datetime import datetime

router = APIRouter(prefix="/mejora", tags=["mejora"])

@router.get("", response_class=HTMLResponse)
async def lista_acciones(request: Request, estado: str = "", tipo: str = "",
                          db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "mejora", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    query = db.query(models.AccionMejora)
    if estado:
        query = query.filter(models.AccionMejora.estado == estado)
    if tipo:
        query = query.filter(models.AccionMejora.tipo == tipo)
    acciones = query.order_by(models.AccionMejora.creado_en.desc()).all()
    return templates.TemplateResponse("mejora/lista.html", {
        "request": request, "user": current_user,
        "acciones": acciones, "filtros": {"estado": estado, "tipo": tipo},
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/nueva", response_class=HTMLResponse)
async def nueva_accion_form(request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "mejora", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    usuarios = db.query(models.Usuario).filter_by(activo=True).all()
    return templates.TemplateResponse("mejora/form.html", {
        "request": request, "user": current_user, "usuarios": usuarios, "accion": None,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/nueva")
async def crear_accion(
    request: Request,
    codigo: str = Form(...), titulo: str = Form(...),
    descripcion: str = Form(""), tipo: str = Form("correctiva"),
    origen: str = Form("auto"), proceso: str = Form(""),
    causa_raiz: str = Form(""), responsable_id: int = Form(...),
    fecha_limite: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "mejora", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    acc = models.AccionMejora(
        codigo=codigo, titulo=titulo, descripcion=descripcion,
        tipo=tipo, origen=origen, proceso=proceso, causa_raiz=causa_raiz,
        responsable_id=responsable_id,
        fecha_limite=datetime.fromisoformat(fecha_limite) if fecha_limite else None,
    )
    db.add(acc)
    db.commit()
    return RedirectResponse(url="/mejora", status_code=302)

@router.post("/{acc_id}/avance")
async def actualizar_avance(
    acc_id: int, porcentaje_avance: int = Form(...),
    estado: str = Form(...), db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    acc = db.query(models.AccionMejora).filter_by(id=acc_id).first()
    if acc:
        acc.porcentaje_avance = porcentaje_avance
        acc.estado = estado
        if estado == "completada":
            acc.fecha_cierre = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/mejora", status_code=302)
