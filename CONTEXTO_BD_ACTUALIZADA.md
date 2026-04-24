# CONTEXTO ACTUALIZADO — Control de Labores
# BD real vs diseño original: cambios aplicados
# Válido para: FastAPI (routers actuales) + Flutter (modelos Drift + providers)
# Fecha: 2026-04-24

---

## 1. ESQUEMA REAL DE LA BASE DE DATOS

Host: 186.64.118.105:3306 | DB: agrico24_control_labores | User: agrico24_mbravo

### Tablas de catálogo (solo lectura desde la app)

```sql
estado              id | nombre                         → 1=activo, 2=inactivo
tipo_personal       id | nombre                         → 1=propio, 2=contratista
tipo_rendimiento    id | nombre                         → 1=individual, 2=grupal
ceco_tipo           id | nombre                         → tipos de CECO
porcentaje_contratista id | porcentaje                  → porcentajes para contratistas
estado_actividad    id | nombre | orden                 → 1=creada,2=revisada,3=aprobada,4=finalizada
estado_permiso      id | nombre                         → estados de permisos de trabajadores
unidad_medida       id | nombre VARCHAR(50)             → catálogo global (sin FKs)
nombre_dia          id | nombre VARCHAR(25)             → lunes, martes, ..., domingo
```

### Tablas tenant / acceso

```sql
empresa
  id, razon_social, rut, email_contacto, plan,
  estado_id FK→estado,
  created_at

campo
  id, empresa_id FK→empresa, nombre, ubicacion,
  estado_id FK→estado,
  created_at

rol
  id, nombre VARCHAR(45)                → 'admin_empresa','supervisor','consultor'

usuario
  id, empresa_id FK→empresa,
  nombre, usuario VARCHAR(25),
  email, password_hash,
  rol_id FK→rol,
  estado_id FK→estado,
  created_at

usuario_campo
  id, usuario_id FK→usuario, campo_id FK→campo
```

### Tablas de configuración por empresa

```sql
horas_por_dia                           ← horas de jornada configuradas por día/empresa
  id, empresa_id FK→empresa,
  nombredia_id FK→nombre_dia,
  horas_dias FLOAT NOT NULL
```

### Tablas maestros por campo/empresa

```sql
labor                                   ← DE EMPRESA, con unidad por defecto
  id, empresa_id FK→empresa,
  nombre VARCHAR(100),
  unidad_id FK→unidad_medida NULL,      ← unidad sugerida para esta labor
  estado_id FK→estado

contratista
  id, rut VARCHAR(12), nombre VARCHAR(45),
  campo_id FK→campo,
  estado_id FK→estado

trabajador
  id, campo_id FK→campo,
  nombre VARCHAR(100), rut VARCHAR(12) NULL,
  tipotrabajador_id FK→tipo_personal,
  contratista_id FK→contratista NULL,
  porcentajecontratista_id FK→porcentaje_contratista NULL,
  estado_id FK→estado,
  created_at

ceco
  id, campo_id FK→campo,
  cecotipo_id FK→ceco_tipo,             ← nombre real de la columna
  nombre VARCHAR(100),
  estado_id FK→estado

permiso
  id, trabajador_id FK→trabajador,
  fecha DATE, horas_permiso FLOAT,
  estadopermiso_id FK→estado_permiso
```

### Tablas transaccionales

```sql
actividad
  id, campo_id FK→campo, usuario_id FK→usuario,
  fecha DATE,
  tipopersonal_id FK→tipo_personal,
  personal_id FK→contratista NULL,      ← contratista asignado (solo si tipo=contratista)
  tiporendimiento_id FK→tipo_rendimiento,
  labor_id FK→labor,
  unidad_medida_id FK→unidad_medida,
  cecotipo_id FK→ceco_tipo,             ← denormalizado desde ceco.cecotipo_id
  ceco_id FK→ceco,
  tarifa DECIMAL(10,2),
  hora_inicio TIME NOT NULL, hora_fin TIME NOT NULL,   ← ambos obligatorios
  estado_id FK→estado_actividad (SmallInteger)

actividad_trabajador
  id, actividad_id FK→actividad, trabajador_id FK→trabajador

rendimiento                             ← rendimiento individual (tipo_rendimiento=1)
  id, actividad_id FK→actividad, trabajador_id FK→trabajador,
  cantidad DECIMAL(10,2),
  horas_trabajadas FLOAT NOT NULL,      ← se precalcula al crear, editable vía PATCH
  horas_extras FLOAT NOT NULL DEFAULT 0,
  porcentajecontratista_id FK→porcentaje_contratista NULL,
  created_at

rendimiento_grupal                      ← rendimiento grupal (tipo_rendimiento=2), 1:1 con actividad
  id, actividad_id FK→actividad UNIQUE,
  cantidad_trabajadores INT NOT NULL,
  rendimiento_total FLOAT NOT NULL,
  porcentajecontratista_id FK→porcentaje_contratista NULL,   ← NULL cuando es propio
  horas_trabajadas FLOAT NOT NULL,
  horas_extras FLOAT NOT NULL DEFAULT 0
```

