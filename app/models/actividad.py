from typing import List, Optional
from datetime import date, time

from sqlalchemy import (
    ForeignKey, Integer, String, Text,
    Date, Time, Numeric, Float, TIMESTAMP, SmallInteger, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------
# Catálogos (solo lectura)
# ---------------------------------------------------------------

class TipoPersonal(Base):
    __tablename__ = "tipo_personal"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25), nullable=False)


class TipoRendimiento(Base):
    __tablename__ = "tipo_rendimiento"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25), nullable=False)


class CecoTipo(Base):
    __tablename__ = "ceco_tipo"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)


class PorcentajeContratista(Base):
    __tablename__ = "porcentaje_contratista"
    id:         Mapped[int]   = mapped_column(Integer, primary_key=True)
    porcentaje: Mapped[float] = mapped_column(Float, nullable=False)


class EstadoActividad(Base):
    __tablename__ = "estado_actividad"
    id:     Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    orden:  Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="estado")


class EstadoPermiso(Base):
    __tablename__ = "estado_permiso"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25), nullable=False)


# ---------------------------------------------------------------
# Maestros
# ---------------------------------------------------------------

class Contratista(Base):
    __tablename__ = "contratista"
    id:        Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rut:       Mapped[str] = mapped_column(String(12), nullable=False)
    nombre:    Mapped[str] = mapped_column(String(45), nullable=False)
    campo_id:  Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    trabajadores: Mapped[List["Trabajador"]] = relationship(back_populates="contratista")


class Trabajador(Base):
    __tablename__ = "trabajador"
    id:                       Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:                 Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    nombre:                   Mapped[str]           = mapped_column(String(100), nullable=False)
    rut:                      Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    tipotrabajador_id:        Mapped[int]           = mapped_column(Integer, ForeignKey("tipo_personal.id"), nullable=False)
    contratista_id:           Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("contratista.id"), nullable=True)
    porcentajecontratista_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("porcentaje_contratista.id"), nullable=True)
    estado_id:                Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    created_at:               Mapped[Optional[str]] = mapped_column(TIMESTAMP, server_default=func.now())
    tipo_personal: Mapped["TipoPersonal"]                    = relationship()
    contratista:   Mapped[Optional["Contratista"]]           = relationship(back_populates="trabajadores")
    porcentaje:    Mapped[Optional["PorcentajeContratista"]] = relationship()
    actividades:   Mapped[List["ActividadTrabajador"]]       = relationship(back_populates="trabajador")
    rendimientos:  Mapped[List["Rendimiento"]]               = relationship(back_populates="trabajador")
    permisos:      Mapped[List["Permiso"]]                   = relationship(back_populates="trabajador")


class Ceco(Base):
    __tablename__ = "ceco"
    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:    Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    cecotipo_id: Mapped[int] = mapped_column(Integer, ForeignKey("ceco_tipo.id"), nullable=False)
    nombre:      Mapped[str] = mapped_column(String(100), nullable=False)
    estado_id:   Mapped[int] = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    ceco_tipo:   Mapped["CecoTipo"]        = relationship()
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="ceco")


class UnidadMedida(Base):
    __tablename__ = "unidad_medida"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)


class Labor(Base):
    __tablename__ = "labor"
    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int]           = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:     Mapped[str]           = mapped_column(String(100), nullable=False)
    unidad_id:  Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("unidad_medida.id"), nullable=True)
    estado_id:  Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    unidad:      Mapped[Optional["UnidadMedida"]] = relationship()
    actividades: Mapped[List["Actividad"]]        = relationship(back_populates="labor")


# ---------------------------------------------------------------
# Transaccional
# ---------------------------------------------------------------

