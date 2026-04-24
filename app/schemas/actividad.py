from typing import Optional, List
from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel


# ---------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------

class EstadoActividadResponse(BaseModel):
    id:     int
    nombre: str
    orden:  int
    model_config = {"from_attributes": True}


class TipoPersonalResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class TipoRendimientoResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class CecoTipoResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class PorcentajeContratistaResponse(BaseModel):
    id:         int
    porcentaje: float
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Contratista
# ---------------------------------------------------------------

class ContratistaCreate(BaseModel):
    rut:      str
    nombre:   str
    campo_id: int


class ContratistaUpdate(BaseModel):
    nombre:    Optional[str] = None
    estado_id: Optional[int] = None


class ContratistaResponse(BaseModel):
    id:        int
    rut:       str
    nombre:    str
    campo_id:  int
    estado_id: int
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Trabajador
# ---------------------------------------------------------------

class TrabajadorCreate(BaseModel):
    campo_id:                 int
    nombre:                   str
    rut:                      Optional[str] = None
    tipotrabajador_id:        int
    contratista_id:           Optional[int] = None
    porcentajecontratista_id: Optional[int] = None


class TrabajadorUpdate(BaseModel):
    nombre:                   Optional[str] = None
    rut:                      Optional[str] = None
    contratista_id:           Optional[int] = None
    porcentajecontratista_id: Optional[int] = None
    estado_id:                Optional[int] = None


class TrabajadorResponse(BaseModel):
    id:                       int
    campo_id:                 int
    nombre:                   str
    rut:                      Optional[str] = None
    tipotrabajador_id:        int
    contratista_id:           Optional[int] = None
    porcentajecontratista_id: Optional[int] = None
    estado_id:                int
    tipo_personal:            Optional[TipoPersonalResponse] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# CECO
# ---------------------------------------------------------------

class CecoCreate(BaseModel):
    campo_id:    int
    cecotipo_id: int
    nombre:      str


class CecoUpdate(BaseModel):
    cecotipo_id: Optional[int] = None
    nombre:      Optional[str] = None
    estado_id:   Optional[int] = None


class CecoResponse(BaseModel):
    id:          int
    campo_id:    int
    cecotipo_id: int
    nombre:      str
    estado_id:   int
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Unidad de medida
# ---------------------------------------------------------------

class UnidadMedidaResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Labor
# ---------------------------------------------------------------

class LaborCreate(BaseModel):
    empresa_id: int
    nombre:     str
    unidad_id:  Optional[int] = None


class LaborUpdate(BaseModel):
    nombre:    Optional[str] = None
    unidad_id: Optional[int] = None
    estado_id: Optional[int] = None


class LaborResponse(BaseModel):
    id:         int
    empresa_id: int
    nombre:     str
    unidad_id:  Optional[int] = None
    estado_id:  int
    unidad:     Optional[UnidadMedidaResponse] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Actividad
# ---------------------------------------------------------------

class ActividadCreate(BaseModel):
    campo_id:           int
    fecha:              date
    tipopersonal_id:    int
    tiporendimiento_id: int
    labor_id:           int
    unidad_medida_id:   int
    ceco_id:            int
    tarifa:             Decimal
    hora_inicio:        time
    hora_fin:           time
    trabajador_ids:     List[int]


class ActividadUpdate(BaseModel):
    fecha:              Optional[date]    = None
    tipopersonal_id:    Optional[int]     = None
    personal_id:        Optional[int]     = None
    tiporendimiento_id: Optional[int]     = None
    labor_id:           Optional[int]     = None
    unidad_medida_id:   Optional[int]     = None
    cecotipo_id:        Optional[int]     = None
    ceco_id:            Optional[int]     = None
    tarifa:             Optional[Decimal] = None
    hora_inicio:        Optional[time]    = None
    hora_fin:           Optional[time]    = None


class ActividadResponse(BaseModel):
    id:                 int
    campo_id:           int
    usuario_id:         int
    fecha:              date
    tipopersonal_id:    int
    personal_id:        Optional[int] = None
    tiporendimiento_id: int
    labor_id:           int
    unidad_medida_id:   int
    cecotipo_id:        int
    ceco_id:            int
    tarifa:             Decimal
    hora_inicio:        time
    hora_fin:           time
    estado_id:          int
    estado:             Optional[EstadoActividadResponse] = None
    model_config = {"from_attributes": True}


class ActividadDetalleResponse(ActividadResponse):
    trabajadores: List["ActividadTrabajadorResponse"] = []
    rendimientos: List["RendimientoResponse"]         = []


# ---------------------------------------------------------------
# Actividad Trabajador
# ---------------------------------------------------------------

class ActividadTrabajadorResponse(BaseModel):
    id:            int
    actividad_id:  int
    trabajador_id: int
    trabajador:    Optional[TrabajadorResponse] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Rendimiento
# ---------------------------------------------------------------

class RendimientoCreate(BaseModel):
    actividad_id:             int
    trabajador_id:            int
    cantidad:                 Decimal
    porcentajecontratista_id: Optional[int] = None


class RendimientoBulkCreate(BaseModel):
    actividad_id: int
    rendimientos: List[RendimientoCreate]