---

## 2. REGLAS DE NEGOCIO CLAVE

**estado vs activo:** Todas las tablas usan `estado_id FK→estado`.
Filtrar activos = `WHERE estado_id = 1`. No existe campo `activo` en ninguna tabla.

**unidad_medida es catálogo global:** Solo tiene `id` y `nombre`. No pertenece a empresa
ni a labor. Es una lista maestra simple (ej: kg, caja, bandeja, jornal).

**Labor sugiere unidad:** `labor.unidad_id` es la unidad de medida sugerida para esa labor.
Flujo UX: usuario selecciona labor → sistema precarga `unidad_medida_id` con `labor.unidad_id`.
El usuario puede cambiarlo si lo desea. `unidad_id` puede ser NULL (sin sugerencia).

**Labor es de empresa:** Las labores son compartidas entre todos los campos de la misma empresa.
Filtrar por `empresa_id == current_user.empresa_id`.

**horas_trabajadas al crear:** Se calcula automáticamente en el backend:
```
horas_trabajadas = (hora_fin - hora_inicio) de la actividad en horas decimales
horas_extras     = max(0, horas_trabajadas - 8)
```
Nunca vienen del cliente al crear. Se calculan con `_calcular_horas(actividad)` y se guardan.
Pueden **editarse** vía `PATCH /rendimientos/{id}` o `PATCH /rendimientos/grupal/{id}`
enviando `horas_trabajadas` / `horas_extras` en el body.

**Rendimiento grupal:** 1:1 con actividad (una fila por actividad). Solo tiene sentido cuando
`actividad.tiporendimiento_id = 2`. En el individual hay N filas (una por trabajador).

**Contratista como entidad:** Trabajadores contratistas se vinculan a una empresa contratista
registrada en la tabla `contratista`. No es texto libre.

**Máquina de estados de actividad:** `creada(1) → revisada(2) → aprobada(3) → finalizada(4)`.
Solo se puede avanzar al siguiente orden, nunca retroceder. Solo se elimina si `estado_id == 1`.
Solo se pueden modificar/eliminar rendimientos si la actividad está en estado 1 o 2.

**Porcentaje contratista opcional en rendimientos:** Tanto `rendimiento.porcentajecontratista_id`
como `rendimiento_grupal.porcentajecontratista_id` aceptan NULL. Es `NOT NULL` solo
conceptualmente para actividades de contratistas (`actividad.tipopersonal_id=2`); para
actividades de propios (`tipopersonal_id=1`) el campo debe omitirse o enviarse como null.

**Permisos solo para propios:** La tabla `permiso` **únicamente aplica a trabajadores propios**
(`trabajador.tipotrabajador_id = 1`). Los trabajadores de contratistas NO tienen permisos.
Todos los endpoints `/permisos/*` (POST, GET lista, GET detalle, PATCH, DELETE) rechazan
con HTTP 400 si el trabajador es contratista, y el GET de lista filtra automáticamente
solo permisos de propios.

**tipo_personal y tipo_rendimiento son FK numéricas**, no ENUMs ni strings.
La app carga estos catálogos al iniciar sesión.

---

## 3. API ACTUAL (FastAPI, prefijo `/api/v1`)

### 3.1 Modelos SQLAlchemy — ver código fuente

