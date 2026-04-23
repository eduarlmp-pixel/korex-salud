# QMS Salud 🏥
**Sistema de Gestión de Calidad para Hospitales, Clínicas y Laboratorios**

Inspirado en Kawak — construido en Python puro, deployable gratis en Render o Railway.

---

## Módulos incluidos

| Módulo | Descripción |
|---|---|
| 📊 Dashboard | KPIs, indicadores, acciones y PQRS en tiempo real |
| 📁 Documentos | Repositorio, versiones, aprobaciones (ISO 9001) |
| ✅ Auditorías | Plan, checklists, hallazgos, Res. 3100 / Joint Commission |
| 🔄 Mejora continua | Acciones correctivas/preventivas, PAMEC, avance % |
| ⚙️ Flujos de trabajo | BPM sin código, instancias activas |
| ⚠️ Riesgos | Mapa térmico FMEA, probabilidad × impacto |
| 📈 Indicadores | KPIs asistenciales, sparklines, alertas de meta |
| 👥 Talento humano | Expedientes, RETHUS, capacitaciones, SST |
| 💬 PQRS | Quejas, peticiones, eventos adversos, respuestas |

---

## Stack tecnológico

- **Backend:** FastAPI + Uvicorn
- **Base de datos:** SQLite (→ PostgreSQL en producción)
- **ORM:** SQLAlchemy
- **Templates:** Jinja2
- **Auth:** JWT con python-jose + bcrypt
- **Frontend:** HTML5 + CSS puro (sin npm, sin build)

---

## Instalación local

### 1. Clonar / copiar el proyecto

```bash
cd qms_salud
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Editar `.env` y cambiar `SECRET_KEY` por una clave segura:

```bash
SECRET_KEY=mi_clave_super_segura_de_al_menos_32_caracteres
```

### 5. Poblar la base de datos con datos de demo

```bash
python seed.py
```

### 6. Ejecutar el servidor

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Abrir en el navegador: **http://localhost:8000**

### Usuarios de demo

| Email | Contraseña | Rol |
|---|---|---|
| admin@qms.co | admin123 | Administrador |
| calidad@qms.co | calidad123 | Calidad |
| auditor@qms.co | auditor123 | Auditor |
| gestor@qms.co | gestor123 | Gestor |

---

## Deploy gratuito en Render.com

### Paso 1 — Subir a GitHub
```bash
git init
git add .
git commit -m "QMS Salud v1.0"
git remote add origin https://github.com/tu-usuario/qms-salud.git
git push -u origin main
```

### Paso 2 — Crear servicio en Render
1. Ir a [render.com](https://render.com) → **New Web Service**
2. Conectar tu repositorio de GitHub
3. Configurar:
   - **Build Command:** `pip install -r requirements.txt && python seed.py`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Agregar variables de entorno en Render:
   - `SECRET_KEY` = (clave aleatoria segura)
   - `DATABASE_URL` = `sqlite:///./qms_salud.db`
5. Clic en **Deploy**

### Deploy en Railway.app
1. Ir a [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Seleccionar tu repo
3. Railway detecta automáticamente el `Procfile`
4. Agregar las mismas variables de entorno
5. ¡Listo!

---

## Migrar a PostgreSQL (producción)

1. En Render/Railway, crear un servicio de PostgreSQL
2. Copiar la `DATABASE_URL` que proveen
3. Actualizar en las variables de entorno:
   ```
   DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db
   ```
4. Instalar el driver: agregar `psycopg2-binary==2.9.9` a `requirements.txt`

La app detecta automáticamente si usar SQLite o PostgreSQL.

---

## Estructura del proyecto

```
qms_salud/
├── main.py                 ← Entrada principal FastAPI
├── database.py             ← Conexión SQLAlchemy
├── models.py               ← Todos los modelos de BD
├── auth.py                 ← JWT + bcrypt
├── templates_config.py     ← Jinja2 compartido
├── seed.py                 ← Datos de demostración
├── requirements.txt
├── Procfile                ← Deploy Render/Railway
├── .env                    ← Variables de entorno
├── routers/
│   ├── auth_router.py      ← Login/logout
│   ├── dashboard.py        ← Dashboard principal
│   ├── documentos.py       ← Gestión documental
│   ├── auditorias.py       ← Auditorías e inspecciones
│   ├── mejora.py           ← Mejora continua
│   └── otros.py            ← Riesgos, Indicadores, Talento, PQRS, Flujos
├── templates/
│   ├── base.html           ← Layout con sidebar
│   ├── login.html
│   ├── dashboard.html
│   ├── documentos/
│   ├── auditorias/
│   ├── mejora/
│   ├── riesgos/
│   ├── indicadores/
│   ├── talento/
│   ├── pqrs/
│   └── flujos/
└── static/
    └── css/main.css        ← Estilos (tema oscuro profesional)
```

---

## API REST (bonus)

FastAPI genera documentación automática:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

---

## Próximos ajustes posibles

- [ ] Notificaciones por email (SendGrid / SMTP)
- [ ] Carga de archivos PDF a documentos
- [ ] Exportar informes a Excel/PDF
- [ ] Dashboard con gráficas Chart.js
- [ ] Módulo de proveedores
- [ ] Módulo de equipos biomédicos
- [ ] API REST completa para integración con HIS/LIS
- [ ] Multitenancy (varias instituciones)
