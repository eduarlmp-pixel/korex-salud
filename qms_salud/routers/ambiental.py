from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import os, base64, json
from collections import defaultdict

router = APIRouter(prefix="/ambiental", tags=["ambiental"])

TIPOS_RESIDUO_LABELS = {
    "aprovechable":    ("Aprovechable",   "#1a56a0"),
    "no_aprovechable": ("No aprovechable","#b45309"),
    "biologico":       ("Biológico",      "#b91c1c"),
    "peligroso":       ("Peligroso",      "#7c3aed"),
    "especial":        ("Especial",       "#0e7490"),
    "quimico":         ("Químico",        "#c2410c"),
}

@router.get("", response_class=HTMLResponse)
async def home_ambiental(request: Request, db: Session = Depends(get_db),
                          current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambiental", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    registros = db.query(models.RegistroResiduo).order_by(models.RegistroResiduo.fecha.desc()).limit(20).all()
    # Totales por tipo
    totales = {}
    for tipo, (label, color) in TIPOS_RESIDUO_LABELS.items():
        total = sum(r.peso_kg for r in db.query(models.RegistroResiduo).filter_by(tipo=tipo).all())
        totales[tipo] = {"label": label, "color": color, "total": round(total, 2)}
    caps = db.query(models.CapacitacionSST).filter_by(area="Ambiental").order_by(models.CapacitacionSST.fecha.desc()).limit(5).all()
    return templates.TemplateResponse("ambiental/home.html", {
        "request": request, "user": current_user,
        "registros": registros, "totales": totales, "caps": caps,
        "tipos_labels": TIPOS_RESIDUO_LABELS,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/nuevo-registro", response_class=HTMLResponse)
async def nuevo_registro_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambiental", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("ambiental/form_residuo.html", {
        "request": request, "user": current_user, "tipos": TIPOS_RESIDUO_LABELS,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/nuevo-registro")
async def crear_registro(
    tipo: str = Form(...), subtipo: str = Form(""),
    peso_kg: float = Form(...), mes: str = Form(""),
    area_generadora: str = Form(""), numero_manifiesto: str = Form(""),
    observaciones: str = Form(""),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    r = models.RegistroResiduo(
        tipo=tipo, subtipo=subtipo, peso_kg=peso_kg, mes=mes,
        area_generadora=area_generadora, numero_manifiesto=numero_manifiesto,
        observaciones=observaciones, registrado_por=current_user.id
    )
    db.add(r); db.commit()
    return RedirectResponse(url="/ambiental", status_code=302)

@router.get("/certificado", response_class=HTMLResponse)
async def generar_certificado(request: Request, mes: str = "", db: Session = Depends(get_db),
                               current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "ambiental", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    query = db.query(models.RegistroResiduo)
    if mes: query = query.filter_by(mes=mes)
    registros = query.all()

    logo_b64 = ""
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f: logo_b64 = base64.b64encode(f.read()).decode()

    totales_cert = defaultdict(float)
    for r in registros: totales_cert[r.tipo] += r.peso_kg

    fecha_hoy = datetime.utcnow().strftime("%d/%m/%Y")
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;margin:0;padding:30px;color:#111;}}
  .header{{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #1a56a0;padding-bottom:14px;margin-bottom:20px;}}
  .header img{{height:55px;}}
  .title{{text-align:center;flex:1;}}
  .title h1{{margin:0;font-size:18px;color:#1a56a0;}}
  .title p{{margin:3px 0;font-size:11px;color:#555;}}
  table{{width:100%;border-collapse:collapse;margin:16px 0;}}
  th{{background:#1a56a0;color:#fff;padding:8px 12px;font-size:11px;}}
  td{{padding:7px 12px;border-bottom:1px solid #c8d8e8;font-size:12px;}}
  tr:nth-child(even){{background:#f0f4f8;}}
  .total-row{{font-weight:bold;background:#c8d8e8!important;}}
  .cert-box{{border:2px solid #1a56a0;border-radius:10px;padding:18px;margin-top:20px;text-align:center;}}
  .cert-box h2{{color:#1a56a0;margin:0 0 6px;font-size:15px;}}
  .footer{{margin-top:20px;font-size:9px;color:#aaa;text-align:center;border-top:1px solid #ddd;padding-top:8px;}}
</style></head><body>
<div class="header">
  {'<img src="data:image/png;base64,' + logo_b64 + '">' if logo_b64 else ''}
  <div class="title">
    <h1>CERTIFICADO DE DISPOSICIÓN DE RESIDUOS</h1>
    <p>Período: {mes if mes else 'Acumulado'} &nbsp;|&nbsp; Fecha de generación: {fecha_hoy}</p>
  </div>
</div>
<table>
  <tr><th>Tipo de residuo</th><th>Subtipo / Descripción</th><th>Mes</th><th>Gestor externo</th><th>N° Manifiesto</th><th>Peso (kg)</th></tr>
"""
    for r in registros:
        label = TIPOS_RESIDUO_LABELS.get(r.tipo, (r.tipo,"#000"))[0]
        html += f"<tr><td>{label}</td><td>{r.subtipo or '—'}</td><td>{r.mes or '—'}</td><td>{r.area_generadora or '—'}</td><td>{r.numero_manifiesto or '—'}</td><td><b>{r.peso_kg} kg</b></td></tr>"

    html += "<tr class='total-row'><td colspan='5'>TOTAL GENERAL</td><td>" + str(round(sum(r.peso_kg for r in registros),2)) + " kg</td></tr></table>"
    html += "<div class='cert-box'><h2>RESUMEN POR TIPO DE RESIDUO</h2><table><tr><th>Tipo</th><th>Total (kg)</th></tr>"
    for tipo, total in totales_cert.items():
        label = TIPOS_RESIDUO_LABELS.get(tipo, (tipo,""))[0]
        html += f"<tr><td>{label}</td><td>{round(total,2)} kg</td></tr>"
    html += f"</table></div><div class='footer'>Documento generado por QMS Salud · {fecha_hoy} · Este certificado acredita los pesos de residuos registrados en el sistema de gestión ambiental.</div></body></html>"

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=certificado_residuos_{mes or 'acumulado'}.html"})
