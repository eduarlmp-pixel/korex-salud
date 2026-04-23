from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

# ─── ENUMS ────────────────────────────────────────────────────────────────────

class RolUsuario(str, enum.Enum):
    admin = "admin"
    calidad = "calidad"
    auditor = "auditor"
    gestor = "gestor"
    consultor = "consultor"

class EstadoDoc(str, enum.Enum):
    borrador = "borrador"
    revision = "revision"
    aprobado = "aprobado"
    obsoleto = "obsoleto"

class EstadoAuditoria(str, enum.Enum):
    planificada = "planificada"
    en_curso = "en_curso"
    cerrada = "cerrada"
    cancelada = "cancelada"

class NivelRiesgo(str, enum.Enum):
    bajo = "bajo"
    moderado = "moderado"
    alto = "alto"
    critico = "critico"

class EstadoAccion(str, enum.Enum):
    pendiente = "pendiente"
    en_proceso = "en_proceso"
    completada = "completada"
    vencida = "vencida"

class TipoPQRS(str, enum.Enum):
    peticion = "peticion"
    queja = "queja"
    reclamo = "reclamo"
    sugerencia = "sugerencia"
    evento_adverso = "evento_adverso"

class EstadoPQRS(str, enum.Enum):
    abierta = "abierta"
    en_gestion = "en_gestion"
    resuelta = "resuelta"
    cerrada = "cerrada"

# ─── USUARIOS ─────────────────────────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.consultor)
    cargo = Column(String(100))
    area = Column(String(100))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    ultimo_acceso = Column(DateTime)
    firma_imagen = Column(Text)      # base64 firma registrada del usuario
    foto_perfil = Column(Text)       # base64 foto de perfil

    documentos_creados = relationship("Documento", back_populates="creador", foreign_keys="Documento.creador_id")
    auditorias_lideradas = relationship("Auditoria", back_populates="lider")
    acciones_asignadas = relationship("AccionMejora", back_populates="responsable")
    talento = relationship("Empleado", back_populates="usuario", uselist=False)

# ─── DOCUMENTOS ───────────────────────────────────────────────────────────────

class CategoriaDoc(Base):
    __tablename__ = "categorias_doc"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(20))
    descripcion = Column(Text)
    documentos = relationship("Documento", back_populates="categoria")

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    version = Column(String(20), default="1.0")
    estado = Column(Enum(EstadoDoc), default=EstadoDoc.borrador)
    categoria_id = Column(Integer, ForeignKey("categorias_doc.id"))
    creador_id = Column(Integer, ForeignKey("usuarios.id"))
    aprobador_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_aprobacion = Column(DateTime)
    fecha_vencimiento = Column(DateTime)
    ruta_archivo = Column(String(300))
    nombre_archivo = Column(String(300))
    visualizaciones = Column(Integer, default=0)
    descargas = Column(Integer, default=0)
    tags = Column(String(300))

    categoria = relationship("CategoriaDoc", back_populates="documentos")
    creador = relationship("Usuario", back_populates="documentos_creados", foreign_keys=[creador_id])
    aprobador = relationship("Usuario", foreign_keys=[aprobador_id])
    versiones = relationship("VersionDoc", back_populates="documento")
    validaciones = relationship("ValidacionDoc", back_populates="documento")

class VersionDoc(Base):
    __tablename__ = "versiones_doc"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"))
    version = Column(String(20))
    cambios = Column(Text)
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    ruta_archivo = Column(String(300))
    documento = relationship("Documento", back_populates="versiones")

class ValidacionDoc(Base):
    __tablename__ = "validaciones_doc"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    etapa = Column(String(50), nullable=False)
    orden = Column(Integer, default=0)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    estado = Column(String(20), default="pendiente")  # pendiente, aprobado, rechazado
    comentario = Column(Text)
    fecha_validacion = Column(DateTime)

    documento = relationship("Documento", back_populates="validaciones")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

# ─── AUDITORÍAS ───────────────────────────────────────────────────────────────

class Auditoria(Base):
    __tablename__ = "auditorias"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(50))  # interna, externa, seguimiento
    estado = Column(Enum(EstadoAuditoria), default=EstadoAuditoria.planificada)
    lider_id = Column(Integer, ForeignKey("usuarios.id"))
    proceso_auditado = Column(String(150))
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    objetivo = Column(Text)
    alcance = Column(Text)
    norma_referencia = Column(String(200))  # ISO 9001, Res. 3100, etc.
    observaciones = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)

    lider = relationship("Usuario", back_populates="auditorias_lideradas")
    hallazgos = relationship("Hallazgo", back_populates="auditoria")
    checklists = relationship("ChecklistAuditoria", back_populates="auditoria")