Los modelos vigentes están en:
- `app/models/usuario.py` → `Estado`, `Rol`, `Empresa`, `Campo`, `Usuario`, `UsuarioCampo`
- `app/models/actividad.py` → catálogos (incluye `NombreDia`) + `Labor`, `Contratista`,
  `Trabajador`, `Ceco`, `UnidadMedida`, `HorasPorDia`, `Actividad`, `ActividadTrabajador`,
  `Rendimiento`, `RendimientoGrupal`, `Permiso`

### 3.2 Schemas Pydantic

Ubicados en `app/schemas/actividad.py` y `app/schemas/usuario.py`.
Schemas relevantes para rendimientos:
- `RendimientoCreate` / `RendimientoBulkCreate` — **sin** horas (se calculan)
- `RendimientoUpdate` — permite editar `cantidad`, `horas_trabajadas`, `horas_extras`, `porcentajecontratista_id`
- `RendimientoGrupalCreate` / `RendimientoGrupalUpdate` — mismo criterio
- `HorasTrabajadasItem` — vista unificada individual + grupal para reportes

### 3.3 Lógica de cálculo de horas

En `app/routers/rendimientos.py`:
```python
def _calcular_horas(actividad: Actividad) -> tuple[float, float]:
    if actividad.hora_inicio is None or actividad.hora_fin is None:
        return 0.0, 0.0
    inicio = datetime.combine(date_type.today(), actividad.hora_inicio)
    fin    = datetime.combine(date_type.today(), actividad.hora_fin)
    horas  = (fin - inicio).total_seconds() / 3600
    extras = max(0.0, horas - 8.0)
    return round(horas, 2), round(extras, 2)
```

### 3.4 Filtro activos — regla global

```python
.where(Tabla.estado_id == 1)   # NUNCA Tabla.activo == True (campo inexistente)
```

### 3.5 Endpoints implementados (prefijo `/api/v1`)

```
# Auth
POST /auth/login
GET  /auth/mis-campos
POST /auth/seleccionar-campo/{campo_id}

# Usuarios
POST  /usuarios
GET   /usuarios
GET   /usuarios/me
PATCH /usuarios/me/clave
GET   /usuarios/{id}
PATCH /usuarios/{id}

# Empresas / Campos / UsuarioCampo
POST /empresas
GET  /empresas
GET  /empresas/{id}
POST  /campos
GET   /campos
GET   /campos/{id}
PATCH /campos/{id}
POST   /usuario-campo
DELETE /usuario-campo/{id}

# Catálogos
GET /catalogos/tipos-personal
GET /catalogos/tipos-rendimiento
GET /catalogos/ceco-tipos
GET /catalogos/porcentajes-contratista
GET /catalogos/estados-actividad
GET /catalogos/unidades-medida

# Maestros — Contratistas
POST   /contratistas
GET    /contratistas?campo_id=
GET    /contratistas/{id}
PATCH  /contratistas/{id}
DELETE /contratistas/{id}

# Maestros — Trabajadores
POST   /trabajadores
GET    /trabajadores?campo_id=&tipotrabajador_id=
GET    /trabajadores/{id}
PATCH  /trabajadores/{id}
DELETE /trabajadores/{id}

# Maestros — CECOs
POST  /cecos
GET   /cecos?campo_id=
PATCH /cecos/{id}

# Maestros — Labores (de empresa)
POST  /labores
GET   /labores?empresa_id=
PATCH /labores/{id}

# Maestros — Unidades de medida (catálogo global)
GET /unidades-medida

# Configuración — Horas por día (filtra por empresa del usuario logueado)
GET /horas-por-dia                          → incluye nombre_dia anidado

# Indicadores (resúmenes diarios)
GET /indicadores/horas-diarias-propios?campo_id=&fecha_desde=&fecha_hasta=
    → suma horas_trabajadas de rendimiento por (trabajador, fecha)
    → filtros: tipopersonal_id=1, actividad.estado_id=1, usuario_id=logueado
    → compara contra horas_por_dia de la empresa (según día de la semana)
    → devuelve: horas_esperadas, diferencia, cumple (bool)

# Maestros — Permisos (SOLO trabajadores propios — tipotrabajador_id=1)
POST   /permisos                           → 400 si el trabajador es contratista
GET    /permisos?campo_id=&trabajador_id=  → filtra solo permisos de propios
GET    /permisos/{id}                      → 400 si el permiso es de contratista
PATCH  /permisos/{id}                      → 400 si el permiso es de contratista
DELETE /permisos/{id}                      → 400 si el permiso es de contratista

# Actividades
POST   /actividades                         → body incluye trabajador_ids
GET    /actividades?campo_id=&fecha_desde=&fecha_hasta=&estado_id=
GET    /actividades/{id}
PATCH  /actividades/{id}
DELETE /actividades/{id}                    → solo si estado_id == 1
POST   /actividades/{id}/trabajadores       → body: [trabajador_ids]
DELETE /actividades/{id}/trabajadores/{trabajador_id}
PATCH  /actividades/{id}/estado             → avanza una posición

# Rendimientos individuales
POST   /rendimientos/bulk
POST   /rendimientos
GET    /rendimientos?actividad_id=
PATCH  /rendimientos/{id}                   → ahora acepta horas_trabajadas / horas_extras
DELETE /rendimientos/{id}                   → solo si actividad.estado_id ∈ {1,2}

# Rendimientos grupales
POST   /rendimientos/grupal
GET    /rendimientos/grupal?actividad_id=
GET    /rendimientos/grupal/{id}
PATCH  /rendimientos/grupal/{id}            → acepta horas_trabajadas / horas_extras
DELETE /rendimientos/grupal/{id}            → solo si actividad.estado_id ∈ {1,2}

# Reporte horas trabajadas (propios, vista unificada individual + grupal)
GET /rendimientos/horas-trabajadas?campo_id=&fecha_desde=&fecha_hasta=
    → filtra: campo_id + usuario logueado + tipopersonal_id=1 + actividad.estado_id=1
    → incluye labor, ceco, hora_inicio, hora_fin
```