class RendimientoUpdate(BaseModel):
    cantidad:                 Optional[Decimal] = None
    horas_trabajadas:         Optional[float]   = None
    horas_extras:             Optional[float]   = None
    porcentajecontratista_id: Optional[int]     = None


class RendimientoResponse(BaseModel):
    id:                       int
    actividad_id:             int
    trabajador_id:            int
    cantidad:                 Decimal
    horas_trabajadas:         float
    horas_extras:             float
    porcentajecontratista_id: Optional[int] = None
    trabajador:               Optional[TrabajadorResponse] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Rendimiento Grupal
# ---------------------------------------------------------------

class RendimientoGrupalCreate(BaseModel):
    actividad_id:             int
    cantidad_trabajadores:    int
    rendimiento_total:        float
    porcentajecontratista_id: Optional[int] = None


class RendimientoGrupalUpdate(BaseModel):
    cantidad_trabajadores:    Optional[int]   = None
    rendimiento_total:        Optional[float] = None
    horas_trabajadas:         Optional[float] = None
    horas_extras:             Optional[float] = None
    porcentajecontratista_id: Optional[int]   = None


class RendimientoGrupalResponse(BaseModel):
    id:                       int
    actividad_id:             int
    cantidad_trabajadores:    int
    rendimiento_total:        float
    porcentajecontratista_id: Optional[int] = None
    horas_trabajadas:         float
    horas_extras:             float
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Permiso
# ---------------------------------------------------------------

class EstadoPermisoResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class TrabajadorSimpleResponse(BaseModel):
    id:     int
    nombre: str
    rut:    Optional[str] = None
    model_config = {"from_attributes": True}


class PermisoCreate(BaseModel):
    trabajador_id: int
    fecha:         date
    horas_permiso: float


class PermisoUpdate(BaseModel):
    horas_permiso:    Optional[float] = None
    estadopermiso_id: Optional[int]   = None


class PermisoResponse(BaseModel):
    id:               int
    trabajador_id:    int
    fecha:            date
    horas_permiso:    float
    estadopermiso_id: int
    trabajador:       Optional[TrabajadorSimpleResponse] = None
    estado_permiso:   Optional[EstadoPermisoResponse]   = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Horas trabajadas (vista unificada individual + grupal)
# ---------------------------------------------------------------

class HorasTrabajadasItem(BaseModel):
    tipo:                  str                 # "individual" | "grupal"
    rendimiento_id:        int                 # id de rendimiento o rendimiento_grupal
    actividad_id:          int
    fecha:                 date
    hora_inicio:           time
    hora_fin:              time
    labor_id:              int
    labor_nombre:          str
    ceco_id:               int
    ceco_nombre:           str
    trabajador_id:         int                 # siempre presente (grupal expandido por trabajador)
    trabajador_nombre:     str
    trabajador_rut:        Optional[str] = None
    cantidad_trabajadores: Optional[int] = None   # solo grupal (informativo)
    horas_trabajadas:      float
    horas_extras:          float


class HorasTrabajadasUpdate(BaseModel):
    horas_trabajadas: Optional[float] = None
    horas_extras:     Optional[float] = None


# ---------------------------------------------------------------
# Horas por día (configuración de jornada por empresa)
# ---------------------------------------------------------------

class NombreDiaResponse(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class HorasPorDiaResponse(BaseModel):
    id:           int
    empresa_id:   int
    nombredia_id: int
    horas_dias:   float
    nombre_dia:   Optional[NombreDiaResponse] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------

class IndicadorHorasDiariasPropio(BaseModel):
    trabajador_id:         int
    trabajador_nombre:     str
    trabajador_rut:        Optional[str] = None
    fecha:                 date
    nombredia_id:          int
    horas_individual:      float                      # suma de rendimiento individual
    horas_grupal:          float                      # suma de rendimiento_grupal expandido
    horas_trabajadas:      float                      # individual + grupal
    horas_permiso:         float                      # suma de permiso.horas_permiso
    total_horas:           float                      # horas_trabajadas + horas_permiso
    horas_extras:          float                      # no se usa en la app (siempre 0)
    horas_esperadas:       Optional[float] = None
    diferencia:            Optional[float] = None     # total_horas - horas_esperadas
    cumple:                Optional[bool]  = None     # total_horas <= horas_esperadas


class IndicadorRendimientoTrabajador(BaseModel):
    trabajador_id:     int
    trabajador_nombre: str
    trabajador_rut:    Optional[str] = None
    tipotrabajador_id: int                            # 1=propio, 2=contratista
    cantidad:          float


class IndicadorRendimientoActividad(BaseModel):
    actividad_id:       int
    labor_id:           int
    labor_nombre:       str
    ceco_id:            int
    ceco_nombre:        str
    hora_inicio:        time
    hora_fin:           time
    unidad_medida_id:   int
    unidad_nombre:      str
    tipopersonal_id:    int                           # 1=propio, 2=contratista
    tiporendimiento_id: int                           # 1=individual, 2=grupal
    cantidad_total:     float
    trabajadores:       List[IndicadorRendimientoTrabajador]


class IndicadorRendimientoFecha(BaseModel):
    fecha:       date
    actividades: List[IndicadorRendimientoActividad]