class Hallazgo(Base):
    __tablename__ = "hallazgos"
    id = Column(Integer, primary_key=True)
    auditoria_id = Column(Integer, ForeignKey("auditorias.id"))
    tipo = Column(String(50))  # no_conformidad, observacion, oportunidad
    descripcion = Column(Text, nullable=False)
    evidencia = Column(Text)
    proceso = Column(String(150))
    criterio = Column(String(200))
    estado = Column(Enum(EstadoAccion), default=EstadoAccion.pendiente)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    auditoria = relationship("Auditoria", back_populates="hallazgos")
    acciones = relationship("AccionMejora", back_populates="hallazgo")

class ChecklistAuditoria(Base):
    __tablename__ = "checklists_auditoria"
    id = Column(Integer, primary_key=True)
    auditoria_id = Column(Integer, ForeignKey("auditorias.id"))
    pregunta = Column(Text, nullable=False)
    criterio = Column(String(200))
    respuesta = Column(String(20))  # si, no, parcial, na
    observacion = Column(Text)
    auditoria = relationship("Auditoria", back_populates="checklists")

# ─── MEJORA CONTINUA ──────────────────────────────────────────────────────────

class AccionMejora(Base):
    __tablename__ = "acciones_mejora"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    tipo = Column(String(50))  # correctiva, preventiva, mejora
    origen = Column(String(100))  # auditoria, pqrs, indicador, riesgo, auto
    estado = Column(Enum(EstadoAccion), default=EstadoAccion.pendiente)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"))
    hallazgo_id = Column(Integer, ForeignKey("hallazgos.id"), nullable=True)
    proceso = Column(String(150))
    causa_raiz = Column(Text)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_limite = Column(DateTime)
    fecha_cierre = Column(DateTime)
    porcentaje_avance = Column(Integer, default=0)
    eficacia = Column(String(50))  # eficaz, no_eficaz, pendiente_verificacion
    creado_en = Column(DateTime, default=datetime.utcnow)

    responsable = relationship("Usuario", back_populates="acciones_asignadas")
    hallazgo = relationship("Hallazgo", back_populates="acciones")

# ─── FLUJOS DE TRABAJO ────────────────────────────────────────────────────────

class FlujoTrabajo(Base):
    __tablename__ = "flujos_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    proceso = Column(String(150))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    pasos = relationship("PasoFlujo", back_populates="flujo")
    instancias = relationship("InstanciaFlujo", back_populates="flujo")

