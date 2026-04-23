from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import os, base64, uuid, shutil, qrcode
from io import BytesIO

router = APIRouter(prefix="/tecnovigilancia", tags=["tecnovigilancia"])
UPLOAD_DIR = "static/uploads/mantenimientos"
QR_DIR = "static/uploads/qr"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

def gen_qr(codigo: str, base_url: str = "http://localhost:8000") -> str:
    url = f"{base_url}/tecnovigilancia/equipo/{codigo}"
    try:
        import qrcode as qr_mod
        qr = qr_mod.QRCode(box_size=8, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

@router.get("", response_class=HTMLResponse)
async def home_tecno(request: Request, db: Session = Depends(get_db),
                      current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "tecnovigilancia", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    equipos = db.query(models.EquipoBiomedico).filter_by(activo=True).all()
    return templates.TemplateResponse("tecnovigilancia/lista.html", {
        "request": request, "user": current_user, "equipos": equipos,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/nuevo-equipo", response_class=HTMLResponse)
async def nuevo_equipo_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "tecnovigilancia", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("tecnovigilancia/form_equipo.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/nuevo-equipo")
async def crear_equipo(
    nombre: str = Form(...), marca: str = Form(""), modelo: str = Form(""),
    serie: str = Form(""), area: str = Form(""), ubicacion: str = Form(""),
    estado: str = Form("operativo"),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    codigo = f"EQ-{uuid.uuid4().hex[:8].upper()}"
    eq = models.EquipoBiomedico(codigo_qr=codigo, nombre=nombre, marca=marca,
        modelo=modelo, serie=serie, area=area, ubicacion=ubicacion, estado=estado)
    db.add(eq); db.commit()
    return RedirectResponse(url=f"/tecnovigilancia/equipo-id/{eq.id}", status_code=302)

@router.get("/equipo-id/{equipo_id}", response_class=HTMLResponse)
async def detalle_equipo_id(equipo_id: int, request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    eq = db.query(models.EquipoBiomedico).filter_by(id=equipo_id).first()
    if not eq: return RedirectResponse(url="/tecnovigilancia")
    qr_b64 = gen_qr(eq.codigo_qr)
    mantenimientos = db.query(models.MantenimientoBiomedico).filter_by(
        equipo_id=equipo_id).order_by(models.MantenimientoBiomedico.fecha.desc()).all()
    return templates.TemplateResponse("tecnovigilancia/detalle.html", {
        "request": request, "user": current_user,
        "eq": eq, "qr_b64": qr_b64, "mantenimientos": mantenimientos,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/equipo/{codigo_qr}", response_class=HTMLResponse)
async def detalle_equipo_qr(codigo_qr: str, request: Request, db: Session = Depends(get_db),
                             current_user=Depends(auth.get_current_user)):
    eq = db.query(models.EquipoBiomedico).filter_by(codigo_qr=codigo_qr).first()
    if not eq: return HTMLResponse("<h2>Equipo no encontrado</h2>", status_code=404)
    if not current_user: return RedirectResponse(url=f"/login?next=/tecnovigilancia/equipo/{codigo_qr}")
    return RedirectResponse(url=f"/tecnovigilancia/equipo-id/{eq.id}")

@router.get("/equipo-id/{equipo_id}/mantenimiento", response_class=HTMLResponse)
async def nuevo_mant_form(equipo_id: int, request: Request, db: Session = Depends(get_db),
                           current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "tecnovigilancia", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    eq = db.query(models.EquipoBiomedico).filter_by(id=equipo_id).first()
    return templates.TemplateResponse("tecnovigilancia/form_mantenimiento.html", {
        "request": request, "user": current_user, "eq": eq,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/equipo-id/{equipo_id}/mantenimiento")
async def crear_mantenimiento(
    request: Request, equipo_id: int,
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    form = await request.form()
    firma_b64 = form.get("firma_tecnico","")
    ev = form.get("evidencia", None)

    ev_ruta = None
    if hasattr(ev, "filename") and ev.filename:
        fname = f"mant_{equipo_id}_{ev.filename}".replace(" ","_")
        ev_ruta = f"{UPLOAD_DIR}/{fname}"
        with open(ev_ruta, "wb") as f: shutil.copyfileobj(ev.file, f)

    prox = form.get("proxima_fecha","")
    m = models.MantenimientoBiomedico(
        equipo_id=equipo_id, tipo=form.get("tipo","preventivo"),
        tecnico=form.get("tecnico",""), descripcion=form.get("descripcion",""),
        hallazgos=form.get("hallazgos",""), acciones=form.get("acciones",""),
        proxima_fecha=datetime.fromisoformat(prox) if prox else None,
        firma_tecnico=firma_b64, firmado=bool(firma_b64),
        evidencia_ruta=ev_ruta, realizado_por=current_user.id
    )
    db.add(m); db.commit()
    return RedirectResponse(url=f"/tecnovigilancia/equipo-id/{equipo_id}", status_code=302)

@router.get("/mantenimiento/{mant_id}/reporte")
async def reporte_mantenimiento(mant_id: int, db: Session = Depends(get_db),
                                 current_user=Depends(auth.get_current_user)):
    m = db.query(models.MantenimientoBiomedico).filter_by(id=mant_id).first()
    eq = m.equipo if m else None
    logo_b64 = ""
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f: logo_b64 = base64.b64encode(f.read()).decode()

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:11px;padding:24px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #b45309;padding-bottom:10px;margin-bottom:16px;}}
  .header img{{height:50px;}} .header-c{{text-align:center;flex:1;}}
  .header-c h2{{margin:0;font-size:14px;color:#b45309;}} .header-c p{{margin:2px 0;font-size:9px;color:#555;}}
  .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}}
  .box{{border:1px solid #ddd;border-radius:5px;padding:7px 10px;}}
  .box .lbl{{font-size:8px;color:#888;text-transform:uppercase;}} .box .val{{font-size:12px;font-weight:bold;}}
  .section{{font-size:9px;font-weight:bold;background:#fef3c7;color:#92400e;padding:3px 8px;margin:10px 0 4px;border-left:3px solid #b45309;}}
  .content{{border:1px solid #ddd;border-radius:4px;padding:8px;min-height:36px;font-size:11px;white-space:pre-wrap;}}
  .firma-box{{border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center;margin-top:12px;}}
  .footer{{margin-top:16px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="header-c">
    <h2>REPORTE DE MANTENIMIENTO BIOMÉDICO</h2>
    <p>Tecnovigilancia · {m.fecha.strftime('%d/%m/%Y') if m else '—'}</p>
  </div>
</div>
<div class="grid">
  <div class="box"><div class="lbl">Equipo</div><div class="val">{eq.nombre if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Código</div><div class="val">{eq.codigo_qr if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Área</div><div class="val">{eq.area if eq else '—'}</div></div>
  <div class="box"><div class="lbl">Técnico</div><div class="val">{m.tecnico if m else '—'}</div></div>
  <div class="box"><div class="lbl">Tipo</div><div class="val">{m.tipo if m else '—'}</div></div>
  <div class="box"><div class="lbl">Próx. mantenimiento</div><div class="val">{m.proxima_fecha.strftime('%d/%m/%Y') if m and m.proxima_fecha else '—'}</div></div>
</div>
<div class="section">DESCRIPCIÓN DEL TRABAJO</div><div class="content">{(m.descripcion or '—') if m else '—'}</div>
<div class="section">HALLAZGOS</div><div class="content">{(m.hallazgos or '—') if m else '—'}</div>
<div class="section">ACCIONES REALIZADAS</div><div class="content">{(m.acciones or '—') if m else '—'}</div>
<div class="firma-box">
  <div style="font-size:9px;color:#555;margin-bottom:6px;">FIRMA DEL TÉCNICO</div>
  {'<img src="' + m.firma_tecnico + '" style="max-height:80px;max-width:240px;">' if m and m.firma_tecnico else '<div style="height:60px;border-bottom:1px solid #aaa;width:200px;margin:0 auto;"></div>'}
  <div style="font-size:9px;color:#555;margin-top:4px;">{m.tecnico if m else '—'}</div>
</div>
<div class="footer">Reporte N° {mant_id} · Generado por QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=reporte_biomedico_{mant_id}.html"})

@router.get("/scanner", response_class=HTMLResponse)
async def scanner_qr(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "tecnovigilancia", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("tecnovigilancia/scanner.html",{
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })
