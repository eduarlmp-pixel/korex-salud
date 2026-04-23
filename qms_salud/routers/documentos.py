from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from templates_config import templates
from sqlalchemy.orm import Session
from database import get_db
import models, auth
from datetime import datetime
import os, shutil, uuid

router = APIRouter(prefix="/documentos", tags=["documentos"])

UPLOAD_DIR = "static/uploads/documentos"
TIPOS_PERMITIDOS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".odt", ".ods", ".odp", ".txt", ".rtf",
}
ETAPAS = [
    ("calidad",           "Calidad"),
    ("planeacion",        "Planeación"),
    ("auditor_medico",    "Auditor Médico"),
    ("juridica",          "Jurídica"),
    ("gerencia",          "Gerencia"),
    ("subgerencia_admin", "Subgerencia Administrativa"),
    ("cientifica",        "Subgerencia Científica"),
]


def _guardar_archivo(archivo: UploadFile, doc_id: int) -> tuple[str, str]:
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in TIPOS_PERMITIDOS:
        return None, None
    carpeta = os.path.join(UPLOAD_DIR, str(doc_id))
    os.makedirs(carpeta, exist_ok=True)
    nombre_unico = f"{uuid.uuid4().hex}{ext}"
    ruta = os.path.join(carpeta, nombre_unico)
    with open(ruta, "wb") as f:
        shutil.copyfileobj(archivo.file, f)
    return ruta.replace("\\", "/"), archivo.filename


