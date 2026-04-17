# CONTEXTO ACTUALIZADO — Control de Labores
# BD real vs diseño original: cambios aplicados
# Válido para: FastAPI (continuar routers) + Flutter (modelos Drift + providers)
# Fecha: 2026-04-16

---

## 1. ESQUEMA REAL DE LA BASE DE DATOS

Host: 200.73.20.99:35026 | DB: lahornilla_control_labores | User: lahornilla_mbravo

### Tablas de catálogo (solo lectura desde la app)

```sql
estado              id | nombre                         → 1=activo, 2=inactivo
tipo_personal       id | nombre                         → 1=propio, 2=contratista
tipo_rendimiento    id | nombre                         → 1=individual, 2=grupal
ceco_tipo           id | nombre                         → tipos de CECO
porcentaje_contratista id | porcentaje                  → porcentajes para contratistas
estado_actividad    id | nombre | orden                 → 1=creada,2=revisada,3=aprobada,4=finalizada
estado_permiso      id | nombre                         → estados de permisos de trabajadores
especie             id | nombre | caja_equivalente
variedad            id | nombre | especie_id
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

usuario
  id, empresa_id FK→empresa,
  nombre, usuario VARCHAR(25),
  email, password_hash,
  rol ENUM('admin_empresa','supervisor','consultor'),
  estado_id FK→estado,
  created_at

usuario_campo
  id, usuario_id FK→usuario, campo_id FK→campo
```

### Tablas maestros por campo/empresa

```sql
unidad_medida                        ← SIMPLIFICADA: solo id + nombre
  id, nombre VARCHAR(50)
  (sin empresa_id, sin labor_id — es catálogo global)

labor                                ← DE EMPRESA, con unidad por defecto
  id, empresa_id FK→empresa,
  nombre VARCHAR(100),
  unidad_id FK→unidad_medida NULL,   ← unidad de medida sugerida para esta labor
  estado_id FK→estado

contratista
  id, rut, nombre,
  campo_id FK→campo,
  estado_id FK→estado

trabajador
  id, campo_id FK→campo,
  nombre, rut,
  tipotrabajador_id FK→tipo_personal,
  contratista_id FK→contratista NULL,
  porcentajecontratista_id FK→porcentaje_contratista NULL,
  estado_id FK→estado,
  created_at

ceco
  id, campo_id FK→campo,
  cecotopi_id FK→ceco_tipo,
  nombre,
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
  ceco_id FK→ceco, labor_id FK→labor,
  unidad_medida_id FK→unidad_medida,
  fecha DATE,
  tipopersonal_id FK→tipo_personal,
  tiporendimiento_id FK→tipo_rendimiento,
  tarifa DECIMAL(10,2),
  hora_inicio TIME NULL, hora_fin TIME NULL,
  estado_id FK→estado_actividad
  (SIN observaciones)

actividad_trabajador
  id, actividad_id FK→actividad, trabajador_id FK→trabajador

rendimiento
  id, actividad_id FK→actividad, trabajador_id FK→trabajador,
  cantidad DECIMAL(10,2),
  horas_trabajadas FLOAT NOT NULL,   ← calculado automático en backend
  horas_extras FLOAT NOT NULL DEFAULT 0,
  created_at
  (SIN observacion)
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

**horas_trabajadas en rendimiento:** Se calcula automáticamente en el backend:
```
horas_trabajadas = (hora_fin - hora_inicio) de la actividad en horas decimales
horas_extras = max(0, horas_trabajadas - 8)
```
Nunca vienen del cliente. El backend los calcula y guarda.

**Contratista como entidad:** Trabajadores contratistas se vinculan a una empresa contratista
registrada en la tabla `contratista`. No es texto libre.

**tipo_personal y tipo_rendimiento son FK numéricas**, no ENUMs ni strings.
La app carga estos catálogos al iniciar sesión.

---

## 3. CAMBIOS REQUERIDOS EN LA API (FastAPI)

### 3.1 Modelos SQLAlchemy

**app/models/actividad.py — modelos completos actualizados:**

```python
# Catálogos simples
class Estado(Base):
    __tablename__ = "estado"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25))

