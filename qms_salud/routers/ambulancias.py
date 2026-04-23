from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import base64, os, json

router = APIRouter(prefix="/ambulancias", tags=["ambulancias"])

ITEMS = [
    ("nivel_aceite","Nivel de aceite"),("nivel_agua","Nivel de agua"),
    ("nivel_combustible","Combustible"),("nivel_liquido_frenos","Líq. de frenos"),
    ("luces_delanteras","Luces delanteras"),("luces_traseras","Luces traseras"),
    ("luces_emergencia","Luces emergencia"),("sirena","Sirena"),
    ("llanta_delantera_der","Llanta del. derecha"),("llanta_delantera_izq","Llanta del. izquierda"),
    ("llanta_trasera_der","Llanta tra. derecha"),("llanta_trasera_izq","Llanta tra. izquierda"),
    ("llanta_repuesto","Llanta de repuesto"),
    ("cinturones","Cinturones de seguridad"),("extintores_amb","Extintores"),
    ("botiquin","Botiquín"),("camilla","Camilla"),("oxigeno","Oxígeno"),
    ("soat","SOAT vigente"),("tecnomecanica","Tecnomecánica"),("tarjeta_operacion","Tarjeta de operación"),
    ("carroceria","Carrocería"),("limpieza","Aseo / limpieza"),
]

@router.get("", response_class=HTMLResponse)
async def lista_ambulancias(request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambulancias", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    ambulancias = db.query(models.Ambulancia).filter_by(activo=True).all()
    data = []
    for a in ambulancias:
        ultimo_pre = db.query(models.Preoperacional).filter_by(
            ambulancia_id=a.id).order_by(models.Preoperacional.fecha.desc()).first()
        data.append({"amb": a, "ultimo": ultimo_pre})
    return templates.TemplateResponse("ambulancias/lista.html", {
        "request": request, "user": current_user, "data": data,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/nueva", response_class=HTMLResponse)
async def nueva_ambulancia_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambulancias", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("ambulancias/form_ambulancia.html", {
        "request": request, "user": current_user, "amb": None,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/nueva")
async def crear_ambulancia(
    request: Request,
    placa: str = Form(...), numero_interno: str = Form(""),
    marca: str = Form(""), modelo: str = Form(""),
    anio: int = Form(2020), tipo: str = Form("TAB"),
    estado: str = Form("activo"),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    a = models.Ambulancia(placa=placa.upper(), numero_interno=numero_interno,
        marca=marca, modelo=modelo, anio=anio, tipo=tipo, estado=estado)
    db.add(a); db.commit()
    return RedirectResponse(url="/ambulancias", status_code=302)

@router.get("/{amb_id}", response_class=HTMLResponse)
async def detalle_ambulancia(amb_id: int, request: Request, db: Session = Depends(get_db),
                              current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambulancias", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    amb = db.query(models.Ambulancia).filter_by(id=amb_id).first()
    conductores = db.query(models.ConductorAmbulancia).filter_by(ambulancia_id=amb_id, activo=True).all()
    preoperacionales = db.query(models.Preoperacional).filter_by(
        ambulancia_id=amb_id).order_by(models.Preoperacional.fecha.desc()).limit(20).all()
    return templates.TemplateResponse("ambulancias/detalle.html", {
        "request": request, "user": current_user,
        "amb": amb, "conductores": conductores,
        "preoperacionales": preoperacionales,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/{amb_id}/conductor")
async def agregar_conductor(
    amb_id: int,
    nombres: str = Form(...), apellidos: str = Form(...),
    documento: str = Form(...), licencia: str = Form(""),
    categoria_licencia: str = Form(""), telefono: str = Form(""),
    email: str = Form(""), vencimiento_licencia: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    c = models.ConductorAmbulancia(
        ambulancia_id=amb_id, nombres=nombres, apellidos=apellidos,
        documento=documento, licencia=licencia, categoria_licencia=categoria_licencia,
        telefono=telefono, email=email,
        vencimiento_licencia=datetime.fromisoformat(vencimiento_licencia) if vencimiento_licencia else None
    )
    db.add(c); db.commit()
    return RedirectResponse(url=f"/ambulancias/{amb_id}", status_code=302)

@router.get("/{amb_id}/preoperacional", response_class=HTMLResponse)
async def nuevo_preoperacional_form(amb_id: int, request: Request, db: Session = Depends(get_db),
                                     current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambulancias", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    amb = db.query(models.Ambulancia).filter_by(id=amb_id).first()
    conductores = db.query(models.ConductorAmbulancia).filter_by(ambulancia_id=amb_id, activo=True).all()
    return templates.TemplateResponse("ambulancias/preoperacional.html", {
        "request": request, "user": current_user,
        "amb": amb, "conductores": conductores, "items": ITEMS,
        "pre": None,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/{amb_id}/preoperacional")
async def crear_preoperacional(
    request: Request, amb_id: int,
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    form = await request.form()
    campos = {k: v for k, v in form.items()}
    firma_b64 = campos.pop("firma_conductor", None)

    pre = models.Preoperacional(
        ambulancia_id=amb_id,
        conductor_id=int(campos.get("conductor_id", 0)) or None,
        turno=campos.get("turno", "manana"),
        kilometraje_inicio=int(campos.get("kilometraje_inicio", 0) or 0),
        observaciones=campos.get("observaciones", ""),
        firma_conductor=firma_b64,
        firmado=bool(firma_b64),
    )
    for campo, _ in ITEMS:
        setattr(pre, campo, campos.get(campo, "ok"))
    db.add(pre); db.commit()
    return RedirectResponse(url=f"/ambulancias/{amb_id}/preoperacional/{pre.id}", status_code=302)

@router.get("/{amb_id}/preoperacional/{pre_id}", response_class=HTMLResponse)
async def ver_preoperacional(amb_id: int, pre_id: int, request: Request,
                              db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambulancias", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    pre  = db.query(models.Preoperacional).filter_by(id=pre_id).first()
    amb  = db.query(models.Ambulancia).filter_by(id=amb_id).first()
    return templates.TemplateResponse("ambulancias/ver_preoperacional.html", {
        "request": request, "user": current_user,
        "pre": pre, "amb": amb, "items": ITEMS,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/{amb_id}/preoperacional/{pre_id}/pdf")
async def pdf_preoperacional(amb_id: int, pre_id: int, db: Session = Depends(get_db),
                              current_user=Depends(auth.get_current_user)):
    pre = db.query(models.Preoperacional).filter_by(id=pre_id).first()
    amb = db.query(models.Ambulancia).filter_by(id=amb_id).first()
    conductor = pre.conductor if pre else None

    # Leer logo en base64
    logo_b64 = ""
    logo_path = "static/img/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    estado_icon = {"ok": "✓", "nok": "✗", "na": "N/A"}

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:10px;margin:0;padding:20px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #1a56a0;padding-bottom:10px;margin-bottom:14px;}}
  .header img{{height:50px;}}
  .header-center{{text-align:center;flex:1;}}
  .header-center h2{{margin:0;font-size:13px;color:#1a56a0;}}
  .header-center p{{margin:2px 0;font-size:9px;color:#555;}}
  .meta-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}}
  .meta-box{{border:1px solid #c8d8e8;border-radius:4px;padding:6px 10px;}}
  .meta-box .label{{font-size:8px;color:#888;text-transform:uppercase;letter-spacing:0.04em;}}
  .meta-box .val{{font-size:11px;font-weight:bold;color:#111;}}
  table{{width:100%;border-collapse:collapse;margin-bottom:12px;}}
  th{{background:#1a56a0;color:#fff;padding:5px 8px;font-size:9px;text-align:left;}}
  td{{padding:4px 8px;border-bottom:1px solid #e0e8f0;font-size:10px;}}
  tr:nth-child(even){{background:#f5f8fc;}}
  .ok{{color:#0e7c45;font-weight:bold;}} .nok{{color:#b91c1c;font-weight:bold;}} .na{{color:#888;}}
  .firma-box{{border:1px solid #c8d8e8;border-radius:6px;padding:10px;text-align:center;margin-top:10px;}}
  .footer{{margin-top:16px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #e0e8f0;padding-top:6px;}}
  .seccion{{font-size:9px;font-weight:bold;background:#e8f0fb;color:#1a56a0;padding:3px 8px;margin:8px 0 4px;border-left:3px solid #1a56a0;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else '<div style="width:80px"></div>'}
  <div class="header-center">
    <h2>PREOPERACIONAL DE AMBULANCIA</h2>
    <p>Control diario de condiciones del vehículo</p>
  </div>
  <div style="text-align:right;font-size:9px;color:#555;">
    <div>Fecha: {pre.fecha.strftime('%d/%m/%Y') if pre else '—'}</div>
    <div>Turno: {pre.turno.upper() if pre else '—'}</div>
  </div>
</div>

<div class="meta-grid">
  <div class="meta-box"><div class="label">Placa</div><div class="val">{amb.placa if amb else '—'}</div></div>
  <div class="meta-box"><div class="label">Tipo</div><div class="val">{amb.tipo if amb else '—'}</div></div>
  <div class="meta-box"><div class="label">Km inicio</div><div class="val">{pre.kilometraje_inicio if pre else 0}</div></div>
  <div class="meta-box"><div class="label">Conductor</div><div class="val">{conductor.nombres + ' ' + conductor.apellidos if conductor else '—'}</div></div>
  <div class="meta-box"><div class="label">Licencia</div><div class="val">{conductor.licencia if conductor else '—'}</div></div>
  <div class="meta-box"><div class="label">Categoría</div><div class="val">{conductor.categoria_licencia if conductor else '—'}</div></div>
</div>

<div class="seccion">ÍTEMS DE INSPECCIÓN</div>
<table>
  <tr><th>Ítem</th><th>Estado</th><th>Ítem</th><th>Estado</th></tr>"""

    items_list = list(ITEMS)
    for i in range(0, len(items_list), 2):
        campo1, label1 = items_list[i]
        val1 = getattr(pre, campo1, "na") if pre else "na"
        cls1 = val1 if val1 in ("ok","nok","na") else "na"
        icn1 = estado_icon.get(val1, "—")
        if i+1 < len(items_list):
            campo2, label2 = items_list[i+1]
            val2 = getattr(pre, campo2, "na") if pre else "na"
            cls2 = val2 if val2 in ("ok","nok","na") else "na"
            icn2 = estado_icon.get(val2, "—")
            html += f'<tr><td>{label1}</td><td class="{cls1}">{icn1}</td><td>{label2}</td><td class="{cls2}">{icn2}</td></tr>'
        else:
            html += f'<tr><td>{label1}</td><td class="{cls1}">{icn1}</td><td></td><td></td></tr>'

    obs = (pre.observaciones or "Sin observaciones") if pre else "—"
    html += f"""</table>
<div class="seccion">OBSERVACIONES</div>
<div style="border:1px solid #c8d8e8;border-radius:4px;padding:8px;min-height:40px;font-size:10px;">{obs}</div>

<div class="firma-box">
  <div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA DEL CONDUCTOR</div>
  {'<img src="' + pre.firma_conductor + '" style="max-height:80px;max-width:240px;">' if pre and pre.firma_conductor else '<div style="height:60px;border-bottom:1px solid #aaa;width:200px;margin:0 auto;"></div>'}
  <div style="font-size:9px;color:#555;margin-top:4px;">{conductor.nombres + ' ' + conductor.apellidos if conductor else 'Conductor'} — C.C. {conductor.documento if conductor else '—'}</div>
</div>

<div class="footer">Documento generado por QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC · Preoperacional N° {pre_id}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
                    headers={"Content-Disposition": f"attachment; filename=preoperacional_{amb.placa}_{pre_id}.html"})