class PasoFlujo(Base):
    __tablename__ = "pasos_flujo"
    id = Column(Integer, primary_key=True)
    flujo_id = Column(Integer, ForeignKey("flujos_trabajo.id"))
    orden = Column(Integer, nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    responsable_rol = Column(String(50))
    dias_limite = Column(Integer, default=3)
    flujo = relationship("FlujoTrabajo", back_populates="pasos")

class InstanciaFlujo(Base):
    __tablename__ = "instancias_flujo"
    id = Column(Integer, primary_key=True)
    flujo_id = Column(Integer, ForeignKey("flujos_trabajo.id"))
    titulo = Column(String(200))
    paso_actual = Column(Integer, default=1)
    estado = Column(String(50), default="activo")
    iniciado_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_cierre = Column(DateTime)
    flujo = relationship("FlujoTrabajo", back_populates="instancias")

# ─── RIESGOS ──────────────────────────────────────────────────────────────────

class Riesgo(Base):
    __tablename__ = "riesgos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    proceso = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=False)
    causa = Column(Text)
    consecuencia = Column(Text)
    probabilidad = Column(Integer)  # 1-5
    impacto = Column(Integer)  # 1-5
    nivel = Column(Enum(NivelRiesgo))
    control_existente = Column(Text)
    accion_propuesta = Column(Text)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_evaluacion = Column(DateTime, default=datetime.utcnow)
    fecha_revision = Column(DateTime)
    activo = Column(Boolean, default=True)
    responsable = relationship("Usuario")

# ─── INDICADORES ──────────────────────────────────────────────────────────────

class Indicador(Base):
    __tablename__ = "indicadores"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    nombre = Column(String(200), nullable=False)
    proceso = Column(String(150))
    formula = Column(Text)
    unidad = Column(String(50))
    meta = Column(Float)
    meta_minima = Column(Float)
    meta_maxima = Column(Float)
    frecuencia = Column(String(50))  # mensual, trimestral, anual
    responsable_id = Column(Integer, ForeignKey("usuarios.id"))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    mediciones = relationship("MedicionIndicador", back_populates="indicador")
    responsable = relationship("Usuario")

class MedicionIndicador(Base):
    __tablename__ = "mediciones_indicador"
    id = Column(Integer, primary_key=True)
    indicador_id = Column(Integer, ForeignKey("indicadores.id"))
    valor = Column(Float, nullable=False)
    periodo = Column(String(20))  # "2024-01", "2024-Q1"
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    registrado_por = Column(Integer, ForeignKey("usuarios.id"))
    observacion = Column(Text)
    indicador = relationship("Indicador", back_populates="mediciones")

# ─── TALENTO HUMANO ───────────────────────────────────────────────────────────

class Empleado(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    documento = Column(String(30), unique=True)
    cargo = Column(String(100))
    area = Column(String(100))
    tipo_contrato = Column(String(50))
    fecha_ingreso = Column(DateTime)
    fecha_retiro = Column(DateTime)
    activo = Column(Boolean, default=True)
    rethus = Column(String(50))
    email = Column(String(150))
    telefono = Column(String(30))
    creado_en = Column(DateTime, default=datetime.utcnow)
    usuario = relationship("Usuario", back_populates="talento")
    capacitaciones = relationship("Capacitacion", back_populates="empleado")
    vencimientos   = relationship("VencimientoCurso", back_populates="empleado")

class Capacitacion(Base):
    __tablename__ = "capacitaciones"
    id = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"))
    tema = Column(String(200), nullable=False)
    tipo = Column(String(100))
    fecha = Column(DateTime)
    horas = Column(Float)
    institucion = Column(String(200))
    aprobado = Column(Boolean, default=True)
    certificado = Column(String(300))
    empleado = relationship("Empleado", back_populates="capacitaciones")

class VencimientoCurso(Base):
    __tablename__ = "vencimientos_cursos"
    id = Column(Integer, primary_key=True, index=True)
    empleado_id      = Column(Integer, ForeignKey("empleados.id"))
    nombre_curso     = Column(String(200), nullable=False)
    categoria        = Column(String(100))
    fecha_realizacion = Column(DateTime)
    fecha_vencimiento = Column(DateTime, nullable=False)
    institucion      = Column(String(200))
    observacion      = Column(Text)
    activo           = Column(Boolean, default=True)
    creado_en        = Column(DateTime, default=datetime.utcnow)
    empleado         = relationship("Empleado", back_populates="vencimientos")

class CapacitacionPlan(Base):
    __tablename__ = "capacitaciones_plan"
    id = Column(Integer, primary_key=True, index=True)
    titulo           = Column(String(200), nullable=False)
    descripcion      = Column(Text)
    tipo             = Column(String(100))
    capacitador      = Column(String(200))
    institucion_cap  = Column(String(200))
    duracion_horas   = Column(Float, default=0)
    modalidad        = Column(String(50), default="presencial")
    lugar            = Column(String(200))
    responsable_id   = Column(Integer, ForeignKey("usuarios.id"))
    creado_por       = Column(Integer, ForeignKey("usuarios.id"))
    fecha_programada = Column(DateTime)
    activo           = Column(Boolean, default=True)
    estado           = Column(String(50), default="programada")
    creado_en        = Column(DateTime, default=datetime.utcnow)
    asistentes  = relationship("CapacitacionAsistente", back_populates="capacitacion")
    responsable = relationship("Usuario", foreign_keys=[responsable_id])
    creador     = relationship("Usuario", foreign_keys=[creado_por])

class CapacitacionAsistente(Base):
    __tablename__ = "capacitaciones_asistentes"
    id = Column(Integer, primary_key=True)
    capacitacion_id = Column(Integer, ForeignKey("capacitaciones_plan.id"))
    empleado_id     = Column(Integer, ForeignKey("empleados.id"))
    asistio         = Column(Boolean, default=None)
    aprobado        = Column(Boolean, default=None)
    nota            = Column(Float, nullable=True)
    capacitacion = relationship("CapacitacionPlan", back_populates="asistentes")
    empleado     = relationship("Empleado")

# ─── PQRS ─────────────────────────────────────────────────────────────────────

class PQRS(Base):
    __tablename__ = "pqrs"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    tipo = Column(Enum(TipoPQRS), nullable=False)
    estado = Column(Enum(EstadoPQRS), default=EstadoPQRS.abierta)
    nombre_solicitante = Column(String(150))
    email_solicitante = Column(String(150))
    telefono_solicitante = Column(String(30))
    servicio = Column(String(150))
    descripcion = Column(Text, nullable=False)
    respuesta = Column(Text)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    fecha_limite = Column(DateTime)
    fecha_cierre = Column(DateTime)
    asignado_a = Column(Integer, ForeignKey("usuarios.id"))
    prioridad = Column(String(20), default="normal")
    asignado = relationship("Usuario")
# ─── COMITÉS ──────────────────────────────────────────────────────────────────

class TipoComite(str, enum.Enum):
    calidad = "calidad"
    seguridad_paciente = "seguridad_paciente"
    etica = "etica"
    iaas = "iaas"
    farmacia = "farmacia"
    historias_clinicas = "historias_clinicas"
    otro = "otro"

class EstadoComite(str, enum.Enum):
    programado = "programado"
    realizado = "realizado"
    cancelado = "cancelado"

class Comite(Base):
    __tablename__ = "comites"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoComite), nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    periodicidad = Column(String(50))  # mensual, bimestral, trimestral
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actas = relationship("ActaComite", back_populates="comite")

class ActaComite(Base):
    __tablename__ = "actas_comite"
    id = Column(Integer, primary_key=True, index=True)
    comite_id = Column(Integer, ForeignKey("comites.id"), nullable=False)
    numero_acta = Column(String(50))
    fecha = Column(DateTime, nullable=False)
    lugar = Column(String(200))
    orden_dia = Column(Text)
    desarrollo = Column(Text)
    estado = Column(Enum(EstadoComite), default=EstadoComite.programado)
    quorum = Column(Boolean, default=False)
    archivo_nombre = Column(String(300))
    archivo_ruta = Column(String(500))
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    comite = relationship("Comite", back_populates="actas")
    asistentes = relationship("AsistenteComite", back_populates="acta")
    compromisos = relationship("CompromisoComite", back_populates="acta")
    creador = relationship("Usuario", foreign_keys=[creado_por])

class AsistenteComite(Base):
    __tablename__ = "asistentes_comite"
    id = Column(Integer, primary_key=True)
    acta_id = Column(Integer, ForeignKey("actas_comite.id"))
    nombre = Column(String(150), nullable=False)
    cargo = Column(String(100))
    area = Column(String(100))
    cedula = Column(String(30))
    email = Column(String(150))
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)
    rol_en_acta = Column(String(50), default="asistente")
    token_firma = Column(String(100))
    firma = Column(Boolean, default=False)
    acta = relationship("ActaComite", back_populates="asistentes")
    empleado = relationship("Empleado", foreign_keys=[empleado_id])

