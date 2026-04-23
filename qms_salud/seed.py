"""
Poblar la BD con datos de demostración.
Ejecutar: python seed.py
"""
from database import SessionLocal, engine
import models
from auth import get_password_hash
from datetime import datetime, timedelta
import random

PERMISOS_POR_ROL = {
    "calidad": [
        ("documentos",         True, True,  True,  True,  False),
        ("auditorias",         True, False, False, False, False),
        ("mejora",             True, True,  True,  False, False),
        ("indicadores",        True, False, False, False, False),
        ("riesgos",            True, False, False, False, False),
        ("comites",            True, True,  True,  False, False),
        ("seguridad-paciente", True, False, False, False, False),
        ("dashboard",          True, False, False, False, False),
    ],
    "auditor": [
        ("auditorias",  True, True,  True,  False, False),
        ("mejora",      True, True,  False, False, False),
        ("documentos",  True, False, False, False, False),
        ("indicadores", True, False, False, False, False),
        ("riesgos",     True, False, False, False, False),
        ("dashboard",   True, False, False, False, False),
    ],
    "gestor": (
        [(m, True, True, True, False, False) for m in [
            "documentos", "auditorias", "mejora", "indicadores", "riesgos", "comites",
            "seguridad-paciente", "flujos", "sst", "ambiental", "ambiente-fisico",
            "tecnovigilancia", "sistemas", "ambulancias", "talento", "pqrs",
        ]] + [("dashboard", True, False, False, False, False)]
    ),
    "consultor": [
        (m, True, False, False, False, False) for m in [
            "documentos", "auditorias", "mejora", "indicadores", "riesgos", "comites",
            "seguridad-paciente", "flujos", "sst", "ambiental", "ambiente-fisico",
            "tecnovigilancia", "sistemas", "ambulancias", "talento", "pqrs", "dashboard",
        ]
    ],
}


