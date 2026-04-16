from typing import List, Optional
import enum

from sqlalchemy import (
    Boolean, Enum, ForeignKey, Integer, String, Text,
    Date, Time, Numeric, TIMESTAMP, SmallInteger, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------
# Enums
# ---------------------------------------------------------------

class TipoPersonal(str, enum.Enum):
    propio      = "propio"
    contratista = "contratista"


class TipoRendimiento(str, enum.Enum):
    individual = "individual"
    grupal     = "grupal"


class TipoCeco(str, enum.Enum):
    agricola      = "agricola"
    administrativo = "administrativo"
    otro          = "otro"


# ---------------------------------------------------------------
# Maestros
# ---------------------------------------------------------------

class EstadoActividad(Base):
    __tablename__ = "estado_actividad"

    id:     Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    orden:  Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)

    actividades: Mapped[List["Actividad"]] = relationship(back_populates="estado")


class UnidadMedida(Base):
    __tablename__ = "unidad_medida"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id:  Mapped[int] = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:      Mapped[str] = mapped_column(String(50), nullable=False)
    abreviatura: Mapped[str] = mapped_column(String(10), nullable=False)

    empresa:     Mapped["Empresa"]        = relationship(back_populates="unidades_medida")
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="unidad_medida")


class Trabajador(Base):
    __tablename__ = "trabajador"

    id:                  Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:            Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    nombre:              Mapped[str]           = mapped_column(String(100), nullable=False)
    rut:                 Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    tipo:                Mapped[str]           = mapped_column(Enum(TipoPersonal), nullable=False)
    empresa_contratista: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    activo:              Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    created_at:          Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now())

    campo:        Mapped["Campo"]                    = relationship(back_populates="trabajadores")
    actividades:  Mapped[List["ActividadTrabajador"]] = relationship(back_populates="trabajador")
    rendimientos: Mapped[List["Rendimiento"]]         = relationship(back_populates="trabajador")


class Ceco(Base):
    __tablename__ = "ceco"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id: Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    tipo:     Mapped[str] = mapped_column(Enum(TipoCeco), nullable=False, default=TipoCeco.agricola)
    codigo:   Mapped[str] = mapped_column(String(30), nullable=False)
    nombre:   Mapped[str] = mapped_column(String(100), nullable=False)
    activo:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    campo:      Mapped["Campo"]            = relationship(back_populates="cecos")
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="ceco")


class Labor(Base):
    __tablename__ = "labor"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    nombre:      Mapped[str]           = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)

    campo:      Mapped["Campo"]            = relationship(back_populates="labores")
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="labor")


# ---------------------------------------------------------------
# Transaccional
# ---------------------------------------------------------------

class Actividad(Base):
    __tablename__ = "actividad"

    id:               Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:         Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    usuario_id:       Mapped[int]           = mapped_column(Integer, ForeignKey("usuario.id"), nullable=False)
    ceco_id:          Mapped[int]           = mapped_column(Integer, ForeignKey("ceco.id"), nullable=False)
    labor_id:         Mapped[int]           = mapped_column(Integer, ForeignKey("labor.id"), nullable=False)
    unidad_medida_id: Mapped[int]           = mapped_column(Integer, ForeignKey("unidad_medida.id"), nullable=False)
    estado_id:        Mapped[int]           = mapped_column(SmallInteger, ForeignKey("estado_actividad.id"), nullable=False, default=1)
    fecha:            Mapped[str]           = mapped_column(Date, nullable=False)
    tipo_personal:    Mapped[str]           = mapped_column(Enum(TipoPersonal), nullable=False)
    tipo_rendimiento: Mapped[str]           = mapped_column(Enum(TipoRendimiento), nullable=False)
    tarifa:           Mapped[float]         = mapped_column(Numeric(10, 2), nullable=False)
    hora_inicio:      Mapped[Optional[str]] = mapped_column(Time, nullable=True)
    hora_fin:         Mapped[Optional[str]] = mapped_column(Time, nullable=True)
    observaciones:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:       Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at:       Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    campo:        Mapped["Campo"]                    = relationship(back_populates="actividades")
    usuario:      Mapped["Usuario"]                  = relationship(back_populates="actividades")
    ceco:         Mapped["Ceco"]                     = relationship(back_populates="actividades")
    labor:        Mapped["Labor"]                    = relationship(back_populates="actividades")
    unidad_medida: Mapped["UnidadMedida"]            = relationship(back_populates="actividades")
    estado:       Mapped["EstadoActividad"]          = relationship(back_populates="actividades")
    trabajadores: Mapped[List["ActividadTrabajador"]] = relationship(back_populates="actividad", cascade="all, delete-orphan")
    rendimientos: Mapped[List["Rendimiento"]]         = relationship(back_populates="actividad", cascade="all, delete-orphan")


class ActividadTrabajador(Base):
    __tablename__ = "actividad_trabajador"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actividad_id:  Mapped[int] = mapped_column(Integer, ForeignKey("actividad.id"), nullable=False)
    trabajador_id: Mapped[int] = mapped_column(Integer, ForeignKey("trabajador.id"), nullable=False)

    actividad:  Mapped["Actividad"]  = relationship(back_populates="trabajadores")
    trabajador: Mapped["Trabajador"] = relationship(back_populates="actividades")


class Rendimiento(Base):
    __tablename__ = "rendimiento"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    actividad_id:  Mapped[int]           = mapped_column(Integer, ForeignKey("actividad.id"), nullable=False)
    trabajador_id: Mapped[int]           = mapped_column(Integer, ForeignKey("trabajador.id"), nullable=False)
    cantidad:      Mapped[float]         = mapped_column(Numeric(10, 2), nullable=False)
    observacion:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:    Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now())

    actividad:  Mapped["Actividad"]  = relationship(back_populates="rendimientos")
    trabajador: Mapped["Trabajador"] = relationship(back_populates="rendimientos")
