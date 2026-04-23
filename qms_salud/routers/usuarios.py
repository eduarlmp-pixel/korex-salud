from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from passlib.context import CryptContext

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALL_MODULES = [
    ("dashboard",          "Dashboard"),
    ("documentos",         "Documentos"),
    ("auditorias",         "Auditorías"),
    ("mejora",             "Mejora continua"),
    ("indicadores",        "Indicadores"),
    ("riesgos",            "Riesgos"),
    ("comites",            "Comités"),
    ("seguridad-paciente", "Seguridad paciente"),
    ("flujos",             "Flujos de trabajo"),
    ("sst",                "SST"),
    ("ambiental",          "Gestión ambiental"),
    ("ambiente-fisico",    "Ambiente físico"),
    ("tecnovigilancia",    "Tecnovigilancia"),
    ("sistemas",           "Sistemas"),
    ("ambulancias",        "Ambulancias"),
    ("talento",            "Talento humano"),
    ("pqrs",               "PQRS"),
]


def _admin_check(current_user):
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.rol.value != "admin":
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return None


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, db: Session = Depends(get_db),
                current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    usuarios = db.query(models.Usuario).order_by(models.Usuario.nombre).all()
    return templates.TemplateResponse("usuarios/lista.html", {
        "request": request, "user": current_user,
        "usuarios": usuarios,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request, db: Session = Depends(get_db),
                     current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    return templates.TemplateResponse("usuarios/form.html", {
        "request": request, "user": current_user,
        "u": None, "roles": models.RolUsuario,
        "permisos": auth.get_permisos(db, current_user),
        "error": None,
    })


@router.post("/nuevo")
async def nuevo_post(request: Request, db: Session = Depends(get_db),
                     current_user=Depends(auth.get_current_user),
                     nombre: str = Form(...), apellido: str = Form(...),
                     email: str = Form(...), password: str = Form(...),
                     rol: str = Form(...), cargo: str = Form(""),
                     area: str = Form("")):
    redir = _admin_check(current_user)
    if redir:
        return redir
    if db.query(models.Usuario).filter_by(email=email).first():
        return templates.TemplateResponse("usuarios/form.html", {
            "request": request, "user": current_user,
            "u": None, "roles": models.RolUsuario,
            "permisos": auth.get_permisos(db, current_user),
            "error": "Ya existe un usuario con ese correo.",
        })
    db.add(models.Usuario(
        nombre=nombre, apellido=apellido, email=email,
        hashed_password=pwd_context.hash(password),
        rol=models.RolUsuario(rol), cargo=cargo, area=area,
    ))
    db.commit()
    return RedirectResponse(url="/usuarios", status_code=302)


@router.get("/{id}/editar", response_class=HTMLResponse)
async def editar_form(id: int, request: Request, db: Session = Depends(get_db),
                      current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    u = db.query(models.Usuario).get(id)
    if not u:
        return RedirectResponse(url="/usuarios")
    return templates.TemplateResponse("usuarios/form.html", {
        "request": request, "user": current_user,
        "u": u, "roles": models.RolUsuario,
        "permisos": auth.get_permisos(db, current_user),
        "error": None,
    })


@router.post("/{id}/editar")
async def editar_post(id: int, request: Request, db: Session = Depends(get_db),
                      current_user=Depends(auth.get_current_user),
                      nombre: str = Form(...), apellido: str = Form(...),
                      email: str = Form(...), rol: str = Form(...),
                      cargo: str = Form(""), area: str = Form(""),
                      activo: str = Form(""), password: str = Form("")):
    redir = _admin_check(current_user)
    if redir:
        return redir
    u = db.query(models.Usuario).get(id)
    if not u:
        return RedirectResponse(url="/usuarios")
    u.nombre = nombre
    u.apellido = apellido
    u.email = email
    u.rol = models.RolUsuario(rol)
    u.cargo = cargo
    u.area = area
    u.activo = activo == "on"
    if password.strip():
        u.hashed_password = pwd_context.hash(password.strip())
    db.commit()
    return RedirectResponse(url="/usuarios", status_code=302)


@router.post("/{id}/eliminar")
async def eliminar(id: int, db: Session = Depends(get_db),
                   current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    if id == current_user.id:
        return RedirectResponse(url="/usuarios", status_code=302)
    u = db.query(models.Usuario).get(id)
    if u:
        db.query(models.PermisoUsuario).filter_by(usuario_id=id).delete()
        db.delete(u)
        db.commit()
    return RedirectResponse(url="/usuarios", status_code=302)


@router.get("/{id}/permisos", response_class=HTMLResponse)
async def permisos_form(id: int, request: Request, db: Session = Depends(get_db),
                        current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    u = db.query(models.Usuario).get(id)
    if not u:
        return RedirectResponse(url="/usuarios")
    registros = db.query(models.PermisoUsuario).filter_by(usuario_id=id).all()
    permisos_map = {p.modulo: p for p in registros}
    return templates.TemplateResponse("usuarios/permisos.html", {
        "request": request, "user": current_user,
        "u": u, "modulos": ALL_MODULES,
        "permisos_map": permisos_map,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.post("/{id}/permisos")
async def permisos_post(id: int, request: Request, db: Session = Depends(get_db),
                        current_user=Depends(auth.get_current_user)):
    redir = _admin_check(current_user)
    if redir:
        return redir
    u = db.query(models.Usuario).get(id)
    if not u:
        return RedirectResponse(url="/usuarios")
    form = await request.form()
    db.query(models.PermisoUsuario).filter_by(usuario_id=id).delete()
    for (modulo, _) in ALL_MODULES:
        if form.get(f"{modulo}_ver"):
            db.add(models.PermisoUsuario(
                usuario_id=id, modulo=modulo,
                puede_ver=True,
                puede_crear=bool(form.get(f"{modulo}_crear")),
                puede_editar=bool(form.get(f"{modulo}_editar")),
                puede_aprobar=bool(form.get(f"{modulo}_aprobar")),
                puede_eliminar=bool(form.get(f"{modulo}_eliminar")),
            ))
    db.commit()
    return RedirectResponse(url="/usuarios", status_code=302)