class TipoPersonal(Base):
    __tablename__ = "tipo_personal"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25))

class TipoRendimiento(Base):
    __tablename__ = "tipo_rendimiento"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25))

class CecoTipo(Base):
    __tablename__ = "ceco_tipo"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45))

class PorcentajeContratista(Base):
    __tablename__ = "porcentaje_contratista"
    id:         Mapped[int]   = mapped_column(Integer, primary_key=True)
    porcentaje: Mapped[float] = mapped_column(Float)

# UnidadMedida — catálogo global simple
class UnidadMedida(Base):
    __tablename__ = "unidad_medida"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    # SIN empresa_id, SIN labor_id

# Labor — de empresa, con unidad sugerida
class Labor(Base):
    __tablename__ = "labor"
    id:         Mapped[int]           = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int]           = mapped_column(Integer, ForeignKey("empresa.id"))
    nombre:     Mapped[str]           = mapped_column(String(100))
    unidad_id:  Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("unidad_medida.id"), nullable=True)
    estado_id:  Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    unidad:     Mapped[Optional["UnidadMedida"]] = relationship()

# Contratista
class Contratista(Base):
    __tablename__ = "contratista"
    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    rut:       Mapped[str] = mapped_column(String(12))
    nombre:    Mapped[str] = mapped_column(String(45))
    campo_id:  Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"))
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), default=1)

# Trabajador
class Trabajador(Base):
    __tablename__ = "trabajador"
    id:                       Mapped[int]           = mapped_column(Integer, primary_key=True)
    campo_id:                 Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"))
    nombre:                   Mapped[str]           = mapped_column(String(100))
    rut:                      Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    tipotrabajador_id:        Mapped[int]           = mapped_column(Integer, ForeignKey("tipo_personal.id"))
    contratista_id:           Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("contratista.id"), nullable=True)
    porcentajecontratista_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("porcentaje_contratista.id"), nullable=True)
    estado_id:                Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    created_at:               Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now())
    tipo_personal: Mapped["TipoPersonal"]                      = relationship()
    contratista:   Mapped[Optional["Contratista"]]             = relationship()
    porcentaje:    Mapped[Optional["PorcentajeContratista"]]   = relationship()

# Ceco
class Ceco(Base):
    __tablename__ = "ceco"
    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    campo_id:    Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"))
    cecotopi_id: Mapped[int] = mapped_column(Integer, ForeignKey("ceco_tipo.id"))
    nombre:      Mapped[str] = mapped_column(String(100))
    estado_id:   Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    ceco_tipo:   Mapped["CecoTipo"] = relationship()

# Actividad
class Actividad(Base):
    __tablename__ = "actividad"
    id:                 Mapped[int]            = mapped_column(Integer, primary_key=True)
    campo_id:           Mapped[int]            = mapped_column(Integer, ForeignKey("campo.id"))
    usuario_id:         Mapped[int]            = mapped_column(Integer, ForeignKey("usuario.id"))
    ceco_id:            Mapped[int]            = mapped_column(Integer, ForeignKey("ceco.id"))
    labor_id:           Mapped[int]            = mapped_column(Integer, ForeignKey("labor.id"))
    unidad_medida_id:   Mapped[int]            = mapped_column(Integer, ForeignKey("unidad_medida.id"))
    tipopersonal_id:    Mapped[int]            = mapped_column(Integer, ForeignKey("tipo_personal.id"))
    tiporendimiento_id: Mapped[int]            = mapped_column(Integer, ForeignKey("tipo_rendimiento.id"))
    fecha:              Mapped[date]           = mapped_column(Date)
    tarifa:             Mapped[float]          = mapped_column(Numeric(10, 2))
    hora_inicio:        Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    hora_fin:           Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    estado_id:          Mapped[int]            = mapped_column(SmallInteger, ForeignKey("estado_actividad.id"), default=1)
    # SIN observaciones
    estado:         Mapped["EstadoActividad"]          = relationship()
    labor:          Mapped["Labor"]                    = relationship()
    unidad_medida:  Mapped["UnidadMedida"]             = relationship()
    tipo_personal:  Mapped["TipoPersonal"]             = relationship()
    tipo_rendimiento: Mapped["TipoRendimiento"]        = relationship()
    trabajadores:   Mapped[List["ActividadTrabajador"]] = relationship(cascade="all, delete-orphan")
    rendimientos:   Mapped[List["Rendimiento"]]         = relationship(cascade="all, delete-orphan")