---

## 4. CAMBIOS REQUERIDOS EN FLUTTER (Drift + Providers)

### 4.1 app_database.dart — tablas

```dart
// Catálogos
class TiposPersonal extends Table {
  IntColumn get id     => integer()();
  TextColumn get nombre => text()();
  @override Set<Column> get primaryKey => {id};
}

class TiposRendimiento extends Table {
  IntColumn get id     => integer()();
  TextColumn get nombre => text()();
  @override Set<Column> get primaryKey => {id};
}

class CecoTipos extends Table {
  IntColumn get id     => integer()();
  TextColumn get nombre => text()();
  @override Set<Column> get primaryKey => {id};
}

class PorcentajesContratista extends Table {
  IntColumn get id          => integer()();
  RealColumn get porcentaje => real()();
  @override Set<Column> get primaryKey => {id};
}

// UnidadesMedida — catálogo global
class UnidadesMedida extends Table {
  IntColumn get id     => integer()();
  TextColumn get nombre => text()();
  @override Set<Column> get primaryKey => {id};
}

// Contratistas
class Contratistas extends Table {
  IntColumn get id       => integer()();
  IntColumn get campoId  => integer()();
  TextColumn get rut     => text()();
  TextColumn get nombre  => text()();
  IntColumn get estadoId => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Labores — empresa + unidad sugerida
class Labores extends Table {
  IntColumn get id       => integer()();
  IntColumn get empresaId => integer()();
  TextColumn get nombre  => text()();
  IntColumn get unidadId => integer().nullable()();
  IntColumn get estadoId => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Trabajadores
class Trabajadores extends Table {
  IntColumn get id                      => integer()();
  IntColumn get campoId                 => integer()();
  TextColumn get nombre                 => text()();
  TextColumn get rut                    => text().nullable()();
  IntColumn get tipotrabajadorId        => integer()();
  IntColumn get contratistaId           => integer().nullable()();
  IntColumn get porcentajecontratistaId => integer().nullable()();
  IntColumn get estadoId                => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Cecos — ojo: la columna se llama cecotipoId (no cecotopiId)
class Cecos extends Table {
  IntColumn get id         => integer()();
  IntColumn get campoId    => integer()();
  IntColumn get cecotipoId => integer()();
  TextColumn get nombre    => text()();
  IntColumn get estadoId   => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Actividades — hora_inicio/hora_fin NOT NULL, con personal_id + cecotipo_id
class Actividades extends Table {
  IntColumn get id                => integer().autoIncrement()();
  IntColumn get remoteId          => integer().nullable()();
  IntColumn get campoId           => integer()();
  IntColumn get usuarioId         => integer()();
  IntColumn get cecoId            => integer()();
  IntColumn get cecotipoId        => integer()();
  IntColumn get laborId           => integer()();
  IntColumn get unidadMedidaId    => integer()();
  IntColumn get estadoId          => integer().withDefault(const Constant(1))();
  DateTimeColumn get fecha        => dateTime()();
  IntColumn get tipopersonalId    => integer()();
  IntColumn get personalId        => integer().nullable()();
  IntColumn get tiporendimientoId => integer()();
  RealColumn get tarifa           => real()();
  TextColumn get horaInicio       => text()();
  TextColumn get horaFin          => text()();
  TextColumn get syncStatus       => textEnum<SyncStatus>()
      .withDefault(const Constant('pending'))();
  IntColumn get syncRetries       => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt    => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt    => dateTime().withDefault(currentDateAndTime)();
}

// Rendimientos individuales
class Rendimientos extends Table {
  IntColumn get id                       => integer().autoIncrement()();
  IntColumn get remoteId                 => integer().nullable()();
  IntColumn get actividadId              => integer()();
  IntColumn get trabajadorId             => integer()();
  RealColumn get cantidad                => real()();
  RealColumn get horasTrabajadas         => real().withDefault(const Constant(0.0))();
  RealColumn get horasExtras             => real().withDefault(const Constant(0.0))();
  IntColumn get porcentajecontratistaId  => integer().nullable()();
  TextColumn get syncStatus              => textEnum<SyncStatus>()
      .withDefault(const Constant('pending'))();
  DateTimeColumn get createdAt           => dateTime().withDefault(currentDateAndTime)();
}

// Rendimientos grupales (1:1 con actividad)
class RendimientosGrupales extends Table {
  IntColumn get id                       => integer().autoIncrement()();
  IntColumn get remoteId                 => integer().nullable()();
  IntColumn get actividadId              => integer()();
  IntColumn get cantidadTrabajadores     => integer()();
  RealColumn get rendimientoTotal        => real()();
  IntColumn get porcentajecontratistaId  => integer()();
  RealColumn get horasTrabajadas         => real()();
  RealColumn get horasExtras             => real().withDefault(const Constant(0.0))();
  TextColumn get syncStatus              => textEnum<SyncStatus>()
      .withDefault(const Constant('pending'))();
  DateTimeColumn get createdAt           => dateTime().withDefault(currentDateAndTime)();
}
```