class Actividad(Base):
    __tablename__ = "actividad"
    id:                Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:          Mapped[int]            = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    usuario_id:        Mapped[int]            = mapped_column(Integer, ForeignKey("usuario.id"), nullable=False)
    ceco_id:           Mapped[int]            = mapped_column(Integer, ForeignKey("ceco.id"), nullable=False)
    labor_id:          Mapped[int]            = mapped_column(Integer, ForeignKey("labor.id"), nullable=False)
    unidad_medida_id:  Mapped[int]            = mapped_column(Integer, ForeignKey("unidad_medida.id"), nullable=False)
    tipopersonal_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("tipo_personal.id"), nullable=False)
    personal_id:        Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("contratista.id"), nullable=True)
    tiporendimiento_id: Mapped[int]           = mapped_column(Integer, ForeignKey("tipo_rendimiento.id"), nullable=False)
    fecha:              Mapped[date]          = mapped_column(Date, nullable=False)
    tarifa:             Mapped[float]         = mapped_column(Numeric(10, 2), nullable=False)
    hora_inicio:        Mapped[time]          = mapped_column(Time, nullable=False)
    hora_fin:           Mapped[time]          = mapped_column(Time, nullable=False)
    estado_id:          Mapped[int]           = mapped_column(SmallInteger, ForeignKey("estado_actividad.id"), nullable=False, default=1)
    cecotipo_id:        Mapped[int]           = mapped_column(Integer, ForeignKey("ceco_tipo.id"), nullable=False)
    campo:            Mapped["Campo"]                     = relationship()
    usuario:          Mapped["Usuario"]                   = relationship()
    ceco:             Mapped["Ceco"]                      = relationship(back_populates="actividades")
    labor:            Mapped["Labor"]                     = relationship(back_populates="actividades")
    unidad_medida:    Mapped["UnidadMedida"]              = relationship()
    tipo_personal:    Mapped["TipoPersonal"]              = relationship()
    personal:         Mapped[Optional["Contratista"]]     = relationship()
    tipo_rendimiento: Mapped["TipoRendimiento"]           = relationship()
    ceco_tipo:        Mapped["CecoTipo"]                  = relationship()
    estado:           Mapped["EstadoActividad"]           = relationship(back_populates="actividades")
    trabajadores:     Mapped[List["ActividadTrabajador"]] = relationship(back_populates="actividad", cascade="all, delete-orphan")
    rendimientos:     Mapped[List["Rendimiento"]]         = relationship(back_populates="actividad", cascade="all, delete-orphan")
    rendimiento_grupal: Mapped[Optional["RendimientoGrupal"]] = relationship(back_populates="actividad", uselist=False, cascade="all, delete-orphan")


class ActividadTrabajador(Base):
    __tablename__ = "actividad_trabajador"
    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actividad_id:  Mapped[int] = mapped_column(Integer, ForeignKey("actividad.id"), nullable=False)
    trabajador_id: Mapped[int] = mapped_column(Integer, ForeignKey("trabajador.id"), nullable=False)
    actividad:  Mapped["Actividad"]  = relationship(back_populates="trabajadores")
    trabajador: Mapped["Trabajador"] = relationship(back_populates="actividades")


class Rendimiento(Base):
    __tablename__ = "rendimiento"
    id:                       Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    actividad_id:             Mapped[int]   = mapped_column(Integer, ForeignKey("actividad.id"), nullable=False)
    trabajador_id:            Mapped[int]   = mapped_column(Integer, ForeignKey("trabajador.id"), nullable=False)
    cantidad:                 Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    horas_trabajadas:         Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    horas_extras:             Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    porcentajecontratista_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("porcentaje_contratista.id"), nullable=True)
    created_at:               Mapped[Optional[str]] = mapped_column(TIMESTAMP, server_default=func.now())
    actividad:  Mapped["Actividad"]                    = relationship(back_populates="rendimientos")
    trabajador: Mapped["Trabajador"]                   = relationship(back_populates="rendimientos")
    porcentaje: Mapped[Optional["PorcentajeContratista"]] = relationship()


class RendimientoGrupal(Base):
    __tablename__ = "rendimiento_grupal"
    id:                       Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    actividad_id:             Mapped[int]   = mapped_column(Integer, ForeignKey("actividad.id"), nullable=False)
    cantidad_trabajadores:    Mapped[int]   = mapped_column(Integer, nullable=False)
    rendimiento_total:        Mapped[float] = mapped_column(Float, nullable=False)
    porcentajecontratista_id: Mapped[int]   = mapped_column(Integer, ForeignKey("porcentaje_contratista.id"), nullable=False)
    horas_trabajadas:         Mapped[float] = mapped_column(Float, nullable=False)
    horas_extras:             Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actividad:  Mapped["Actividad"]             = relationship(back_populates="rendimiento_grupal")
    porcentaje: Mapped["PorcentajeContratista"] = relationship()


class Permiso(Base):
    __tablename__ = "permiso"
    id:               Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    trabajador_id:    Mapped[int]   = mapped_column(Integer, ForeignKey("trabajador.id"), nullable=False)
    fecha:            Mapped[date]  = mapped_column(Date, nullable=False)
    horas_permiso:    Mapped[float] = mapped_column(Float, nullable=False)
    estadopermiso_id: Mapped[int]   = mapped_column(Integer, ForeignKey("estado_permiso.id"), nullable=False, default=1)
    trabajador:    Mapped["Trabajador"]    = relationship(back_populates="permisos")
    estado_permiso: Mapped["EstadoPermiso"] = relationship()