class CompromisoComite(Base):
    __tablename__ = "compromisos_comite"
    id = Column(Integer, primary_key=True, index=True)
    acta_id = Column(Integer, ForeignKey("actas_comite.id"))
    descripcion = Column(Text, nullable=False)
    responsable = Column(String(150))
    fecha_limite = Column(DateTime)
    estado = Column(String(30), default="pendiente")  # pendiente, cumplido, vencido
    observacion = Column(Text)
    acta = relationship("ActaComite", back_populates="compromisos")

# ─── PERMISOS Y ROLES PERSONALIZADOS ─────────────────────────────────────────

class PermisoUsuario(Base):
    __tablename__ = "permisos_usuario"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    modulo = Column(String(50), nullable=False)
    puede_ver    = Column(Boolean, default=True)
    puede_crear  = Column(Boolean, default=False)
    puede_editar = Column(Boolean, default=False)
    puede_aprobar = Column(Boolean, default=False)
    puede_eliminar = Column(Boolean, default=False)

# ─── AMBULANCIAS Y PREOPERACIONAL ─────────────────────────────────────────────

class EstadoVehiculo(str, enum.Enum):
    activo    = "activo"
    inactivo  = "inactivo"
    taller    = "taller"

class Ambulancia(Base):
    __tablename__ = "ambulancias"
    id = Column(Integer, primary_key=True, index=True)
    placa         = Column(String(20), unique=True, nullable=False)
    numero_interno= Column(String(20))
    marca         = Column(String(100))
    modelo        = Column(String(100))
    anio          = Column(Integer)
    tipo          = Column(String(50))   # TAB, TAM, TAN, etc.
    estado        = Column(Enum(EstadoVehiculo), default=EstadoVehiculo.activo)
    kilometraje   = Column(Integer, default=0)
    foto          = Column(String(300))
    activo        = Column(Boolean, default=True)
    creado_en     = Column(DateTime, default=datetime.utcnow)
    conductores   = relationship("ConductorAmbulancia", back_populates="ambulancia")
    preoperacionales = relationship("Preoperacional", back_populates="ambulancia")

class ConductorAmbulancia(Base):
    __tablename__ = "conductores_ambulancia"
    id = Column(Integer, primary_key=True, index=True)
    ambulancia_id = Column(Integer, ForeignKey("ambulancias.id"))
    nombres       = Column(String(100), nullable=False)
    apellidos     = Column(String(100), nullable=False)
    documento     = Column(String(30), unique=True)
    licencia      = Column(String(50))
    categoria_licencia = Column(String(20))
    vencimiento_licencia = Column(DateTime)
    telefono      = Column(String(30))
    email         = Column(String(150))
    activo        = Column(Boolean, default=True)
    creado_en     = Column(DateTime, default=datetime.utcnow)
    ambulancia    = relationship("Ambulancia", back_populates="conductores")
    preoperacionales = relationship("Preoperacional", back_populates="conductor")

