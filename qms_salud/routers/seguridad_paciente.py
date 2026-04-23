from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from templates_config import templates
import models, auth
from datetime import datetime
import os, base64, shutil

router = APIRouter(prefix="/seguridad-paciente", tags=["seguridad_paciente"])
UPLOAD_DIR = "static/uploads/seguridad"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_logo_b64():
    if os.path.exists("static/img/logo.png"):
        with open("static/img/logo.png","rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# Definición de secciones y campos para la ronda
SECCIONES_RONDA = [
    ("Infraestructura física", [
        ("pisos_paredes","Pisos y paredes"),
        ("ventilacion","Ventilación"),
        ("iluminacion","Iluminación"),
        ("antideslizantes","Antideslizantes"),
        ("privacidad","Privacidad del usuario"),
        ("senalizacion","Señalización"),
        ("techo","Techo"),
        ("condiciones_aseo","Condiciones generales de aseo"),
        ("espacios_humanizados","Espacios humanizados"),
    ]),
    ("Gestión documental", [
        ("historia_clinica","Historia clínica (organización y confidencialidad)"),
        ("rotulacion","Rotulación (avisos, áreas, elementos)"),
        ("formatos_vigentes","Se utilizan formatos vigentes"),
        ("consentimiento","Consentimiento informado diligenciado y entendido"),
        ("registro_hc","Registro completo de formatos de historia clínica"),
        ("identificacion_riesgos","Identificación de riesgos en valoración integral"),
        ("reporte_eventos","Identifica medios de reporte de incidentes o eventos adversos"),
        ("entorno_seguro","Entorno del paciente seguro (barandas, escalerilla, acompañante)"),
        ("identificacion_paciente","Identificación del paciente (rótulo, manilla, historia clínica)"),
    ]),
    ("Medicamentos", [
        ("almacenamiento_med","Estado de almacenamiento de medicamentos"),
        ("prescripcion","Adecuada prescripción médica"),
        ("conciliacion_med","Conciliación medicamentosa registrada en HC"),
        ("dispensacion","Correcta dispensación y administración de medicamentos"),
        ("correctos_med","El profesional conoce los correctos de administración"),
    ]),
    ("Dispositivos y equipos biomédicos", [
        ("equipos_funcionando","Equipos biomédicos funcionando adecuadamente"),
        ("mantenimiento_prev","Equipo cuenta con mantenimiento preventivo"),
        ("calibracion","Equipo cuenta con calibración"),
        ("ficha_uso","Equipos biomédicos con ficha de uso rápido"),
        ("entrenamiento_eq","Personal entrenado en uso de equipos del servicio"),
        ("limpieza_equipos","Cumple con limpieza y desinfección de equipos"),
        ("almacenamiento_disp","Área de almacenamiento de dispositivos médicos"),
    ]),
    ("Recurso humano", [
        ("personal_completo","Personal completo según programación de turnos"),
        ("carnet_visible","Porta el carnet en lugar visible"),
        ("politica_seguridad","Conoce la política de seguridad del paciente"),
        ("cultura_reporte","Cultura de reporte: identifica medios de reporte"),
        ("supervision","Cuenta con supervisión cuando realiza actividades"),
    ]),
    ("Medidas de prevención de infecciones", [
        ("bioseguridad","Cumplimiento de medidas de bioseguridad (lavado de manos)"),
        ("elementos_lavado","Disponibilidad de elementos para higienización de manos"),
        ("rotulacion_mezclas","Rotulación de mezclas y cambios de equipos venosos"),
        ("limpieza_areas","Limpieza y desinfección de áreas y superficies"),
        ("segregacion_residuos","Segregación adecuada de residuos en canecas y guardianes"),
        ("epp_aislamiento","Uso de EPP y medidas de aislamiento"),
    ]),
    ("Paquetes instruccionales", [
        ("escala_braden","Aplicación de la escala de Braden (úlceras)"),
        ("prevencion_ulceras","Acciones de prevención de úlceras por presión"),
        ("higienizacion_manos","Higienización de manos"),
        ("elementos_lavado2","Elementos para lavado disponibles"),
        ("educacion_familia","Educación a usuario y su familia"),
        ("mecanismos_aislamiento","Mecanismos de aislamiento"),
        ("prevencion_infecciones","Acciones de prevención de infecciones"),
        ("identificacion_muestras","Identificación de muestras"),
        ("identificacion_usuarios","Identificación de usuarios"),
        ("consentimiento_pac","Consentimiento informado"),
        ("caidas","Prevención de caídas"),
        ("maternidad_segura","Maternidad segura"),
        ("reporte_gestion","Reporte y gestión de eventos de seguridad"),
    ]),
    ("Entrevista con el usuario y su familia", [
        ("educacion_seguridad","Educación sobre seguridad del paciente"),
        ("educacion_humanizacion","Educación sobre humanización"),
        ("ciclo_atencion","Educación sobre ciclo de atención"),
    ]),
]

PREGUNTAS_COLABORADOR = [
    "¿Si usted pudiera cambiar algo de su servicio para mejorar la seguridad del paciente, qué debería ser?",
    "¿Cuál fue el último evento adverso que usted observó?",
    "¿Qué cree usted que, teniendo en cuenta las condiciones de su servicio, será causante del próximo evento adverso?",
    "¿Cuál fue el último evento adverso que prolongó la hospitalización de un paciente?",
    "¿Qué estuvo mal ayer?",
    "¿Cuando las cosas van mal, a quién contacta usted?",
    "¿Si usted pudiera iniciar este día otra vez, qué haría diferente?",
    "¿Qué pregunta debí haberle hecho y no la hice?",
]

@router.get("", response_class=HTMLResponse)
async def home_sp(request: Request, db: Session = Depends(get_db),
                  current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "seguridad-paciente", "puede_ver"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    rondas = db.query(models.RondaSeguridad).order_by(models.RondaSeguridad.fecha.desc()).limit(10).all()
    paquetes = db.query(models.PaqueteInstruccional).filter_by(vigente=True).all()
    # Stats rondas
    total_rondas = db.query(models.RondaSeguridad).count()
    pct_prom = 0
    if rondas:
        pcts = [r.porcentaje for r in rondas if r.porcentaje]
        pct_prom = round(sum(pcts)/len(pcts), 1) if pcts else 0
    return templates.TemplateResponse("seguridad_paciente/home.html", {
        "request": request, "user": current_user,
        "rondas": rondas, "paquetes": paquetes,
        "total_rondas": total_rondas, "pct_prom": pct_prom,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.get("/ronda/nueva", response_class=HTMLResponse)
async def nueva_ronda_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "seguridad-paciente", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("seguridad_paciente/form_ronda.html", {
        "request": request, "user": current_user,
        "secciones": SECCIONES_RONDA, "preguntas": PREGUNTAS_COLABORADOR,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/ronda/nueva")
async def crear_ronda(request: Request,
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    form = await request.form()
    firma_eval = form.get("firma_evaluador","")
    firma_rec  = form.get("firma_receptor","")

    # Recopilar todos los campos de checklist
    campos_bool = {}
    total = 0
    cumple = 0
    for _, items in SECCIONES_RONDA:
        for campo, _ in items:
            val = form.get(campo, "2")
            campos_bool[campo] = val
            total += 1
            if val == "1":
                cumple += 1

    pct = round((cumple/total)*100, 1) if total > 0 else 0

    ronda = models.RondaSeguridad(
        evaluador=form.get("evaluador",""),
        servicio=form.get("servicio",""),
        fecha=datetime.fromisoformat(form.get("fecha","")) if form.get("fecha") else datetime.utcnow(),
        observaciones=form.get("observaciones",""),
        firma_evaluador=firma_eval,
        firma_receptor=firma_rec,
        firmado=bool(firma_eval),
        total_items=total,
        items_cumple=cumple,
        porcentaje=pct,
        creado_por=current_user.id,
        pregunta1=form.get("pregunta1",""),
        pregunta2=form.get("pregunta2",""),
        pregunta3=form.get("pregunta3",""),
        pregunta4=form.get("pregunta4",""),
        pregunta5=form.get("pregunta5",""),
        pregunta6=form.get("pregunta6",""),
        pregunta7=form.get("pregunta7",""),
        pregunta8=form.get("pregunta8",""),
        **campos_bool
    )
    db.add(ronda); db.commit()
    return RedirectResponse(url=f"/seguridad-paciente/ronda/{ronda.id}/reporte", status_code=302)

@router.get("/ronda/{ronda_id}/reporte")
async def reporte_ronda(ronda_id: int, db: Session = Depends(get_db),
                         current_user=Depends(auth.get_current_user)):
    r = db.query(models.RondaSeguridad).filter_by(id=ronda_id).first()
    logo_b64 = get_logo_b64()

    # Determinar semáforo
    pct = r.porcentaje if r else 0
    if pct >= 95:
        semaforo_color = "#0e7c45"; semaforo_txt = "ÁREA QUE CUMPLE Y REQUIERE MANTENIMIENTO (95%-100%)"
    elif pct >= 85:
        semaforo_color = "#b45309"; semaforo_txt = "ÁREA QUE REQUIERE MEJORAR Y CONSOLIDAR (85%-94%)"
    else:
        semaforo_color = "#b91c1c"; semaforo_txt = "ÁREA REQUIERE INTENSIFICAR EL MEJORAMIENTO (< 85%)"

    icon = {"1":"✓","2":"✗"}
    col  = {"1":"#0e7c45","2":"#b91c1c"}

    # Filas de checklist agrupadas por sección
    filas_html = ""
    for sec_nombre, items in SECCIONES_RONDA:
        filas_html += f'<tr><td colspan="4" style="background:#d0dff0;font-weight:bold;font-size:10px;border:1px solid #888;padding:4px 8px;">{sec_nombre.upper()}</td></tr>'
        for campo, label in items:
            val = getattr(r, campo, "2") if r else "2"
            ic  = icon.get(val,"—")
            cl  = col.get(val,"#888")
            filas_html += f'<tr><td style="border:1px solid #ddd;padding:4px 8px;font-size:10px;">{label}</td><td style="border:1px solid #ddd;text-align:center;color:{cl};font-weight:bold;">{ic}</td><td style="border:1px solid #ddd;text-align:center;font-size:10px;color:#888;">Semaforización</td><td style="border:1px solid #ddd;padding:4px 8px;font-size:10px;"></td></tr>'

    # Preguntas colaborador
    pregs_html = ""
    for i, preg in enumerate(PREGUNTAS_COLABORADOR):
        campo = f"pregunta{i+1}"
        resp = getattr(r, campo, "") if r else ""
        pregs_html += f'<tr><td style="border:1px solid #ddd;padding:5px 8px;font-size:10px;width:60%;">{i+1}. {preg}</td><td style="border:1px solid #ddd;padding:5px 8px;font-size:10px;">{resp or ""}</td></tr>'

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;font-size:10px;margin:0;padding:18px;color:#111;}}
  .header-top{{display:flex;justify-content:space-between;align-items:stretch;border:1px solid #888;margin-bottom:0;}}
  .logo-cell{{padding:6px 10px;border-right:1px solid #888;display:flex;align-items:center;min-width:80px;}}
  .title-cell{{flex:1;text-align:center;padding:6px;border-right:1px solid #888;}}
  .code-cell{{padding:6px 10px;font-size:9px;min-width:120px;}}
  h2{{margin:0;font-size:12px;font-weight:bold;text-transform:uppercase;}}
  table{{width:100%;border-collapse:collapse;margin-bottom:4px;}}
  th{{background:#d0dff0;padding:5px 8px;font-size:9px;text-align:left;border:1px solid #888;}}
  td{{padding:3px 8px;border:1px solid #ddd;font-size:10px;vertical-align:top;}}
  .sec{{background:#d0dff0;font-weight:bold;text-align:center;}}
  .semaforo{{padding:8px 12px;border-radius:6px;font-weight:bold;font-size:11px;display:inline-block;margin:8px 0;}}
  .firma-area{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:12px;}}
  .firma-box{{border:1px solid #ddd;border-radius:4px;padding:10px;text-align:center;}}
  .footer{{margin-top:10px;font-size:8px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:6px;}}
</style></head><body>

<div class="header-top">
  <div class="logo-cell">{'<img src="data:image/png;base64,' + logo_b64 + '" style="height:45px;">' if logo_b64 else ''}</div>
  <div class="title-cell">
    <div style="font-size:10px;font-weight:bold;">SEGURIDAD DEL PACIENTE</div>
    <h2>LISTA DE CHEQUEO — RONDA DE SEGURIDAD</h2>
  </div>
  <div class="code-cell">
    <div><b>Código:</b> GER-SEG-FM-13</div>
    <div><b>Versión:</b> 02</div>
    <div><b>Fecha:</b> NOV. 2020</div>
  </div>
</div>

<table style="margin-top:0;"><tr>
  <td style="border:1px solid #888;padding:4px 8px;width:35%;"><b>Nombre del evaluador:</b> {r.evaluador if r else '—'}</td>
  <td style="border:1px solid #888;padding:4px 8px;width:40%;"><b>Servicio o área:</b> {r.servicio if r else '—'}</td>
  <td style="border:1px solid #888;padding:4px 8px;"><b>Fecha:</b> {r.fecha.strftime('%d/%m/%Y') if r and r.fecha else '—'}</td>
</tr></table>

<table style="margin-top:4px;">
  <tr><th style="width:60%;">ÍTEM A VERIFICAR</th><th style="width:10%;text-align:center;">Cumple (1) / No (2)</th><th style="width:15%;text-align:center;">Semaforización</th><th>Observaciones</th></tr>
  {filas_html}
</table>

<div style="margin-top:8px;">
  <div class="semaforo" style="background:{semaforo_color}22;color:{semaforo_color};border:1px solid {semaforo_color};">
    {semaforo_txt} — Resultado: <b>{pct}%</b> ({r.items_cumple if r else 0}/{r.total_items if r else 0} ítems)
  </div>
</div>

<table style="margin-top:8px;">
  <tr><td colspan="2" class="sec" style="border:1px solid #888;">ENTREVISTA AL COLABORADOR</td></tr>
  <tr><th style="width:60%;">Pregunta</th><th>Respuesta</th></tr>
  {pregs_html}
</table>

<div style="margin-top:8px;border:1px solid #ddd;border-radius:4px;padding:8px;">
  <b>Observaciones generales:</b><br>
  <div style="min-height:30px;">{(r.observaciones or '') if r else ''}</div>
</div>

<table style="margin-top:8px;">
  <tr>
    <td style="border:1px solid #888;padding:4px 8px;background:#f0f0f0;font-size:9px;font-weight:bold;">ÁREA QUE CUMPLE Y REQUIERE MANTENIMIENTO</td>
    <td style="border:1px solid #888;padding:4px 8px;text-align:center;font-weight:bold;color:#0e7c45;">95% A 100%</td>
    <td style="border:1px solid #888;padding:4px 8px;background:#f0f0f0;font-size:9px;font-weight:bold;">REQUIERE MEJORAR Y CONSOLIDAR</td>
    <td style="border:1px solid #888;padding:4px 8px;text-align:center;font-weight:bold;color:#b45309;">85% A 94%</td>
    <td style="border:1px solid #888;padding:4px 8px;background:#f0f0f0;font-size:9px;font-weight:bold;">REQUIERE INTENSIFICAR MEJORAMIENTO</td>
    <td style="border:1px solid #888;padding:4px 8px;text-align:center;font-weight:bold;color:#b91c1c;">&lt; 85%</td>
  </tr>
</table>

<div class="firma-area">
  <div class="firma-box">
    <div style="font-size:9px;color:#555;margin-bottom:6px;font-weight:bold;">REALIZÓ (EVALUADOR)</div>
    {'<img src="' + r.firma_evaluador + '" style="max-height:70px;max-width:200px;">' if r and r.firma_evaluador else '<div style="height:55px;border-bottom:1px solid #aaa;width:160px;margin:0 auto;"></div>'}
    <div style="font-size:10px;margin-top:4px;">{r.evaluador if r else '—'}</div>
  </div>
  <div class="firma-box">
    <div style="font-size:9px;color:#555;margin-bottom:6px;font-weight:bold;">RECIBIÓ</div>
    {'<img src="' + r.firma_receptor + '" style="max-height:70px;max-width:200px;">' if r and r.firma_receptor else '<div style="height:55px;border-bottom:1px solid #aaa;width:160px;margin:0 auto;"></div>'}
    <div style="font-size:10px;margin-top:4px;">Responsable del área</div>
  </div>
</div>

<div class="footer">Ronda de Seguridad N° {ronda_id} · QMS Salud · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>"""

    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=ronda_seguridad_{ronda_id}.html"})

# ── PAQUETES INSTRUCCIONALES ──
@router.get("/paquete/nuevo", response_class=HTMLResponse)
async def nuevo_paquete_form(request: Request, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    if not auth.tiene_permiso(db, current_user, "seguridad-paciente", "puede_crear"):
        return RedirectResponse(url="/?sin_acceso=1", status_code=302)
    return templates.TemplateResponse("seguridad_paciente/form_paquete.html", {
        "request": request, "user": current_user,
        "permisos": auth.get_permisos(db, current_user),
    })

@router.post("/paquete/nuevo")
async def crear_paquete(
    nombre: str = Form(...), tipo: str = Form(""),
    descripcion: str = Form(""), objetivo: str = Form(""),
    contenido: str = Form(""), version: str = Form("1.0"),
    archivo: UploadFile = File(None),
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    arch_ruta = None
    if archivo and archivo.filename:
        fname = f"paq_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{archivo.filename}".replace(" ","_")
        arch_ruta = f"{UPLOAD_DIR}/{fname}"
        with open(arch_ruta,"wb") as f: shutil.copyfileobj(archivo.file, f)
    p = models.PaqueteInstruccional(
        nombre=nombre, tipo=tipo, descripcion=descripcion,
        objetivo=objetivo, contenido=contenido, version=version,
        archivo_ruta=arch_ruta, creado_por=current_user.id
    )
    db.add(p); db.commit()
    return RedirectResponse(url="/seguridad-paciente", status_code=302)