# Rendimiento
class Rendimiento(Base):
    __tablename__ = "rendimiento"
    id:               Mapped[int]   = mapped_column(Integer, primary_key=True)
    actividad_id:     Mapped[int]   = mapped_column(Integer, ForeignKey("actividad.id"))
    trabajador_id:    Mapped[int]   = mapped_column(Integer, ForeignKey("trabajador.id"))
    cantidad:         Mapped[float] = mapped_column(Numeric(10, 2))
    horas_trabajadas: Mapped[float] = mapped_column(Float, nullable=False)
    horas_extras:     Mapped[float] = mapped_column(Float, default=0.0)
    created_at:       Mapped[str]   = mapped_column(TIMESTAMP, server_default=func.now())
    # SIN observacion

# Permiso
class Permiso(Base):
    __tablename__ = "permiso"
    id:               Mapped[int]   = mapped_column(Integer, primary_key=True)
    trabajador_id:    Mapped[int]   = mapped_column(Integer, ForeignKey("trabajador.id"))
    fecha:            Mapped[date]  = mapped_column(Date)
    horas_permiso:    Mapped[float] = mapped_column(Float)
    estadopermiso_id: Mapped[int]   = mapped_column(Integer, ForeignKey("estado_permiso.id"), default=1)
```

**app/models/usuario.py — cambios:**
```python
# Empresa: reemplazar activa BOOLEAN por estado_id
# Campo: reemplazar activo BOOLEAN por estado_id
# Usuario: agregar campo `usuario` VARCHAR(25), reemplazar activo por estado_id

class Empresa(Base):
    ...
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    # ELIMINAR: activa: Mapped[bool]

class Campo(Base):
    ...
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    # ELIMINAR: activo: Mapped[bool]

class Usuario(Base):
    ...
    usuario:   Mapped[str] = mapped_column(String(25), nullable=False)
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), default=1)
    # ELIMINAR: activo: Mapped[bool]
```

### 3.2 Schemas Pydantic

```python
# Catálogos
class UnidadMedidaResponse(BaseModel):
    id: int; nombre: str
    model_config = {"from_attributes": True}

class LaborCreate(BaseModel):
    empresa_id: int; nombre: str
    unidad_id: Optional[int] = None   # unidad sugerida, puede ser None

class LaborResponse(BaseModel):
    id: int; empresa_id: int; nombre: str
    unidad_id: Optional[int]; estado_id: int
    unidad: Optional[UnidadMedidaResponse] = None
    model_config = {"from_attributes": True}

class ContratistaCreate(BaseModel):
    rut: str; nombre: str; campo_id: int

class ContratistaResponse(BaseModel):
    id: int; rut: str; nombre: str; campo_id: int; estado_id: int
    model_config = {"from_attributes": True}

class TrabajadorCreate(BaseModel):
    campo_id: int; nombre: str; rut: Optional[str] = None
    tipotrabajador_id: int
    contratista_id: Optional[int] = None
    porcentajecontratista_id: Optional[int] = None

class TrabajadorResponse(BaseModel):
    id: int; campo_id: int; nombre: str; rut: Optional[str]
    tipotrabajador_id: int; contratista_id: Optional[int]
    porcentajecontratista_id: Optional[int]; estado_id: int
    tipo_personal: Optional[TipoPersonalResponse] = None
    model_config = {"from_attributes": True}