def seed():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Usuarios
    usuarios_data = [
        {"nombre": "KOREX", "apellido": "Solutions", "email": "admin@qms.co", "password": "admin123", "rol": "admin", "cargo": "Director de Calidad", "area": "Calidad"},
        {"nombre": "Laura", "apellido": "Gómez", "email": "calidad@qms.co", "password": "calidad123", "rol": "calidad", "cargo": "Coordinadora de Calidad", "area": "Calidad"},
        {"nombre": "Andrés", "apellido": "Torres", "email": "auditor@qms.co", "password": "auditor123", "rol": "auditor", "cargo": "Auditor Interno", "area": "Calidad"},
        {"nombre": "María", "apellido": "Sánchez", "email": "gestor@qms.co", "password": "gestor123", "rol": "gestor", "cargo": "Jefe de Enfermería", "area": "Hospitalización"},
        {"nombre": "Juan", "apellido": "Pérez", "email": "consultor@qms.co", "password": "consultor123", "rol": "consultor", "cargo": "Médico General", "area": "Urgencias"},
    ]
    usuarios = []
    for u in usuarios_data:
        existing = db.query(models.Usuario).filter_by(email=u["email"]).first()
        if not existing:
            user = models.Usuario(
                nombre=u["nombre"], apellido=u["apellido"], email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                rol=u["rol"], cargo=u["cargo"], area=u["area"]
            )
            db.add(user)
            db.flush()
            usuarios.append(user)
        else:
            usuarios.append(existing)
    db.commit()

    # Categorías de documentos
    cats = ["Políticas", "Procedimientos", "Protocolos Clínicos", "Manuales", "Formatos", "Guías de Práctica"]
    categorias = []
    for c in cats:
        existing = db.query(models.CategoriaDoc).filter_by(nombre=c).first()
        if not existing:
            cat = models.CategoriaDoc(nombre=c, codigo=c[:3].upper())
            db.add(cat)
            db.flush()
            categorias.append(cat)
        else:
            categorias.append(existing)
    db.commit()

    db.commit()  # solo categorías, sin documentos de ejemplo

    # Auditorías
    auds_data = [
        ("AUD-2024-001", "Auditoría Interna ISO 9001 - Urgencias", "cerrada", "Urgencias"),
        ("AUD-2024-002", "Auditoría de Habilitación Res. 3100 - UCI", "cerrada", "UCI"),
        ("AUD-2024-003", "Auditoría PAMEC - Hospitalización", "en_curso", "Hospitalización"),
        ("AUD-2024-004", "Seguimiento Planes de Mejora - Calidad", "planificada", "Calidad"),
        ("AUD-2025-001", "Auditoría Interna Integral - Todos los procesos", "planificada", "Todos"),
    ]
    for cod, titulo, estado, proceso in auds_data:
        existing = db.query(models.Auditoria).filter_by(codigo=cod).first()
        if not existing:
            aud = models.Auditoria(
                codigo=cod, titulo=titulo, estado=estado, proceso_auditado=proceso,
                lider_id=usuarios[2].id,
                fecha_inicio=datetime.utcnow() - timedelta(days=random.randint(10, 90)),
                fecha_fin=datetime.utcnow() + timedelta(days=random.randint(1, 30)),
                norma_referencia="ISO 9001:2015 / Res. 3100/2019",
            )
            db.add(aud)
            db.flush()
            # Hallazgos para auditorías cerradas
            if estado in ["cerrada", "en_curso"]:
                tipos_h = ["no_conformidad", "observacion", "oportunidad"]
                procesos_h = ["Admisiones", "Enfermería", "Farmacia", "Laboratorio"]
                for j in range(random.randint(2, 5)):
                    h = models.Hallazgo(
                        auditoria_id=aud.id,
                        tipo=random.choice(tipos_h),
                        descripcion=f"Hallazgo {j+1}: {'No se evidencia registro completo de' if j%2==0 else 'Oportunidad de mejora en'} {random.choice(procesos_h)}.",
                        proceso=random.choice(procesos_h),
                        estado=random.choice(["pendiente", "en_proceso", "completada"]),
                    )
                    db.add(h)
    db.commit()

    # Riesgos
    riesgos_data = [
        ("RIE-001", "Urgencias", "Identificación incorrecta del paciente", 3, 5),
        ("RIE-002", "Farmacia", "Error en dispensación de medicamentos", 4, 5),
        ("RIE-003", "Hospitalización", "Caída de pacientes", 4, 3),
        ("RIE-004", "Quirófano", "Infección del sitio operatorio", 2, 5),
        ("RIE-005", "UCI", "Úlceras por presión", 3, 3),
        ("RIE-006", "Laboratorio", "Resultado crítico no notificado", 2, 4),
        ("RIE-007", "Calidad", "Documentos desactualizados en circulación", 3, 2),
        ("RIE-008", "RRHH", "Personal sin capacitación obligatoria", 2, 3),
    ]
    niveles = {(1,1):"bajo",(1,2):"bajo",(2,1):"bajo",(2,2):"bajo",(2,3):"moderado",
               (3,2):"moderado",(3,3):"moderado",(3,4):"alto",(4,3):"alto",(4,4):"alto",
               (2,4):"alto",(4,5):"critico",(5,4):"critico",(5,5):"critico",(3,5):"critico",(4,2):"moderado"}
    for cod, proceso, desc, prob, imp in riesgos_data:
        existing = db.query(models.Riesgo).filter_by(codigo=cod).first()
        if not existing:
            nivel = niveles.get((prob, imp), "moderado")
            r = models.Riesgo(
                codigo=cod, proceso=proceso, descripcion=desc,
                probabilidad=prob, impacto=imp, nivel=nivel,
                responsable_id=usuarios[0].id,
                fecha_evaluacion=datetime.utcnow() - timedelta(days=random.randint(10, 60)),
                fecha_revision=datetime.utcnow() + timedelta(days=90),
            )
            db.add(r)
    db.commit()

    # Indicadores
    inds_data = [
        ("IND-001", "Tasa de Infección Asociada a Atención en Salud", "UCI", "%", 2.0, 0, 3.0, "mensual"),
        ("IND-002", "Tasa de Caídas de Pacientes", "Hospitalización", "por 1000 días", 1.5, 0, 2.5, "mensual"),
        ("IND-003", "Satisfacción del Paciente", "Todos", "%", 90.0, 85.0, 100.0, "mensual"),
        ("IND-004", "Tasa de Reingreso no Planificado 30 días", "Hospitalización", "%", 5.0, 0, 8.0, "mensual"),
        ("IND-005", "Giro-Cama", "Hospitalización", "días", 4.5, 3.0, 6.0, "mensual"),
        ("IND-006", "Oportunidad en Consulta Externa", "Consulta Externa", "días", 3.0, 1.0, 5.0, "mensual"),
        ("IND-007", "Cumplimiento de Auditorías", "Calidad", "%", 95.0, 90.0, 100.0, "trimestral"),
        ("IND-008", "PQRS resueltas a tiempo", "Calidad", "%", 95.0, 90.0, 100.0, "mensual"),
    ]
    for cod, nombre, proceso, unidad, meta, meta_min, meta_max, freq in inds_data:
        existing = db.query(models.Indicador).filter_by(codigo=cod).first()
        if not existing:
            ind = models.Indicador(
                codigo=cod, nombre=nombre, proceso=proceso, unidad=unidad,
                meta=meta, meta_minima=meta_min, meta_maxima=meta_max,
                frecuencia=freq, responsable_id=usuarios[1].id,
            )
            db.add(ind)
            db.flush()
            # Mediciones últimos 6 meses
            meses = ["2024-07","2024-08","2024-09","2024-10","2024-11","2024-12"]
            for mes in meses:
                variacion = random.uniform(-0.3, 0.3)
                valor = round(meta * (1 + variacion), 2)
                m = models.MedicionIndicador(
                    indicador_id=ind.id, valor=valor, periodo=mes,
                    registrado_por=usuarios[1].id,
                )
                db.add(m)
    db.commit()

    # Acciones de mejora
    acciones_data = [
        ("ACC-001", "Implementar doble verificación medicamentos alto riesgo", "correctiva", "auditoria"),
        ("ACC-002", "Actualizar protocolo de identificación de paciente", "correctiva", "pqrs"),
        ("ACC-003", "Capacitar personal en manejo de caídas", "preventiva", "indicador"),
        ("ACC-004", "Digitalizar registros de enfermería nocturnos", "mejora", "auto"),
        ("ACC-005", "Implementar ronda de seguridad semanal en UCI", "preventiva", "riesgo"),
    ]
    estados_acc = ["pendiente", "en_proceso", "completada", "en_proceso", "pendiente"]
    avances = [0, 45, 100, 70, 20]
    for i, (cod, titulo, tipo, origen) in enumerate(acciones_data):
        existing = db.query(models.AccionMejora).filter_by(codigo=cod).first()
        if not existing:
            acc = models.AccionMejora(
                codigo=cod, titulo=titulo, tipo=tipo, origen=origen,
                estado=estados_acc[i], porcentaje_avance=avances[i],
                responsable_id=usuarios[i % len(usuarios)].id,
                proceso=["Farmacia","Urgencias","Hospitalización","Enfermería","UCI"][i],
                fecha_limite=datetime.utcnow() + timedelta(days=random.randint(5, 60)),
            )
            db.add(acc)
    db.commit()

    # Empleados
    empleados_data = [
        ("Carlos", "García", "10001", "Director de Calidad", "Calidad"),
        ("Laura", "Gómez", "10002", "Coordinadora de Calidad", "Calidad"),
        ("Andrés", "Torres", "10003", "Auditor Interno", "Calidad"),
        ("María", "Sánchez", "10004", "Jefe de Enfermería", "Hospitalización"),
        ("Juan", "Pérez", "10005", "Médico General", "Urgencias"),
        ("Ana", "Rodríguez", "10006", "Enfermera Jefe UCI", "UCI"),
        ("Pedro", "Martínez", "10007", "Químico Farmacéutico", "Farmacia"),
        ("Diana", "López", "10008", "Bacterióloga", "Laboratorio"),
    ]
    for nombres, apellidos, doc, cargo, area in empleados_data:
        existing = db.query(models.Empleado).filter_by(documento=doc).first()
        if not existing:
            emp = models.Empleado(
                nombres=nombres, apellidos=apellidos, documento=doc,
                cargo=cargo, area=area, activo=True,
                fecha_ingreso=datetime.utcnow() - timedelta(days=random.randint(180, 1800)),
            )
            db.add(emp)
    db.commit()

    # PQRS
    pqrs_data = [
        ("PQR-001", "queja", "abierta", "Demora en atención urgencias", "Juan Ciudadano", "alta"),
        ("PQR-002", "peticion", "resuelta", "Solicitud de historia clínica", "Ana Martínez", "normal"),
        ("PQR-003", "evento_adverso", "en_gestion", "Caída de paciente en piso 3", "Interno", "alta"),
        ("PQR-004", "sugerencia", "cerrada", "Mejorar señalización hospitalaria", "Pedro Ruiz", "baja"),
        ("PQR-005", "reclamo", "abierta", "Error en factura de servicios", "María Torres", "normal"),
        ("PQR-006", "queja", "en_gestion", "Trato inadecuado en admisiones", "Carlos Díaz", "alta"),
    ]
    for cod, tipo, estado, desc, nombre, prioridad in pqrs_data:
        existing = db.query(models.PQRS).filter_by(codigo=cod).first()
        if not existing:
            p = models.PQRS(
                codigo=cod, tipo=tipo, estado=estado, descripcion=desc,
                nombre_solicitante=nombre, prioridad=prioridad,
                asignado_a=usuarios[1].id,
                fecha_registro=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                fecha_limite=datetime.utcnow() + timedelta(days=random.randint(1, 15)),
            )
            db.add(p)
    db.commit()

    # Flujos de trabajo
    flujos_data = [
        ("Ingreso de Paciente", "Proceso de admisión hospitalaria", "Admisiones"),
        ("Gestión de PQRS", "Recepción y respuesta de PQRS", "Calidad"),
        ("Aprobación de Documentos", "Revisión y aprobación de documentos del SGC", "Calidad"),
    ]
    for nombre, desc, proceso in flujos_data:
        existing = db.query(models.FlujoTrabajo).filter_by(nombre=nombre).first()
        if not existing:
            f = models.FlujoTrabajo(nombre=nombre, descripcion=desc, proceso=proceso)
            db.add(f)
            db.flush()
            pasos = [
                ("Recepción", 1, 1), ("Verificación documentos", 2, 1),
                ("Asignación cama/servicio", 3, 2), ("Notificación área", 4, 1)
            ]
            for np, orden, dias in pasos:
                db.add(models.PasoFlujo(
                    flujo_id=f.id, orden=orden, nombre=np,
                    responsable_rol="gestor", dias_limite=dias
                ))
    db.commit()
    # Permisos de usuario por rol
    for usuario in db.query(models.Usuario).all():
        rol_str = usuario.rol.value if hasattr(usuario.rol, "value") else usuario.rol
        if rol_str == "admin" or rol_str not in PERMISOS_POR_ROL:
            continue
        db.query(models.PermisoUsuario).filter_by(usuario_id=usuario.id).delete()
        for (modulo, ver, crear, editar, aprobar, eliminar) in PERMISOS_POR_ROL[rol_str]:
            db.add(models.PermisoUsuario(
                usuario_id=usuario.id, modulo=modulo,
                puede_ver=ver, puede_crear=crear, puede_editar=editar,
                puede_aprobar=aprobar, puede_eliminar=eliminar,
            ))
    db.commit()

    db.close()
    print("✅ Base de datos poblada con datos de demostración.")
    print("   Usuarios creados:")
    print("   admin@qms.co     / admin123     (Administrador)")
    print("   calidad@qms.co   / calidad123   (Calidad)")
    print("   auditor@qms.co   / auditor123   (Auditor)")

if __name__ == "__main__":
    seed()
