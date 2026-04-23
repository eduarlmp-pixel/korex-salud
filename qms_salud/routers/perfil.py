from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
import base64

router = APIRouter(prefix="/perfil", tags=["perfil"])


@router.get("", response_class=HTMLResponse)
async def ver_perfil(request: Request, db: Session = Depends(get_db),
                     current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")

    actas_recientes = db.query(models.ActaComite).order_by(
        models.ActaComite.fecha.desc()).limit(10).all()

    # Firmas pendientes del usuario (para badge en base.html)
    nombre_usuario = f"{current_user.nombre} {current_user.apellido}".strip()
    pendientes_firma = db.query(models.FirmaActa).filter(
        models.FirmaActa.nombre.ilike(f"%{nombre_usuario}%"),
        models.FirmaActa.firma_imagen.is_(None)
    ).count()

    return templates.TemplateResponse("perfil/index.html", {
        "request": request, "user": current_user,
        "actas_recientes": actas_recientes,
        "pendientes_firma": pendientes_firma,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.post("/actualizar")
async def actualizar_perfil(
    request: Request,
    nombre: str = Form(...), apellido: str = Form(...),
    cargo: str = Form(""), area: str = Form(""),
    nueva_password: str = Form(""),
    firma_archivo: UploadFile = File(None),
    firma_pad: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    current_user.nombre = nombre
    current_user.apellido = apellido
    current_user.cargo = cargo
    if nueva_password.strip():
        current_user.hashed_password = auth.get_password_hash(nueva_password)
    if firma_archivo and firma_archivo.filename:
        contenido = await firma_archivo.read()
        ext = firma_archivo.filename.split(".")[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        b64 = base64.b64encode(contenido).decode()
        current_user.firma_imagen = f"data:{mime};base64,{b64}"
    elif firma_pad.strip():
        current_user.firma_imagen = firma_pad
    db.commit()
    return RedirectResponse(url="/perfil?ok=1", status_code=302)


@router.post("/borrar-firma")
async def borrar_firma(db: Session = Depends(get_db),
                       current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    current_user.firma_imagen = None
    db.commit()
    return RedirectResponse(url="/perfil", status_code=302)


@router.get("/mi-firma")
async def obtener_firma(db: Session = Depends(get_db),
                        current_user=Depends(auth.get_current_user)):
    if not current_user:
        return JSONResponse({"firma": None})
    return JSONResponse({"firma": current_user.firma_imagen})
