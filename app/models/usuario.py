from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Estado(Base):
    __tablename__ = "estado"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(25), nullable=False)


class Rol(Base):
    __tablename__ = "rol"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)


class Empresa(Base):
    __tablename__ = "empresa"
    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    razon_social:   Mapped[str]           = mapped_column(String(150), nullable=False)
    rut:            Mapped[str]           = mapped_column(String(12), nullable=False, unique=True)
    email_contacto: Mapped[str]           = mapped_column(String(100), nullable=False)
    plan:           Mapped[str]           = mapped_column(String(30), nullable=False, default="basico")
    estado_id:      Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    created_at:     Mapped[Optional[str]] = mapped_column(TIMESTAMP, server_default=func.now())
    campos:   Mapped[List["Campo"]]   = relationship(back_populates="empresa")
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa")


class Campo(Base):
    __tablename__ = "campo"
    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int]           = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:     Mapped[str]           = mapped_column(String(100), nullable=False)
    ubicacion:  Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    estado_id:  Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    created_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP, server_default=func.now())
    empresa:  Mapped["Empresa"]            = relationship(back_populates="campos")
    usuarios: Mapped[List["UsuarioCampo"]] = relationship(back_populates="campo")


class Usuario(Base):
    __tablename__ = "usuario"
    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:        Mapped[str]           = mapped_column(String(100), nullable=False)
    usuario:       Mapped[str]           = mapped_column(String(25), nullable=False)
    email:         Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str]           = mapped_column(String(255), nullable=False)
    rol_id:        Mapped[int]           = mapped_column(Integer, ForeignKey("rol.id"), nullable=False)
    estado_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("estado.id"), nullable=False, default=1)
    created_at:    Mapped[Optional[str]] = mapped_column(TIMESTAMP, server_default=func.now())
    rol:    Mapped["Rol"]                 = relationship()
    empresa: Mapped["Empresa"]            = relationship(back_populates="usuarios")
    campos:  Mapped[List["UsuarioCampo"]] = relationship(back_populates="usuario")


class UsuarioCampo(Base):
    __tablename__ = "usuario_campo"
    id:         Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuario.id"), nullable=False)
    campo_id:   Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    usuario: Mapped["Usuario"] = relationship(back_populates="campos")
    campo:   Mapped["Campo"]   = relationship(back_populates="usuarios")