class Preoperacional(Base):
    __tablename__ = "preoperacionales"
    id = Column(Integer, primary_key=True, index=True)
    ambulancia_id = Column(Integer, ForeignKey("ambulancias.id"))
    conductor_id  = Column(Integer, ForeignKey("conductores_ambulancia.id"))
    fecha         = Column(DateTime, default=datetime.utcnow)
    turno         = Column(String(20))  # manana, tarde, noche
    kilometraje_inicio = Column(Integer)
    # Ítems de inspección (True=OK, False=NOK, None=N/A)
    # MOTOR Y FLUIDOS
    nivel_aceite      = Column(String(10))
    nivel_agua        = Column(String(10))
    nivel_combustible = Column(String(10))
    nivel_liquido_frenos = Column(String(10))
    # LUCES
    luces_delanteras  = Column(String(10))
    luces_traseras    = Column(String(10))
    luces_emergencia  = Column(String(10))
    sirena            = Column(String(10))
    # LLANTAS
    llanta_delantera_der = Column(String(10))
    llanta_delantera_izq = Column(String(10))
    llanta_trasera_der   = Column(String(10))
    llanta_trasera_izq   = Column(String(10))
    llanta_repuesto      = Column(String(10))
    # SEGURIDAD
    cinturones        = Column(String(10))
    extintores_amb    = Column(String(10))
    botiquin          = Column(String(10))
    camilla           = Column(String(10))
    oxigeno           = Column(String(10))
    # DOCUMENTOS
    soat              = Column(String(10))
    tecnomecanica     = Column(String(10))
    tarjeta_operacion = Column(String(10))
    # GENERAL
    carroceria        = Column(String(10))
    limpieza          = Column(String(10))
    observaciones     = Column(Text)
    firma_conductor   = Column(Text)   # base64 imagen firma
    firmado           = Column(Boolean, default=False)
    ambulancia  = relationship("Ambulancia", back_populates="preoperacionales")
    conductor   = relationship("ConductorAmbulancia", back_populates="preoperacionales")

# ─── ACTAS COMITÉ: FIRMAS Y BLOQUEO ──────────────────────────────────────────

class FirmaActa(Base):
    __tablename__ = "firmas_acta"
    id = Column(Integer, primary_key=True)
    acta_id = Column(Integer, ForeignKey("actas_comite.id"))
    nombre = Column(String(150))
    cargo  = Column(String(100))
    rol_en_acta = Column(String(30), default="integrante")  # presidente, secretario, integrante
    firma_imagen = Column(Text)   # base64
    comentario   = Column(Text)
    valida       = Column(Boolean, default=True)  # True=aprueba, False=no viable
    fecha_firma  = Column(DateTime, default=datetime.utcnow)
    acta         = relationship("ActaComite")

# ─── SST ─────────────────────────────────────────────────────────────────────

class TipoInspeccion(str, enum.Enum):
    extintor  = "extintor"
    botiquin  = "botiquin"
    epp       = "epp"
    general   = "general"

class InspeccionSST(Base):
    __tablename__ = "inspecciones_sst"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoInspeccion), nullable=False)
    ubicacion = Column(String(200))
    fecha     = Column(DateTime, default=datetime.utcnow)
    realizado_por = Column(Integer, ForeignKey("usuarios.id"))
    observaciones = Column(Text)
    estado    = Column(String(20), default="conforme")  # conforme, no_conforme
    creado_en = Column(DateTime, default=datetime.utcnow)
    evidencias = relationship("EvidenciaInspeccion", back_populates="inspeccion")
    items      = relationship("ItemInspeccion", back_populates="inspeccion")
    realizado  = relationship("Usuario", foreign_keys=[realizado_por])

class ItemInspeccion(Base):
    __tablename__ = "items_inspeccion"
    id = Column(Integer, primary_key=True)
    inspeccion_id = Column(Integer, ForeignKey("inspecciones_sst.id"))
    descripcion = Column(String(200))
    resultado   = Column(String(20))  # ok, nok, na
    observacion = Column(Text)
    inspeccion  = relationship("InspeccionSST", back_populates="items")

