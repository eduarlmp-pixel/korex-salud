from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import os, base64, shutil

# ─── SISTEMAS ────────────────────────────────────────────────────────────────
sistemas_router = APIRouter(prefix="/sistemas", tags=["sistemas"])
UPLOAD_MANT = "static/uploads/mantenimientos"
os.makedirs(UPLOAD_MANT, exist_ok=True)

@sistemas_router.get("", response_class=HTMLResponse)
async def home_sistemas(request: Request, db: Session = Depends(get_db),
                         current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sistemas", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    equipos = db.query(models.EquipoSistemas).filter_by(activo=True).all()
    mantenimientos = db.query(models.MantenimientoSistemas).order_by(
        models.MantenimientoSistemas.creado_en.desc()).limit(10).all()
    return templates.TemplateResponse("sistemas/home.html", {
        "request": request, "user": current_user,
        "equipos": equipos, "mantenimientos": mantenimientos,
        "permisos": auth.get_permisos(db, current_user),
    })

@sistemas_router.get("/nuevo-equipo", response_class=HTMLResponse)
async def nuevo_equipo_sis_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sistemas", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("sistemas/form_equipo.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@sistemas_router.post("/nuevo-equipo")
async def crear_equipo_sis(
    nombre: str = Form(...), tipo: str = Form("desktop"),
    marca: str = Form(""), modelo: str = Form(""), serie: str = Form(""),
    area: str = Form(""), usuario_asignado: str = Form(""),
    ip: str = Form(""), so: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    eq = models.EquipoSistemas(nombre=nombre, tipo=tipo, marca=marca, modelo=modelo,
        serie=serie, area=area, usuario_asignado=usuario_asignado, ip=ip, so=so)
    db.add(eq); db.commit()
    return RedirectResponse(url="/sistemas", status_code=302)

@sistemas_router.get("/equipo/{eq_id}/mantenimiento", response_class=HTMLResponse)
async def nuevo_mant_sis_form(eq_id: int, request: Request, db: Session = Depends(get_db),
                               current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sistemas", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    eq = db.query(models.EquipoSistemas).filter_by(id=eq_id).first()
    return templates.TemplateResponse("sistemas/form_mantenimiento.html", {
        "request": request, "user": current_user, "eq": eq,
        "permisos": auth.get_permisos(db, current_user),
    })

@sistemas_router.post("/equipo/{eq_id}/mantenimiento")
async def crear_mant_sis(request: Request, eq_id: int,
                          db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    form = await request.form()
    m = models.MantenimientoSistemas(
        equipo_id=eq_id, tipo=form.get("tipo","preventivo"),
        tecnico=form.get("tecnico",""), descripcion=form.get("descripcion",""),
        actividades=form.get("actividades",""), observaciones=form.get("observaciones",""),
        firma_tecnico=form.get("firma_tecnico",""),
        firmado_tecnico=bool(form.get("firma_tecnico","")),
        realizado_por=current_user.id
    )
    db.add(m); db.commit()
    return RedirectResponse(url=f"/sistemas/mantenimiento/{m.id}/firmar-usuario", status_code=302)

@sistemas_router.get("/mantenimiento/{mant_id}/firmar-usuario", response_class=HTMLResponse)
async def firmar_usuario_form(mant_id: int, request: Request, db: Session = Depends(get_db),
                               current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sistemas", "puede_editar"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    m = db.query(models.MantenimientoSistemas).filter_by(id=mant_id).first()
    return templates.TemplateResponse("sistemas/firmar_usuario.html", {
        "request": request, "user": current_user, "m": m,
        "permisos": auth.get_permisos(db, current_user),
    })

@sistemas_router.post("/mantenimiento/{mant_id}/firmar-usuario")
async def firmar_usuario(mant_id: int, firma_usuario: str = Form(""),
                          db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    m = db.query(models.MantenimientoSistemas).filter_by(id=mant_id).first()
    if m:
        m.firma_usuario = firma_usuario
        m.firmado_usuario = bool(firma_usuario)
        db.commit()
    return RedirectResponse(url=f"/sistemas/mantenimiento/{mant_id}/reporte", status_code=302)

@sistemas_router.get("/mantenimiento/{mant_id}/reporte")
async def reporte_sistemas(mant_id: int, db: Session = Depends(get_db),
                            current_user=Depends(auth.get_current_user)):
    m  = db.query(models.MantenimientoSistemas).filter_by(id=mant_id).first()
    eq = m.equipo if m else None
    logo_b64 = ""
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f: logo_b64 = base64.b64encode(f.read()).decode()

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:11px;padding:24px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #1a56a0;padding-bottom:10px;margin-bottom:16px;}}
  .header img{{height:50px;}} .header-c{{text-align:center;flex:1;}}
  .header-c h2{{margin:0;font-size:14px;color:#1a56a0;}}
  .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}}
  .box{{border:1px solid #ddd;border-radius:5px;padding:7px 10px;}}
  .box .lbl{{font-size:8px;color:#888;text-transform:uppercase;}} .box .val{{font-size:12px;font-weight:bold;}}
  .section{{font-size:9px;font-weight:bold;background:#e8f0fb;color:#1a56a0;padding:3px 8px;margin:10px 0 4px;border-left:3px solid #1a56a0;}}
  .content{{border:1px solid #ddd;border-radius:4px;padding:8px;min-height:36px;font-size:11px;}}
  .firmas{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px;}}
  .firma-box{{border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center;}}
  .footer{{margin-top:14px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="header-c"><h2>REPORTE DE MANTENIMIENTO — SISTEMAS</h2><p>{m.fecha.strftime('%d/%m/%Y') if m else '—'}</p></div>
</div>
<div class="grid">
  <div class="box"><div class="lbl">Equipo</div><div class="val">{eq.nombre if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Tipo</div><div class="val">{eq.tipo if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Área</div><div class="val">{eq.area if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Usuario asignado</div><div class="val">{eq.usuario_asignado if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Técnico</div><div class="val">{m.tecnico if m else '—'}</div></div>
  <div class="box"><div class="lbl">Tipo mant.</div><div class="val">{m.tipo if m else '—'}</div></div>
</div>
<div class="section">DESCRIPCIÓN</div><div class="content">{(m.descripcion or '—') if m else '—'}</div>
<div class="section">ACTIVIDADES REALIZADAS</div><div class="content">{(m.actividades or '—') if m else '—'}</div>
<div class="section">OBSERVACIONES</div><div class="content">{(m.observaciones or '—') if m else '—'}</div>
<div class="firmas">
  <div class="firma-box"><div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA TÉCNICO</div>
    {'<img src="' + m.firma_tecnico + '" style="max-height:70px;max-width:180px;">' if m and m.firma_tecnico else '<div style="height:50px;border-bottom:1px solid #aaa;width:140px;margin:0 auto;"></div>'}
    <div style="font-size:9px;margin-top:4px;">{m.tecnico if m else '—'}</div>
  </div>
  <div class="firma-box"><div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA USUARIO DEL EQUIPO</div>
    {'<img src="' + m.firma_usuario + '" style="max-height:70px;max-width:180px;">' if m and m.firma_usuario else '<div style="height:50px;border-bottom:1px solid #aaa;width:140px;margin:0 auto;"></div>'}
    <div style="font-size:9px;margin-top:4px;">{eq.usuario_asignado if eq else '—'}</div>
  </div>
</div>
<div class="footer">Reporte N° {mant_id} · QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=mant_sistemas_{mant_id}.html"})

# ─── AMBIENTE FÍSICO ─────────────────────────────────────────────────────────
ambiente_router = APIRouter(prefix="/ambiente-fisico", tags=["ambiente_fisico"])
UPLOAD_AMB = "static/uploads/evidencias"

@ambiente_router.get("", response_class=HTMLResponse)
async def home_ambiente(request: Request, db: Session = Depends(get_db),
                         current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambiente-fisico", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    mantenimientos = db.query(models.MantenimientoAmbiente).order_by(
        models.MantenimientoAmbiente.fecha_programada.desc()).all()
    return templates.TemplateResponse("ambiente_fisico/home.html", {
        "request": request, "user": current_user, "mantenimientos": mantenimientos,
        "permisos": auth.get_permisos(db, current_user),
    })

@ambiente_router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_mant_amb_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambiente-fisico", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("ambiente_fisico/form.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@ambiente_router.post("/nuevo")
async def crear_mant_amb(
    area: str = Form(...), tipo_trabajo: str = Form(""),
    descripcion: str = Form(""), fecha_programada: str = Form(""),
    responsable: str = Form(""), contratista: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    m = models.MantenimientoAmbiente(
        area=area, tipo_trabajo=tipo_trabajo, descripcion=descripcion,
        responsable=responsable, contratista=contratista,
        fecha_programada=datetime.fromisoformat(fecha_programada) if fecha_programada else None,
        creado_por=current_user.id
    )
    db.add(m); db.commit()
    return RedirectResponse(url="/ambiente-fisico", status_code=302)

@ambiente_router.post("/{mant_id}/evidencia")
async def subir_evidencia(mant_id: int, descripcion: str = Form(""),
                           archivo: UploadFile = File(None),
                           db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if archivo and archivo.filename:
        fname = f"amb_{mant_id}_{archivo.filename}".replace(" ","_")
        ruta = f"{UPLOAD_AMB}/{fname}"
        with open(ruta, "wb") as f: shutil.copyfileobj(archivo.file, f)
        ev = models.EvidenciaAmbiente(mantenimiento_id=mant_id, archivo_nombre=archivo.filename,
            archivo_ruta=ruta, descripcion=descripcion)
        db.add(ev); db.commit()
    return RedirectResponse(url="/ambiente-fisico", status_code=302)

@ambiente_router.post("/{mant_id}/estado")
async def cambiar_estado_amb(mant_id: int, estado: str = Form(...),
                              fecha_ejecucion: str = Form(""),
                              db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    m = db.query(models.MantenimientoAmbiente).filter_by(id=mant_id).first()
    if m:
        m.estado = estado
        if fecha_ejecucion: m.fecha_ejecucion = datetime.fromisoformat(fecha_ejecucion)
        db.commit()
    return RedirectResponse(url="/ambiente-fisico", status_code=302)

@ambiente_router.get("/{mant_id}/pdf")
async def pdf_ambiente(mant_id: int, db: Session = Depends(get_db),
                        current_user=Depends(auth.get_current_user)):
    m = db.query(models.MantenimientoAmbiente).filter_by(id=mant_id).first()
    logo_b64 = ""
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f: logo_b64 = base64.b64encode(f.read()).decode()

    evidencias_html = ""
    if m and m.evidencias:
        for ev in m.evidencias:
            evidencias_html += f"<li>{ev.archivo_nombre} — {ev.descripcion or ''}</li>"

    estado_color = {"programado":"#1a56a0","en_ejecucion":"#b45309","completado":"#0e7c45"}
    col = estado_color.get(m.estado if m else "programado","#1a56a0")

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:11px;padding:24px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {col};padding-bottom:10px;margin-bottom:16px;}}
  .header img{{height:50px;}} .hc{{text-align:center;flex:1;}}
  .hc h2{{margin:0;font-size:14px;color:{col};}}
  .meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}}
  .box{{border:1px solid #ddd;border-radius:4px;padding:6px 10px;}}
  .box .l{{font-size:8px;color:#888;text-transform:uppercase;}} .box .v{{font-size:12px;font-weight:bold;}}
  .sec{{font-size:9px;font-weight:bold;background:#e8f0fb;color:{col};padding:3px 8px;margin:10px 0 4px;border-left:3px solid {col};}}
  .content{{border:1px solid #ddd;border-radius:4px;padding:8px;min-height:36px;}}
  .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:bold;background:{col}22;color:{col};border:1px solid {col};}}
  .footer{{margin-top:14px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="hc"><h2>REGISTRO DE MANTENIMIENTO — AMBIENTE FÍSICO</h2><p>{m.fecha_programada.strftime('%d/%m/%Y') if m and m.fecha_programada else '—'}</p></div>
  <div><span class="badge">{(m.estado or '').upper()}</span></div>
</div>
<div class="meta">
  <div class="box"><div class="l">Área</div><div class="v">{m.area if m else '—'}</div></div>
  <div class="box"><div class="l">Tipo de trabajo</div><div class="v">{m.tipo_trabajo or '—'}</div></div>
  <div class="box"><div class="l">Responsable</div><div class="v">{m.responsable or '—'}</div></div>
  <div class="box"><div class="l">Contratista</div><div class="v">{m.contratista or '—'}</div></div>
  <div class="box"><div class="l">Fecha programada</div><div class="v">{m.fecha_programada.strftime('%d/%m/%Y') if m and m.fecha_programada else '—'}</div></div>
  <div class="box"><div class="l">Fecha ejecución</div><div class="v">{m.fecha_ejecucion.strftime('%d/%m/%Y') if m and m.fecha_ejecucion else 'Pendiente'}</div></div>
</div>
<div class="sec">DESCRIPCIÓN DEL TRABAJO</div>
<div class="content">{(m.descripcion or '—') if m else '—'}</div>
{'<div class="sec">EVIDENCIAS</div><div class="content"><ul>' + evidencias_html + '</ul></div>' if evidencias_html else ''}
<div class="footer">Mantenimiento N° {mant_id} · Ambiente Físico · QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=mant_ambiente_{mant_id}.html"})