@router.get("", response_class=HTMLResponse)
async def lista_documentos(request: Request, q: str = "", estado: str = "", categoria: str = "",
                            db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    query = db.query(models.Documento)
    if q:
        query = query.filter(models.Documento.titulo.ilike(f"%{q}%") | models.Documento.codigo.ilike(f"%{q}%"))
    if estado:
        query = query.filter(models.Documento.estado == estado)
    if categoria:
        query = query.filter(models.Documento.categoria_id == int(categoria))
    documentos = query.order_by(models.Documento.fecha_creacion.desc()).all()
    categorias = db.query(models.CategoriaDoc).all()

    # Documentos pendientes de validación para el usuario actual
    pendientes_validacion = db.query(models.ValidacionDoc).filter(
        models.ValidacionDoc.estado == "pendiente",
        models.ValidacionDoc.usuario_id == current_user.id,
    ).count()

    return templates.TemplateResponse("documentos/lista.html", {
        "request": request, "user": current_user,
        "documentos": documentos, "categorias": categorias,
        "filtros": {"q": q, "estado": estado, "categoria": categoria},
        "pendientes_validacion": pendientes_validacion,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_doc_form(request: Request, db: Session = Depends(get_db),
                          current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    categorias = db.query(models.CategoriaDoc).all()
    usuarios = db.query(models.Usuario).filter_by(activo=True).all()
    return templates.TemplateResponse("documentos/form.html", {
        "request": request, "user": current_user,
        "categorias": categorias, "usuarios": usuarios, "doc": None,
        "etapas": ETAPAS,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.post("/nuevo")
async def crear_documento(
    request: Request,
    codigo: str = Form(...), titulo: str = Form(...),
    descripcion: str = Form(""), version: str = Form("1.0"),
    estado: str = Form("borrador"), categoria_id: int = Form(...),
    aprobador_id: str = Form(""), tags: str = Form(""),
    archivo: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)

    doc = models.Documento(
        codigo=codigo, titulo=titulo, descripcion=descripcion,
        version=version, estado=estado, categoria_id=categoria_id,
        creador_id=current_user.id,
        aprobador_id=int(aprobador_id) if aprobador_id else None,
        tags=tags,
    )
    db.add(doc)
    db.flush()

    if archivo and archivo.filename:
        ruta, nombre = _guardar_archivo(archivo, doc.id)
        if ruta:
            doc.ruta_archivo = ruta
            doc.nombre_archivo = nombre

    # Crear registros de validación para etapas seleccionadas
    form_data = await request.form()
    etapas_sel = form_data.getlist("etapas")
    for orden, (clave, _) in enumerate(ETAPAS):
        if clave in etapas_sel:
            uid_str = form_data.get(f"validador_{clave}", "")
            uid = int(uid_str) if uid_str else None
            db.add(models.ValidacionDoc(
                documento_id=doc.id, etapa=clave, orden=orden,
                usuario_id=uid, estado="pendiente",
            ))
        if estado == "revision" and etapas_sel:
            doc.estado = models.EstadoDoc.revision

    db.commit()
    return RedirectResponse(url=f"/documentos/{doc.id}", status_code=302)


@router.get("/{doc_id}", response_class=HTMLResponse)
async def detalle_documento(doc_id: int, request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    doc.visualizaciones += 1
    db.commit()
    versiones = db.query(models.VersionDoc).filter_by(documento_id=doc_id).order_by(models.VersionDoc.creado_en.desc()).all()
    validaciones = db.query(models.ValidacionDoc).filter_by(documento_id=doc_id).order_by(models.ValidacionDoc.orden).all()
    mi_validacion = next((v for v in validaciones if v.usuario_id == current_user.id and v.estado == "pendiente"), None)
    usuarios = db.query(models.Usuario).filter_by(activo=True).all()
    etapas_dict = dict(ETAPAS)
    return templates.TemplateResponse("documentos/detalle.html", {
        "request": request, "user": current_user, "doc": doc,
        "versiones": versiones, "validaciones": validaciones,
        "mi_validacion": mi_validacion,
        "etapas_dict": etapas_dict, "etapas": ETAPAS,
        "usuarios": usuarios,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.get("/{doc_id}/descargar")
async def descargar_documento(doc_id: int, db: Session = Depends(get_db),
                               current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    if not doc or not doc.ruta_archivo or not os.path.exists(doc.ruta_archivo):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    doc.descargas += 1
    db.commit()
    return FileResponse(
        path=doc.ruta_archivo,
        filename=doc.nombre_archivo or os.path.basename(doc.ruta_archivo),
        media_type="application/octet-stream",
    )


@router.post("/{doc_id}/enviar-revision")
async def enviar_revision(doc_id: int, request: Request,
                           db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    if not doc:
        return RedirectResponse(url="/documentos", status_code=302)

    form_data = await request.form()
    etapas_sel = form_data.getlist("etapas")

    # Eliminar validaciones anteriores pendientes y crear las nuevas
    db.query(models.ValidacionDoc).filter_by(documento_id=doc_id, estado="pendiente").delete()

    for orden, (clave, _) in enumerate(ETAPAS):
        if clave in etapas_sel:
            uid_str = form_data.get(f"validador_{clave}", "")
            uid = int(uid_str) if uid_str else None
            db.add(models.ValidacionDoc(
                documento_id=doc_id, etapa=clave, orden=orden,
                usuario_id=uid, estado="pendiente",
            ))

    doc.estado = models.EstadoDoc.revision
    db.commit()
    return RedirectResponse(url=f"/documentos/{doc_id}", status_code=302)


@router.post("/{doc_id}/validar")
async def validar_documento(doc_id: int, validacion_id: int = Form(...),
                              decision: str = Form(...), comentario: str = Form(""),
                              db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    val = db.query(models.ValidacionDoc).filter_by(id=validacion_id, documento_id=doc_id).first()
    if val:
        val.estado = decision  # "aprobado" o "rechazado"
        val.comentario = comentario
        val.fecha_validacion = datetime.utcnow()
        val.usuario_id = current_user.id
        db.flush()

        doc = db.query(models.Documento).filter_by(id=doc_id).first()
        if decision == "rechazado":
            doc.estado = models.EstadoDoc.borrador
        else:
            # Si todas las validaciones requeridas están aprobadas → aprobar
            pendientes = db.query(models.ValidacionDoc).filter_by(
                documento_id=doc_id, estado="pendiente").count()
            rechazadas = db.query(models.ValidacionDoc).filter_by(
                documento_id=doc_id, estado="rechazado").count()
            if pendientes == 0 and rechazadas == 0:
                doc.estado = models.EstadoDoc.aprobado
                doc.fecha_aprobacion = datetime.utcnow()
        db.commit()
    return RedirectResponse(url=f"/documentos/{doc_id}", status_code=302)


@router.post("/{doc_id}/aprobar")
async def aprobar_documento(doc_id: int, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_aprobar"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    if doc:
        doc.estado = models.EstadoDoc.aprobado
        doc.fecha_aprobacion = datetime.utcnow()
        db.commit()
    return RedirectResponse(url=f"/documentos/{doc_id}", status_code=302)


@router.get("/{doc_id}/editar", response_class=HTMLResponse)
async def editar_doc_form(doc_id: int, request: Request, db: Session = Depends(get_db),
                           current_user=Depends(auth.get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_editar"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    categorias = db.query(models.CategoriaDoc).all()
    usuarios = db.query(models.Usuario).filter_by(activo=True).all()
    return templates.TemplateResponse("documentos/form.html", {
        "request": request, "user": current_user,
        "doc": doc, "categorias": categorias, "usuarios": usuarios,
        "etapas": ETAPAS,
        "permisos": auth.get_permisos(db, current_user),
    })


@router.post("/{doc_id}/editar")
async def editar_documento(
    request: Request, doc_id: int,
    codigo: str = Form(...), titulo: str = Form(...),
    descripcion: str = Form(""), version: str = Form("1.0"),
    estado: str = Form("borrador"), categoria_id: int = Form(...),
    aprobador_id: str = Form(""), tags: str = Form(""),
    archivo: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "documentos", "puede_editar"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    doc = db.query(models.Documento).filter_by(id=doc_id).first()
    if doc:
        # Guardar versión anterior si cambia la versión
        if doc.version != version and doc.ruta_archivo:
            db.add(models.VersionDoc(
                documento_id=doc_id, version=doc.version,
                cambios=f"Actualizado a v{version}",
                ruta_archivo=doc.ruta_archivo,
                creado_por=current_user.id,
            ))
        doc.codigo = codigo
        doc.titulo = titulo
        doc.descripcion = descripcion
        doc.version = version
        doc.estado = estado
        doc.categoria_id = categoria_id
        doc.aprobador_id = int(aprobador_id) if aprobador_id else None
        doc.tags = tags
        if estado == "aprobado" and not doc.fecha_aprobacion:
            doc.fecha_aprobacion = datetime.utcnow()

        if archivo and archivo.filename:
            ruta, nombre = _guardar_archivo(archivo, doc_id)
            if ruta:
                doc.ruta_archivo = ruta
                doc.nombre_archivo = nombre
        db.commit()
    return RedirectResponse(url=f"/documentos/{doc_id}", status_code=302)