class EvidenciaInspeccion(Base):
    __tablename__ = "evidencias_inspeccion"
    id = Column(Integer, primary_key=True)
    inspeccion_id = Column(Integer, ForeignKey("inspecciones_sst.id"))
    archivo_nombre = Column(String(300))
    archivo_ruta   = Column(String(500))
    inspeccion     = relationship("InspeccionSST", back_populates="evidencias")

class TipoCapacitacion(str, enum.Enum):
    evaluacion    = "evaluacion"
    socializacion = "socializacion"

class CapacitacionSST(Base):
    __tablename__ = "capacitaciones_sst"
    id = Column(Integer, primary_key=True, index=True)
    tema   = Column(String(200), nullable=False)
    tipo   = Column(Enum(TipoCapacitacion), default=TipoCapacitacion.evaluacion)
    fecha  = Column(DateTime)
    area   = Column(String(100))
    instructor = Column(String(150))
    total_asistentes  = Column(Integer, default=0)
    certificado_ruta  = Column(String(500))   # para socializacion
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en  = Column(DateTime, default=datetime.utcnow)
    preguntas  = relationship("PreguntaCapacitacion", back_populates="capacitacion")
    respuestas = relationship("RespuestaCapacitacion", back_populates="capacitacion")
    creador    = relationship("Usuario", foreign_keys=[creado_por])

class PreguntaCapacitacion(Base):
    __tablename__ = "preguntas_capacitacion"
    id = Column(Integer, primary_key=True)
    capacitacion_id = Column(Integer, ForeignKey("capacitaciones_sst.id"))
    pregunta    = Column(Text, nullable=False)
    respuesta_correcta = Column(String(300))
    capacitacion = relationship("CapacitacionSST", back_populates="preguntas")

class RespuestaCapacitacion(Base):
    __tablename__ = "respuestas_capacitacion"
    id = Column(Integer, primary_key=True)
    capacitacion_id = Column(Integer, ForeignKey("capacitaciones_sst.id"))
    nombre_participante = Column(String(150))
    respuestas_json     = Column(Text)   # JSON {pregunta_id: respuesta}
    correctas           = Column(Integer, default=0)
    total               = Column(Integer, default=0)
    porcentaje          = Column(Float, default=0.0)
    fecha               = Column(DateTime, default=datetime.utcnow)
    capacitacion = relationship("CapacitacionSST", back_populates="respuestas")

class CondicionInsegura(Base):
    __tablename__ = "condiciones_inseguras"
    id = Column(Integer, primary_key=True, index=True)
    descripcion   = Column(Text, nullable=False)
    area_afectada = Column(String(150))
    ubicacion     = Column(String(200))
    riesgo        = Column(String(50), default="medio")  # bajo, medio, alto, critico
    estado        = Column(String(30), default="abierta")  # abierta, en_gestion, cerrada
    reportado_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha_reporte = Column(DateTime, default=datetime.utcnow)
    fecha_cierre  = Column(DateTime)
    evidencia_ruta = Column(String(500))
    accion_tomada  = Column(Text)
    reportado      = relationship("Usuario", foreign_keys=[reportado_por])

# ─── GESTIÓN AMBIENTAL ───────────────────────────────────────────────────────

class TipoResiduo(str, enum.Enum):
    aprovechable     = "aprovechable"
    no_aprovechable  = "no_aprovechable"
    biologico        = "biologico"
    peligroso        = "peligroso"
    especial         = "especial"
    quimico          = "quimico"

class RegistroResiduo(Base):
    __tablename__ = "registros_residuos"
    id = Column(Integer, primary_key=True, index=True)
    tipo    = Column(Enum(TipoResiduo), nullable=False)
    subtipo = Column(String(100))   # papel, cartón, plástico, vidrio…
    peso_kg = Column(Float, nullable=False)
    unidad  = Column(String(20), default="kg")
    mes     = Column(String(7))    # "2025-01"
    area_generadora = Column(String(200))  # empresa de gestión
    numero_manifiesto = Column(String(100))
    registrado_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha          = Column(DateTime, default=datetime.utcnow)
    observaciones  = Column(Text)
    registrado     = relationship("Usuario", foreign_keys=[registrado_por])

# ─── TECNOVIGILANCIA / EQUIPOS BIOMÉDICOS ────────────────────────────────────

class EquipoBiomedico(Base):
    __tablename__ = "equipos_biomedicos"
    id = Column(Integer, primary_key=True, index=True)
    codigo_qr    = Column(String(100), unique=True, index=True)
    nombre       = Column(String(200), nullable=False)
    marca        = Column(String(100))
    modelo       = Column(String(100))
    serie        = Column(String(100))
    area         = Column(String(100))
    ubicacion    = Column(String(200))
    fecha_compra = Column(DateTime)
    vida_util    = Column(Integer)   # años
    estado       = Column(String(30), default="operativo")
    foto         = Column(String(300))
    activo       = Column(Boolean, default=True)
    creado_en    = Column(DateTime, default=datetime.utcnow)
    mantenimientos = relationship("MantenimientoBiomedico", back_populates="equipo")

class MantenimientoBiomedico(Base):
    __tablename__ = "mantenimientos_biomedicos"
    id = Column(Integer, primary_key=True, index=True)
    equipo_id   = Column(Integer, ForeignKey("equipos_biomedicos.id"))
    tipo        = Column(String(30), default="preventivo")  # preventivo, correctivo, calibracion
    fecha       = Column(DateTime, default=datetime.utcnow)
    tecnico     = Column(String(150))
    descripcion = Column(Text)
    hallazgos   = Column(Text)
    acciones    = Column(Text)
    proxima_fecha = Column(DateTime)
    firma_tecnico   = Column(Text)  # base64
    firmado         = Column(Boolean, default=False)
    evidencia_ruta  = Column(String(500))
    realizado_por   = Column(Integer, ForeignKey("usuarios.id"))
    creado_en       = Column(DateTime, default=datetime.utcnow)
    equipo          = relationship("EquipoBiomedico", back_populates="mantenimientos")
    realizado       = relationship("Usuario", foreign_keys=[realizado_por])

# ─── SISTEMAS / MANTENIMIENTO PCs ────────────────────────────────────────────

class EquipoSistemas(Base):
    __tablename__ = "equipos_sistemas"
    id = Column(Integer, primary_key=True, index=True)
    nombre    = Column(String(200), nullable=False)
    tipo      = Column(String(50))   # desktop, laptop, servidor, impresora
    marca     = Column(String(100))
    modelo    = Column(String(100))
    serie     = Column(String(100))
    area      = Column(String(100))
    usuario_asignado = Column(String(150))
    ip        = Column(String(30))
    so        = Column(String(100))   # Sistema operativo
    estado    = Column(String(30), default="activo")
    activo    = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    mantenimientos = relationship("MantenimientoSistemas", back_populates="equipo")

class MantenimientoSistemas(Base):
    __tablename__ = "mantenimientos_sistemas"
    id = Column(Integer, primary_key=True, index=True)
    equipo_id    = Column(Integer, ForeignKey("equipos_sistemas.id"))
    tipo         = Column(String(30), default="preventivo")
    fecha        = Column(DateTime, default=datetime.utcnow)
    tecnico      = Column(String(150))
    descripcion  = Column(Text)
    actividades  = Column(Text)
    observaciones= Column(Text)
    firma_tecnico  = Column(Text)   # base64
    firma_usuario  = Column(Text)   # base64 del usuario del equipo
    firmado_tecnico  = Column(Boolean, default=False)
    firmado_usuario  = Column(Boolean, default=False)
    realizado_por    = Column(Integer, ForeignKey("usuarios.id"))
    creado_en        = Column(DateTime, default=datetime.utcnow)
    equipo     = relationship("EquipoSistemas", back_populates="mantenimientos")
    realizado  = relationship("Usuario", foreign_keys=[realizado_por])

# ─── AMBIENTE FÍSICO ─────────────────────────────────────────────────────────

class MantenimientoAmbiente(Base):
    __tablename__ = "mantenimientos_ambiente"
    id = Column(Integer, primary_key=True, index=True)
    area        = Column(String(150), nullable=False)
    tipo_trabajo= Column(String(150))  # pintura, plomería, eléctrico…
    descripcion = Column(Text)
    fecha_programada = Column(DateTime)
    fecha_ejecucion  = Column(DateTime)
    responsable      = Column(String(150))
    contratista      = Column(String(150))
    estado      = Column(String(30), default="programado")  # programado, en_ejecucion, completado
    observaciones = Column(Text)
    evidencias    = relationship("EvidenciaAmbiente", back_populates="mantenimiento")
    creado_por    = Column(Integer, ForeignKey("usuarios.id"))
    creado_en     = Column(DateTime, default=datetime.utcnow)
    creado        = relationship("Usuario", foreign_keys=[creado_por])

class EvidenciaAmbiente(Base):
    __tablename__ = "evidencias_ambiente"
    id = Column(Integer, primary_key=True)
    mantenimiento_id = Column(Integer, ForeignKey("mantenimientos_ambiente.id"))
    archivo_nombre   = Column(String(300))
    archivo_ruta     = Column(String(500))
    descripcion      = Column(Text)
    fecha            = Column(DateTime, default=datetime.utcnow)
    mantenimiento    = relationship("MantenimientoAmbiente", back_populates="evidencias")

# ─── SEGURIDAD DEL PACIENTE ──────────────────────────────────────────────────

