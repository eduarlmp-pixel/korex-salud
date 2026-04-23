from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import os, shutil, json, base64

router = APIRouter(prefix="/sst", tags=["sst"])
UPLOAD_DIR = "static/uploads/evidencias"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ITEMS_EXTINTOR = [
    "Ubicación señalizada","Acceso libre (sin obstáculos)","Manómetro en zona verde",
    "Sello de seguridad intacto","Etiqueta de inspección vigente","Manguera en buen estado",
    "Tipo correcto para el área","Fecha de recarga vigente",
]
ITEMS_BOTIQUIN = [
    "Gasas estériles","Vendas","Esparadrapo","Guantes desechables",
    "Antiséptico (alcohol/betadine)","Tijeras","Termómetro","Manual de primeros auxilios",
    "Medicamentos básicos (sin vencidos)","Señalización visible",
]

def get_logo_b64():
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

@router.get("", response_class=HTMLResponse)
async def home_sst(request: Request, db: Session = Depends(get_db),
                   current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sst", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    inspecciones = db.query(models.InspeccionSST).order_by(models.InspeccionSST.creado_en.desc()).limit(10).all()
    capacitaciones = db.query(models.CapacitacionSST).order_by(models.CapacitacionSST.fecha.desc()).limit(8).all()
    condiciones = db.query(models.CondicionInsegura).filter_by(estado="abierta").count()
    condiciones_list = db.query(models.CondicionInsegura).order_by(models.CondicionInsegura.fecha_reporte.desc()).limit(10).all()
    return templates.TemplateResponse("sst/home.html", {
        "request": request, "user": current_user,
        "inspecciones": inspecciones, "capacitaciones": capacitaciones,
        "condiciones_abiertas": condiciones, "condiciones_list": condiciones_list,
        "permisos": auth.get_permisos(db, current_user),
    })

# ── INSPECCIONES ──
@router.get("/inspeccion/nueva", response_class=HTMLResponse)
async def nueva_inspeccion_form(request: Request, tipo: str = "extintor",
                                 db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sst", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    items = ITEMS_EXTINTOR if tipo == "extintor" else ITEMS_BOTIQUIN
    return templates.TemplateResponse("sst/form_inspeccion.html", {
        "request": request, "user": current_user, "tipo": tipo, "items": items,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/inspeccion/nueva")
async def crear_inspeccion(
    request: Request,
    tipo: str = Form(...), ubicacion: str = Form(""),
    observaciones: str = Form(""), estado: str = Form("conforme"),
    firma_inspector: str = Form(""),
    evidencia: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    insp = models.InspeccionSST(tipo=tipo, ubicacion=ubicacion,
        observaciones=observaciones, estado=estado, realizado_por=current_user.id)
    # Guardar firma en observaciones extra si modelo no tiene campo firma
    if firma_inspector:
        insp.observaciones = (observaciones or "") + f"||FIRMA||{firma_inspector}"
    db.add(insp); db.flush()

    form = await request.form()
    items_data = [(k, v) for k, v in form.items() if k.startswith("item_")]
    for k, v in items_data:
        nombre = k.replace("item_","").replace("_"," ")
        it = models.ItemInspeccion(inspeccion_id=insp.id, descripcion=nombre, resultado=v)
        db.add(it)

    if evidencia and evidencia.filename:
        fname = f"insp_{insp.id}_{evidencia.filename}".replace(" ","_")
        ruta = f"{UPLOAD_DIR}/{fname}"
        with open(ruta,"wb") as f: shutil.copyfileobj(evidencia.file, f)
        ev = models.EvidenciaInspeccion(inspeccion_id=insp.id,
            archivo_nombre=evidencia.filename, archivo_ruta=ruta)
        db.add(ev)
    db.commit()
    return RedirectResponse(url=f"/sst/inspeccion/{insp.id}/reporte", status_code=302)

@router.get("/inspeccion/{insp_id}/reporte")
async def reporte_inspeccion(insp_id: int, db: Session = Depends(get_db),
                              current_user=Depends(auth.get_current_user)):
    insp = db.query(models.InspeccionSST).filter_by(id=insp_id).first()
    items = db.query(models.ItemInspeccion).filter_by(inspeccion_id=insp_id).all()
    logo_b64 = get_logo_b64()

    # Separar firma de observaciones
    firma_b64 = ""
    obs_limpio = ""
    if insp and insp.observaciones and "||FIRMA||" in insp.observaciones:
        partes = insp.observaciones.split("||FIRMA||")
        obs_limpio = partes[0]
        firma_b64 = partes[1] if len(partes) > 1 else ""
    elif insp:
        obs_limpio = insp.observaciones or ""

    tipo_label = {"extintor":"Extintores","botiquin":"Botiquines","epp":"EPP","general":"General"}
    tipo_color = {"extintor":"#b91c1c","botiquin":"#0e7c45","epp":"#b45309","general":"#1a56a0"}
    t = insp.tipo.value if insp else "general"
    color = tipo_color.get(t, "#1a56a0")

    icon_map = {"ok":"✓","nok":"✗","na":"N/A"}
    rows = ""
    for i in range(0, len(items), 2):
        it1 = items[i]
        v1 = it1.resultado or "na"
        c1 = "#0e7c45" if v1=="ok" else ("#b91c1c" if v1=="nok" else "#888")
        if i+1 < len(items):
            it2 = items[i+1]
            v2 = it2.resultado or "na"
            c2 = "#0e7c45" if v2=="ok" else ("#b91c1c" if v2=="nok" else "#888")
            rows += f'<tr><td>{it1.descripcion}</td><td style="color:{c1};font-weight:bold;">{icon_map.get(v1,"—")}</td><td>{it2.descripcion}</td><td style="color:{c2};font-weight:bold;">{icon_map.get(v2,"—")}</td></tr>'
        else:
            rows += f'<tr><td>{it1.descripcion}</td><td style="color:{c1};font-weight:bold;">{icon_map.get(v1,"—")}</td><td></td><td></td></tr>'

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:11px;padding:24px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {color};padding-bottom:10px;margin-bottom:16px;}}
  .header img{{height:50px;}} .hc{{text-align:center;flex:1;}}
  .hc h2{{margin:0;font-size:14px;color:{color};}} .hc p{{margin:2px 0;font-size:9px;color:#555;}}
  .meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}}
  .box{{border:1px solid #ddd;border-radius:4px;padding:6px 10px;}}
  .box .l{{font-size:8px;color:#888;text-transform:uppercase;}} .box .v{{font-size:12px;font-weight:bold;}}
  .sec{{font-size:9px;font-weight:bold;background:#f0f4f8;color:{color};padding:3px 8px;margin:10px 0 4px;border-left:3px solid {color};}}
  table{{width:100%;border-collapse:collapse;margin-bottom:12px;}}
  th{{background:{color};color:#fff;padding:6px 10px;font-size:10px;text-align:left;}}
  td{{padding:5px 10px;border-bottom:1px solid #eee;font-size:11px;}}
  tr:nth-child(even){{background:#f9fafb;}}
  .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:bold;}}
  .ok{{background:#dcfce7;color:#0e7c45;}} .nok{{background:#fee2e2;color:#b91c1c;}}
  .firma-box{{border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center;margin-top:12px;max-width:300px;}}
  .footer{{margin-top:14px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="hc">
    <h2>INSPECCIÓN DE {tipo_label.get(t,'').upper()}</h2>
    <p>Seguridad y Salud en el Trabajo · {insp.creado_en.strftime('%d/%m/%Y %H:%M') if insp else '—'}</p>
  </div>
  <div style="text-align:right;font-size:9px;color:#555;">
    <div>N° {insp_id}</div>
    <div class="badge {'ok' if insp and insp.estado == 'conforme' else 'nok'}" style="margin-top:4px;">
      {insp.estado.upper() if insp else '—'}
    </div>
  </div>
</div>
<div class="meta">
  <div class="box"><div class="l">Ubicación</div><div class="v">{insp.ubicacion or '—'}</div></div>
  <div class="box"><div class="l">Inspector</div><div class="v">{insp.realizado.nombre + ' ' + insp.realizado.apellido if insp and insp.realizado else '—'}</div></div>
  <div class="box"><div class="l">Fecha</div><div class="v">{insp.creado_en.strftime('%d/%m/%Y') if insp else '—'}</div></div>
</div>
<div class="sec">ÍTEMS INSPECCIONADOS</div>
<table><tr><th>Ítem</th><th>Estado</th><th>Ítem</th><th>Estado</th></tr>{rows}</table>
<div class="sec">OBSERVACIONES</div>
<div style="border:1px solid #ddd;border-radius:4px;padding:8px;min-height:36px;">{obs_limpio or 'Sin observaciones'}</div>
<div class="firma-box">
  <div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA DEL INSPECTOR</div>
  {'<img src="' + firma_b64 + '" style="max-height:70px;max-width:220px;">' if firma_b64 else '<div style="height:50px;border-bottom:1px solid #aaa;width:180px;margin:0 auto;"></div>'}
  <div style="font-size:9px;margin-top:4px;">{insp.realizado.nombre + ' ' + insp.realizado.apellido if insp and insp.realizado else '—'}</div>
</div>
<div class="footer">Reporte de inspección N° {insp_id} · QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=inspeccion_{t}_{insp_id}.html"})

# ── CONDICIONES INSEGURAS ──
@router.get("/condicion/nueva", response_class=HTMLResponse)
async def nueva_condicion_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sst", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("sst/form_condicion.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/condicion/nueva")
async def crear_condicion(
    request: Request,
    descripcion: str = Form(...), area_afectada: str = Form(""),
    ubicacion: str = Form(""), riesgo: str = Form("medio"),
    firma_reportante: str = Form(""),
    evidencia: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    ev_ruta = None
    if evidencia and evidencia.filename:
        fname = f"cond_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{evidencia.filename}".replace(" ","_")
        ev_ruta = f"{UPLOAD_DIR}/{fname}"
        with open(ev_ruta,"wb") as f: shutil.copyfileobj(evidencia.file, f)

    desc_con_firma = descripcion
    if firma_reportante:
        desc_con_firma = descripcion + f"||FIRMA||{firma_reportante}"

    c = models.CondicionInsegura(
        descripcion=desc_con_firma, area_afectada=area_afectada,
        ubicacion=ubicacion, riesgo=riesgo, evidencia_ruta=ev_ruta,
        reportado_por=current_user.id
    )
    db.add(c); db.commit()
    return RedirectResponse(url=f"/sst/condicion/{c.id}/reporte", status_code=302)

@router.get("/condicion/{cond_id}/reporte")
async def reporte_condicion(cond_id: int, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    c = db.query(models.CondicionInsegura).filter_by(id=cond_id).first()
    logo_b64 = get_logo_b64()

    firma_b64 = ""
    desc_limpio = ""
    if c and c.descripcion and "||FIRMA||" in c.descripcion:
        partes = c.descripcion.split("||FIRMA||")
        desc_limpio = partes[0]
        firma_b64 = partes[1] if len(partes) > 1 else ""
    elif c:
        desc_limpio = c.descripcion or ""

    colores = {"bajo":"#0e7c45","medio":"#b45309","alto":"#c2410c","critico":"#b91c1c"}
    col = colores.get(c.riesgo if c else "medio","#b45309")

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:11px;padding:24px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {col};padding-bottom:10px;margin-bottom:16px;}}
  .header img{{height:50px;}} .hc{{text-align:center;flex:1;}}
  .hc h2{{margin:0;font-size:14px;color:{col};}}
  .meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}}
  .box{{border:1px solid #ddd;border-radius:4px;padding:6px 10px;}}
  .box .l{{font-size:8px;color:#888;text-transform:uppercase;}} .box .v{{font-size:12px;font-weight:bold;}}
  .sec{{font-size:9px;font-weight:bold;background:#fff8f0;color:{col};padding:3px 8px;margin:10px 0 4px;border-left:3px solid {col};}}
  .content{{border:1px solid #ddd;border-radius:4px;padding:8px;min-height:40px;}}
  .riesgo{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:bold;background:{col}22;color:{col};border:1px solid {col};}}
  .firma-box{{border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center;margin-top:12px;max-width:300px;}}
  .footer{{margin-top:14px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="hc"><h2>REPORTE DE CONDICIÓN INSEGURA</h2><p>SST · N° {cond_id} · {c.fecha_reporte.strftime('%d/%m/%Y %H:%M') if c else '—'}</p></div>
  <div><span class="riesgo">Riesgo: {(c.riesgo or '').upper()}</span></div>
</div>
<div class="meta">
  <div class="box"><div class="l">Área afectada</div><div class="v">{c.area_afectada or '—'}</div></div>
  <div class="box"><div class="l">Ubicación</div><div class="v">{c.ubicacion or '—'}</div></div>
  <div class="box"><div class="l">Estado</div><div class="v">{c.estado if c else '—'}</div></div>
</div>
<div class="sec">DESCRIPCIÓN DE LA CONDICIÓN</div>
<div class="content">{desc_limpio}</div>
{'<div class="sec">EVIDENCIA</div><div class="content" style="color:#555;">Archivo adjunto registrado en el sistema.</div>' if c and c.evidencia_ruta else ''}
<div class="firma-box">
  <div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA DEL REPORTANTE</div>
  {'<img src="' + firma_b64 + '" style="max-height:70px;max-width:220px;">' if firma_b64 else '<div style="height:50px;border-bottom:1px solid #aaa;width:180px;margin:0 auto;"></div>'}
  <div style="font-size:9px;margin-top:4px;">{c.reportado.nombre + ' ' + c.reportado.apellido if c and c.reportado else '—'}</div>
</div>
<div style="margin-top:14px;padding:10px;background:#fff8f0;border:1px solid {col};border-radius:6px;font-size:11px;">
  <strong>⚠️ ACCIÓN REQUERIDA:</strong> El área <strong>{c.area_afectada or 'involucrada'}</strong> debe tomar acciones correctivas sobre esta condición reportada.
</div>
<div class="footer">Reporte condición insegura N° {cond_id} · QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=condicion_insegura_{cond_id}.html"})

@router.post("/condicion/{cond_id}/accion")
async def registrar_accion(cond_id: int, accion_tomada: str = Form(...),
                            estado: str = Form("cerrada"),
                            db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    c = db.query(models.CondicionInsegura).filter_by(id=cond_id).first()
    if c:
        c.accion_tomada = accion_tomada
        c.estado = estado
        if estado == "cerrada": c.fecha_cierre = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/sst", status_code=302)

# ── CAPACITACIONES ──
@router.get("/capacitacion/nueva", response_class=HTMLResponse)
async def nueva_cap_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sst", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("sst/form_capacitacion.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/capacitacion/nueva")
async def crear_capacitacion(
    request: Request,
    tema: str = Form(...), tipo: str = Form("evaluacion"),
    fecha: str = Form(""), area: str = Form(""), instructor: str = Form(""),
    total_asistentes: int = Form(0),
    certificado: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    cert_ruta = None
    if certificado and certificado.filename:
        fname = f"cap_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{certificado.filename}".replace(" ","_")
        cert_ruta = f"static/uploads/capacitaciones/{fname}"
        os.makedirs("static/uploads/capacitaciones", exist_ok=True)
        with open(cert_ruta,"wb") as f: shutil.copyfileobj(certificado.file, f)
    cap = models.CapacitacionSST(
        tema=tema, tipo=tipo, area=area, instructor=instructor,
        total_asistentes=total_asistentes, certificado_ruta=cert_ruta,
        fecha=datetime.fromisoformat(fecha) if fecha else None,
        creado_por=current_user.id
    )
    db.add(cap); db.flush()
    form = await request.form()
    preguntas = [v for k,v in form.items() if k.startswith("pregunta_")]
    resp_correctas = [v for k,v in form.items() if k.startswith("respuesta_correcta_")]
    for i,preg in enumerate(preguntas):
        if preg.strip():
            rc = resp_correctas[i] if i < len(resp_correctas) else ""
            db.add(models.PreguntaCapacitacion(capacitacion_id=cap.id, pregunta=preg, respuesta_correcta=rc))
    db.commit()
    return RedirectResponse(url=f"/sst/capacitacion/{cap.id}", status_code=302)

@router.get("/capacitacion/{cap_id}", response_class=HTMLResponse)
async def ver_capacitacion(cap_id: int, request: Request, db: Session = Depends(get_db),
                            current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "sst", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    cap = db.query(models.CapacitacionSST).filter_by(id=cap_id).first()
    preguntas = db.query(models.PreguntaCapacitacion).filter_by(capacitacion_id=cap_id).all()
    respuestas = db.query(models.RespuestaCapacitacion).filter_by(capacitacion_id=cap_id).all()
    pct_adherencia = round(sum(r.porcentaje for r in respuestas)/len(respuestas),1) if respuestas else 0
    return templates.TemplateResponse("sst/ver_capacitacion.html", {
        "request": request, "user": current_user,
        "cap": cap, "preguntas": preguntas, "respuestas": respuestas,
        "pct_adherencia": pct_adherencia,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/capacitacion/{cap_id}/respuesta")
async def registrar_respuesta(cap_id: int, request: Request,
    nombre_participante: str = Form(...),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    preguntas = db.query(models.PreguntaCapacitacion).filter_by(capacitacion_id=cap_id).all()
    form = await request.form()
    correctas = 0; resp_json = {}
    for p in preguntas:
        resp = form.get(f"resp_{p.id}","")
        resp_json[str(p.id)] = resp
        if resp.strip().lower() == (p.respuesta_correcta or "").strip().lower():
            correctas += 1
    pct = round((correctas/len(preguntas))*100,1) if preguntas else 0
    db.add(models.RespuestaCapacitacion(
        capacitacion_id=cap_id, nombre_participante=nombre_participante,
        respuestas_json=json.dumps(resp_json), correctas=correctas,
        total=len(preguntas), porcentaje=pct
    ))
    db.commit()
    return RedirectResponse(url=f"/sst/capacitacion/{cap_id}", status_code=302)
