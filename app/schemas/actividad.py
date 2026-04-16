from typing import Optional, List
from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------
# Estado actividad
# ---------------------------------------------------------------

class EstadoActividadResponse(BaseModel):
    id:     int
    nombre: str
    orden:  int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Unidad de medida
# ---------------------------------------------------------------

class UnidadMedidaBase(BaseModel):
    nombre:      str
    abreviatura: str


class UnidadMedidaCreate(UnidadMedidaBase):
    empresa_id: int


class UnidadMedidaResponse(UnidadMedidaBase):
    id:         int
    empresa_id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Trabajador
# ---------------------------------------------------------------

class TrabajadorBase(BaseModel):
    nombre:              str
    rut:                 Optional[str] = None
    tipo:                str
    empresa_contratista: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in ("propio", "contratista"):
            raise ValueError("tipo debe ser 'propio' o 'contratista'")
        return v

    @field_validator("empresa_contratista")
    @classmethod
    def contratista_requiere_empresa(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("tipo") == "contratista" and not v:
            raise ValueError("empresa_contratista es requerida cuando tipo es 'contratista'")
        return v


class TrabajadorCreate(TrabajadorBase):
    campo_id: int


class TrabajadorUpdate(BaseModel):
    nombre:              Optional[str] = None
    rut:                 Optional[str] = None
    empresa_contratista: Optional[str] = None
    activo:              Optional[bool] = None


class TrabajadorResponse(TrabajadorBase):
    id:       int
    campo_id: int
    activo:   bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# CECO
# ---------------------------------------------------------------

class CecoBase(BaseModel):
    tipo:   str = "agricola"
    codigo: str
    nombre: str


class CecoCreate(CecoBase):
    campo_id: int


class CecoUpdate(BaseModel):
    tipo:   Optional[str] = None
    nombre: Optional[str] = None
    activo: Optional[bool] = None


class CecoResponse(CecoBase):
    id:       int
    campo_id: int
    activo:   bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Labor
# ---------------------------------------------------------------

class LaborBase(BaseModel):
    nombre:      str
    descripcion: Optional[str] = None


class LaborCreate(LaborBase):
    campo_id: int


class LaborUpdate(BaseModel):
    nombre:      Optional[str] = None
    descripcion: Optional[str] = None
    activo:      Optional[bool] = None


class LaborResponse(LaborBase):
    id:       int
    campo_id: int
    activo:   bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Actividad
# ---------------------------------------------------------------

class ActividadBase(BaseModel):
    fecha:            date
    tipo_personal:    str
    tipo_rendimiento: str
    tarifa:           Decimal
    hora_inicio:      Optional[time] = None
    hora_fin:         Optional[time] = None
    observaciones:    Optional[str]  = None

    @field_validator("tipo_personal")
    @classmethod
    def tipo_personal_valido(cls, v: str) -> str:
        if v not in ("propio", "contratista"):
            raise ValueError("tipo_personal debe ser 'propio' o 'contratista'")
        return v

    @field_validator("tipo_rendimiento")
    @classmethod
    def tipo_rendimiento_valido(cls, v: str) -> str:
        if v not in ("individual", "grupal"):
            raise ValueError("tipo_rendimiento debe ser 'individual' o 'grupal'")
        return v


class ActividadCreate(ActividadBase):
    campo_id:         int
    ceco_id:          int
    labor_id:         int
    unidad_medida_id: int
    trabajador_ids:   List[int]  # IDs de trabajadores a asignar


class ActividadUpdate(BaseModel):
    ceco_id:          Optional[int]     = None
    labor_id:         Optional[int]     = None
    unidad_medida_id: Optional[int]     = None
    fecha:            Optional[date]    = None
    tarifa:           Optional[Decimal] = None
    hora_inicio:      Optional[time]    = None
    hora_fin:         Optional[time]    = None
    observaciones:    Optional[str]     = None
    estado_id:        Optional[int]     = None


class ActividadResponse(ActividadBase):
    id:               int
    campo_id:         int
    usuario_id:       int
    ceco_id:          int
    labor_id:         int
    unidad_medida_id: int
    estado_id:        int
    estado:           Optional[EstadoActividadResponse] = None

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

class RendimientoBase(BaseModel):
    cantidad:    Decimal
    observacion: Optional[str] = None


class RendimientoCreate(RendimientoBase):
    actividad_id:  int
    trabajador_id: int


class RendimientoBulkCreate(BaseModel):
    """Para cargar rendimientos de múltiples trabajadores en una sola llamada."""
    actividad_id:  int
    rendimientos:  List[RendimientoCreate]


class RendimientoUpdate(BaseModel):
    cantidad:    Optional[Decimal] = None
    observacion: Optional[str]     = None


class RendimientoResponse(RendimientoBase):
    id:            int
    actividad_id:  int
    trabajador_id: int
    trabajador:    Optional[TrabajadorResponse] = None

    model_config = {"from_attributes": True}