### 4.2 @DriftDatabase actualizado

```dart
@DriftDatabase(tables: [
  // Catálogos
  TiposPersonal, TiposRendimiento, CecoTipos, PorcentajesContratista, EstadosActividad,
  UnidadesMedida,
  // Tenant
  Empresas, Campos, Usuarios,
  // Maestros
  Contratistas, Trabajadores, Cecos, Labores, Permisos,
  // Transaccional
  Actividades, ActividadTrabajadores, Rendimientos, RendimientosGrupales,
])
```

Incrementar `schemaVersion` y agregar migración que recrea las tablas modificadas
e incorpora `rendimientos_grupales`.

### 4.3 Providers

```dart
// Filtro activo → estadoId == 1 en todos los providers
.where((t) => t.estadoId.equals(1))

// Providers catálogo (cargan en login)
tiposPersonalProvider, tiposRendimientoProvider, cecoTiposProvider,
porcentajesContratistaProvider, unidadesMedidaProvider

// Providers de maestros
contratistasProvider(campoId)
trabajadoresProvider(campoId, tipotrabajadorId?)
cecosProvider(campoId)
laboresProvider(empresaId)
permisosProvider(trabajadorId)

// Providers transaccionales
actividadesProvider(campoId, filtros)
rendimientosProvider(actividadId)
rendimientoGrupalProvider(actividadId)    // nuevo
```

### 4.4 Lógica de horas en Flutter (registro local offline)

```dart
double calcularHorasTrabajadas(String horaInicio, String horaFin) {
  final pi = horaInicio.split(':');
  final pf = horaFin.split(':');
  final ini = Duration(hours: int.parse(pi[0]), minutes: int.parse(pi[1]));
  final fin = Duration(hours: int.parse(pf[0]), minutes: int.parse(pf[1]));
  final diff = fin - ini;
  return (diff.inMinutes / 60).clamp(0.0, 24.0);
}

double calcularHorasExtras(double horasTrabajadas) =>
    (horasTrabajadas - 8.0).clamp(0.0, 24.0);
```