class CecoCreate(BaseModel):
    campo_id: int; cecotopi_id: int; nombre: str

class CecoResponse(BaseModel):
    id: int; campo_id: int; cecotopi_id: int; nombre: str; estado_id: int
    model_config = {"from_attributes": True}

class ActividadCreate(BaseModel):
    campo_id: int; ceco_id: int; labor_id: int; unidad_medida_id: int
    tipopersonal_id: int
    tiporendimiento_id: int
    fecha: date; tarifa: Decimal
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    trabajador_ids: List[int]
    # SIN observaciones

class ActividadResponse(BaseModel):
    id: int; campo_id: int; usuario_id: int
    ceco_id: int; labor_id: int; unidad_medida_id: int
    tipopersonal_id: int; tiporendimiento_id: int
    fecha: date; tarifa: Decimal
    hora_inicio: Optional[time]; hora_fin: Optional[time]
    estado_id: int
    estado: Optional[EstadoActividadResponse] = None
    model_config = {"from_attributes": True}

class RendimientoCreate(BaseModel):
    actividad_id: int; trabajador_id: int; cantidad: Decimal
    # SIN horas — se calculan en backend

class RendimientoBulkCreate(BaseModel):
    actividad_id: int
    rendimientos: List[RendimientoCreate]

class RendimientoResponse(BaseModel):
    id: int; actividad_id: int; trabajador_id: int
    cantidad: Decimal; horas_trabajadas: float; horas_extras: float
    model_config = {"from_attributes": True}

class PermisoCreate(BaseModel):
    trabajador_id: int; fecha: date; horas_permiso: float

class PermisoResponse(BaseModel):
    id: int; trabajador_id: int; fecha: date
    horas_permiso: float; estadopermiso_id: int
    model_config = {"from_attributes": True}
```

### 3.3 Lógica de cálculo de horas (en routers/rendimientos.py)

```python
from datetime import datetime, date as date_type, timedelta

def calcular_horas(actividad: Actividad) -> tuple[float, float]:
    if actividad.hora_inicio is None or actividad.hora_fin is None:
        return 0.0, 0.0
    inicio = datetime.combine(date_type.today(), actividad.hora_inicio)
    fin    = datetime.combine(date_type.today(), actividad.hora_fin)
    horas  = (fin - inicio).total_seconds() / 3600
    extras = max(0.0, horas - 8.0)
    return round(horas, 2), round(extras, 2)
```

### 3.4 Filtro activos — cambio global en TODOS los routers

```python
# ANTES (ya no válido)
.where(Tabla.activo == True)

# AHORA en todas las queries
.where(Tabla.estado_id == 1)
```

### 3.5 Endpoints completos

```
# Catálogos (GET, no requieren campo_id)
GET  /catalogos/tipos-personal
GET  /catalogos/tipos-rendimiento
GET  /catalogos/ceco-tipos
GET  /catalogos/porcentajes-contratista
GET  /unidades-medida               → lista completa (catálogo global)

# Contratistas
POST /contratistas
GET  /contratistas?campo_id=

# Labores (de empresa, incluye unidad sugerida)
POST /labores
GET  /labores?empresa_id=           → incluir unidad relacionada en response
PATCH /labores/{id}

# Trabajadores
POST /trabajadores
GET  /trabajadores?campo_id=&tipotrabajador_id=
PATCH /trabajadores/{id}

# CECOs
POST /cecos
GET  /cecos?campo_id=
PATCH /cecos/{id}

# Actividades
POST  /actividades                  → body: tipopersonal_id, tiporendimiento_id (int), SIN observaciones
GET   /actividades?campo_id=&fecha_desde=&fecha_hasta=&estado_id=
GET   /actividades/{id}
PATCH /actividades/{id}
PATCH /actividades/{id}/estado
DELETE /actividades/{id}            → solo si estado_id == 1