class RondaSeguridad(Base):
    __tablename__ = "rondas_seguridad"
    id = Column(Integer, primary_key=True, index=True)
    evaluador     = Column(String(150), nullable=False)
    servicio      = Column(String(150), nullable=False)
    fecha         = Column(DateTime, default=datetime.utcnow)
    # Sección: Infraestructura física
    pisos_paredes       = Column(String(5))
    ventilacion         = Column(String(5))
    iluminacion         = Column(String(5))
    antideslizantes     = Column(String(5))
    privacidad          = Column(String(5))
    senalizacion        = Column(String(5))
    techo               = Column(String(5))
    condiciones_aseo    = Column(String(5))
    espacios_humanizados= Column(String(5))
    # Sección: Gestión documental
    historia_clinica    = Column(String(5))
    rotulacion          = Column(String(5))
    formatos_vigentes   = Column(String(5))
    consentimiento      = Column(String(5))
    registro_hc         = Column(String(5))
    identificacion_riesgos = Column(String(5))
    reporte_eventos     = Column(String(5))
    entorno_seguro      = Column(String(5))
    identificacion_paciente = Column(String(5))
    # Sección: Medicamentos
    almacenamiento_med  = Column(String(5))
    prescripcion        = Column(String(5))
    conciliacion_med    = Column(String(5))
    dispensacion        = Column(String(5))
    correctos_med       = Column(String(5))
    # Sección: Equipos biomédicos
    equipos_funcionando = Column(String(5))
    mantenimiento_prev  = Column(String(5))
    calibracion         = Column(String(5))
    ficha_uso           = Column(String(5))
    entrenamiento_eq    = Column(String(5))
    limpieza_equipos    = Column(String(5))
    almacenamiento_disp = Column(String(5))
    # Sección: Recurso humano
    personal_completo   = Column(String(5))
    carnet_visible      = Column(String(5))
    politica_seguridad  = Column(String(5))
    cultura_reporte     = Column(String(5))
    supervision         = Column(String(5))
    # Sección: Prevención infecciones
    bioseguridad        = Column(String(5))
    elementos_lavado    = Column(String(5))
    rotulacion_mezclas  = Column(String(5))
    limpieza_areas      = Column(String(5))
    segregacion_residuos= Column(String(5))
    epp_aislamiento     = Column(String(5))
    # Paquetes instruccionales
    escala_braden       = Column(String(5))
    prevencion_ulceras  = Column(String(5))
    higienizacion_manos = Column(String(5))
    elementos_lavado2   = Column(String(5))
    educacion_familia   = Column(String(5))
    mecanismos_aislamiento = Column(String(5))
    prevencion_infecciones = Column(String(5))
    identificacion_muestras = Column(String(5))
    identificacion_usuarios = Column(String(5))
    consentimiento_pac  = Column(String(5))
    caidas              = Column(String(5))
    maternidad_segura   = Column(String(5))
    reporte_gestion     = Column(String(5))
    # Entrevista usuario
    educacion_seguridad = Column(String(5))
    educacion_humanizacion = Column(String(5))
    ciclo_atencion      = Column(String(5))
    # Entrevista colaborador (texto libre)
    pregunta1 = Column(Text)
    pregunta2 = Column(Text)
    pregunta3 = Column(Text)
    pregunta4 = Column(Text)
    pregunta5 = Column(Text)
    pregunta6 = Column(Text)
    pregunta7 = Column(Text)
    pregunta8 = Column(Text)
    # Resultado
    total_items    = Column(Integer, default=0)
    items_cumple   = Column(Integer, default=0)
    porcentaje     = Column(Float, default=0.0)
    observaciones  = Column(Text)
    firma_evaluador= Column(Text)   # base64
    firma_receptor = Column(Text)   # base64
    firmado        = Column(Boolean, default=False)
    creado_por     = Column(Integer, ForeignKey("usuarios.id"))
    creado_en      = Column(DateTime, default=datetime.utcnow)
    creado         = relationship("Usuario", foreign_keys=[creado_por])

class PaqueteInstruccional(Base):
    __tablename__ = "paquetes_instruccionales"
    id = Column(Integer, primary_key=True, index=True)
    nombre     = Column(String(200), nullable=False)
    tipo       = Column(String(100))  # ulceras, caidas, infecciones, medicamentos...
    descripcion= Column(Text)
    objetivo   = Column(Text)
    contenido  = Column(Text)
    version    = Column(String(20), default="1.0")
    vigente    = Column(Boolean, default=True)
    archivo_ruta = Column(String(500))
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en  = Column(DateTime, default=datetime.utcnow)
    creado     = relationship("Usuario", foreign_keys=[creado_por])