### 4.5 Flujo UX CrearActividad

```
1. tipopersonal_id    → dropdown desde tiposPersonalProvider
2. ceco_id            → dropdown desde cecosProvider(campoId)
                        (al seleccionar, el backend toma cecotipo_id desde ceco.cecotipo_id)
3. labor_id           → dropdown desde laboresProvider(empresaId)
                        al seleccionar → precargar unidad_medida_id con labor.unidadId
4. unidad_medida_id   → dropdown desde unidadesMedidaProvider (precargado, editable)
5. tiporendimiento_id → dropdown desde tiposRendimientoProvider
6. tarifa             → campo numérico
7. fecha              → DatePicker
8. hora_inicio / hora_fin → TimePicker (OBLIGATORIOS, NOT NULL en BD)
9. trabajadores       → multi-select filtrado por tipotrabajadorId == tipopersonal_id
```

### 4.6 Sincronización de catálogos al login

```dart
await Future.wait([
  _sincronizarCatalogo('/catalogos/tipos-personal',          db.tiposPersonal),
  _sincronizarCatalogo('/catalogos/tipos-rendimiento',       db.tiposRendimiento),
  _sincronizarCatalogo('/catalogos/ceco-tipos',              db.cecoTipos),
  _sincronizarCatalogo('/catalogos/porcentajes-contratista', db.porcentajesContratista),
  _sincronizarCatalogo('/catalogos/estados-actividad',       db.estadosActividad),
  _sincronizarCatalogo('/catalogos/unidades-medida',         db.unidadesMedida),
  _sincronizarLabores('/labores?empresa_id=$empresaId',      db.labores),
]);
// Luego, ya con campo seleccionado:
_sincronizarMaestrosCampo(campoId);  // trabajadores, cecos, contratistas, permisos
```

---

## 5. NOTAS FINALES PARA CLAUDE CODE

- `activo` no existe en ninguna tabla — siempre usar `estado_id = 1` para activos.
- `unidad_medida` es catálogo global: solo `id` y `nombre`, sin FKs de empresa o labor.
- `labor.unidad_id` es sugerencia — puede ser NULL, el usuario puede cambiarla.
- `actividad.hora_inicio` y `actividad.hora_fin` son **NOT NULL** (TIME obligatorio).
- `actividad.cecotipo_id` se guarda denormalizado desde `ceco.cecotipo_id` al crear.
- `actividad.personal_id` es el `contratista_id` asignado; NULL si `tipopersonal_id=1` (propio).
- `horas_trabajadas` y `horas_extras` se **calculan** al crear rendimiento/rendimiento_grupal,
  pero pueden **editarse** vía PATCH — útil para ajustes manuales por parte del supervisor.
- `rendimiento` (individual, N por actividad) y `rendimiento_grupal` (1:1 con actividad) coexisten;
  el tipo depende de `actividad.tiporendimiento_id` (1=individual, 2=grupal).
- `tipo_personal` y `tipo_rendimiento` son IDs enteros, no strings ni ENUMs.
- En todos los routers FastAPI, los filtros de "activo" usan `estado_id == 1`.
- Rendimientos solo se pueden modificar/eliminar si la actividad está en estado 1 (creada) o 2 (revisada).
- La actividad solo se elimina si `estado_id == 1`.
- Reporte de horas trabajadas (`GET /rendimientos/horas-trabajadas`) filtra además por
  `tipopersonal_id=1` (propios) y `actividad.estado_id=1` (creada), y por `usuario_id`
  del usuario logueado.
- `horas_por_dia` configura las horas de jornada por día de la semana a nivel empresa
  (referencia `nombre_dia` como catálogo de días). El endpoint `GET /horas-por-dia`
  filtra automáticamente por la empresa del usuario logueado.
- Convención de `nombre_dia.id`: **1=lunes, 2=martes, ..., 7=domingo** (coincide con
  `date.isoweekday()` de Python).
- Indicadores: el resumen diario de horas trabajadas (propios) se calcula en la API, no
  en una vista MySQL — agrega `rendimiento` por `trabajador_id + fecha`, cruza con
  `horas_por_dia` según día de la semana y marca `cumple` cuando el total del día no
  excede las horas configuradas.