# Rendimientos (horas calculadas en backend)
POST  /rendimientos/bulk
POST  /rendimientos
GET   /rendimientos?actividad_id=
PATCH /rendimientos/{id}
DELETE /rendimientos/{id}

# Permisos
POST /permisos
GET  /permisos?trabajador_id=
```

---

## 4. CAMBIOS REQUERIDOS EN FLUTTER (Drift + Providers)

### 4.1 app_database.dart — tablas nuevas y modificadas

```dart
// NUEVAS tablas de catálogo
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

class Contratistas extends Table {
  IntColumn get id       => integer()();
  IntColumn get campoId  => integer()();
  TextColumn get rut     => text()();
  TextColumn get nombre  => text()();
  IntColumn get estadoId => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// UnidadesMedida — SIMPLIFICADA (solo id + nombre, catálogo global)
class UnidadesMedida extends Table {
  IntColumn get id     => integer()();
  TextColumn get nombre => text()();
  // SIN empresaId, SIN laborId
  @override Set<Column> get primaryKey => {id};
}

// Labores — empresaId + unidadId sugerida
class Labores extends Table {
  IntColumn get id       => integer()();
  IntColumn get empresaId => integer()();
  TextColumn get nombre  => text()();
  IntColumn get unidadId => integer().nullable()(); // ← unidad sugerida
  IntColumn get estadoId => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Trabajadores — ids en lugar de strings
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

// Cecos — cecotipoId en lugar de tipo ENUM + codigo
class Cecos extends Table {
  IntColumn get id         => integer()();
  IntColumn get campoId    => integer()();
  IntColumn get cecotipoId => integer()();
  TextColumn get nombre    => text()();
  IntColumn get estadoId   => integer().withDefault(const Constant(1))();
  @override Set<Column> get primaryKey => {id};
}

// Actividades — ids para tipo, sin observaciones
class Actividades extends Table {
  IntColumn get id                => integer().autoIncrement()();
  IntColumn get remoteId          => integer().nullable()();
  IntColumn get campoId           => integer()();
  IntColumn get usuarioId         => integer()();
  IntColumn get cecoId            => integer()();
  IntColumn get laborId           => integer()();
  IntColumn get unidadMedidaId    => integer()();
  IntColumn get estadoId          => integer().withDefault(const Constant(1))();
  DateTimeColumn get fecha        => dateTime()();
  IntColumn get tipopersonalId    => integer()();
  IntColumn get tiporendimientoId => integer()();
  RealColumn get tarifa           => real()();
  TextColumn get horaInicio       => text().nullable()();
  TextColumn get horaFin          => text().nullable()();
  // SIN observaciones
  TextColumn get syncStatus       => textEnum<SyncStatus>()
      .withDefault(const Constant('pending'))();
  IntColumn get syncRetries       => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt    => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt    => dateTime().withDefault(currentDateAndTime)();
}

// Rendimientos — con horas, sin observacion
class Rendimientos extends Table {
  IntColumn get id               => integer().autoIncrement()();
  IntColumn get remoteId         => integer().nullable()();
  IntColumn get actividadId      => integer()();
  IntColumn get trabajadorId     => integer()();
  RealColumn get cantidad        => real()();
  RealColumn get horasTrabajadas => real().withDefault(const Constant(0.0))();
  RealColumn get horasExtras     => real().withDefault(const Constant(0.0))();
  // SIN observacion
  TextColumn get syncStatus      => textEnum<SyncStatus>()
      .withDefault(const Constant('pending'))();
  DateTimeColumn get createdAt   => dateTime().withDefault(currentDateAndTime)();
}
```

### 4.2 @DriftDatabase actualizado

```dart
@DriftDatabase(tables: [
  // Catálogos
  TiposPersonal, TiposRendimiento, CecoTipos, PorcentajesContratista, EstadosActividad,
  // Tenant
  Empresas, Campos, Usuarios,
  // Maestros
  Contratistas, Trabajadores, Cecos, Labores, UnidadesMedida,
  // Transaccional
  Actividades, ActividadTrabajadores, Rendimientos,
])
```

Incrementar `schemaVersion` a 2 y agregar migración que recrea las tablas modificadas.

### 4.3 Providers a actualizar

```dart
// Filtros de activo — cambiar en TODOS los providers
// ANTES: .where((t) => t.activo.equals(true))
// AHORA: .where((t) => t.estadoId.equals(1))

// Providers nuevos necesarios
tiposPersonalProvider          → StreamProvider<List<TiposPersonalData>>
tiposRendimientoProvider       → StreamProvider<List<TiposRendimientoData>>
cecoTiposProvider              → StreamProvider<List<CecoTiposData>>
contratistasProvider(campoId)  → StreamProvider filtrado por campo y estado=1
unidadesMedidaProvider         → StreamProvider<List<UnidadesMedidaData>> (todo el catálogo)

// Providers modificados
laboresProvider(empresaId)     // ← antes laborProvider(campoId)
trabajadoresProvider(campoId, tipotrabajadorId) // ← antes tipo era string
cecosProvider(campoId)         // sin cambios en firma
```

### 4.4 Lógica de horas en Flutter (para registro local offline)

```dart
double calcularHorasTrabajadas(String? horaInicio, String? horaFin) {
  if (horaInicio == null || horaFin == null) return 0.0;
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

### 4.5 Flujo UX CrearActividad — actualizado

```
1. tipopersonal_id  → dropdown desde tiposPersonalProvider
2. CECO             → dropdown desde cecosProvider(campoId) — muestra nombre
3. labor_id         → dropdown desde laboresProvider(empresaId)
                      al seleccionar → precargar unidad_medida_id con labor.unidadId
                      (si labor.unidadId != null)
4. unidad_medida_id → dropdown desde unidadesMedidaProvider
                      (precargado por paso 3, editable)
5. tiporendimiento_id → dropdown desde tiposRendimientoProvider
6. tarifa           → campo numérico
7. fecha            → DatePicker
8. hora_inicio / hora_fin → TimePicker (opcionales)
9. trabajadores     → multi-select filtrado por tipotrabajadorId == tipopersonal_id
```

### 4.6 Sincronización de catálogos al login

```dart
// Después de setSession() exitoso en AuthNotifier:
await Future.wait([
  _sincronizarCatalogo('/catalogos/tipos-personal',    db.tiposPersonal),
  _sincronizarCatalogo('/catalogos/tipos-rendimiento', db.tiposRendimiento),
  _sincronizarCatalogo('/catalogos/ceco-tipos',        db.cecoTipos),
  _sincronizarCatalogo('/catalogos/porcentajes-contratista', db.porcentajesContratista),
  _sincronizarCatalogo('/unidades-medida',             db.unidadesMedida),
  _sincronizarLabores('/labores?empresa_id=$empresaId', db.labores),
]);
// Luego, ya con campo seleccionado:
_sincronizarMaestrosCampo(campoId);  // trabajadores, cecos, contratistas
```

---

## 5. NOTAS FINALES PARA CLAUDE CODE

- `activo` no existe en ninguna tabla — siempre usar `estado_id = 1` para activos
- `unidad_medida` es catálogo global: solo `id` y `nombre`, sin FKs de empresa o labor
- `labor.unidad_id` es la sugerencia de unidad — puede ser NULL, y el usuario puede cambiarla
- `horas_trabajadas` y `horas_extras` NUNCA vienen del cliente, siempre calculados en backend
- `observaciones` (actividad) y `observacion` (rendimiento) no existen en la BD real
- `tipo_personal` y `tipo_rendimiento` son IDs enteros, no strings ni ENUMs
- Al hacer `build_runner build`, incrementar `schemaVersion` a 2 en AppDatabase
- En todos los routers FastAPI, los filtros de "activo" usan `estado_id == 1`
