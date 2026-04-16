from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
import re


# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    usuario_id:   int
    nombre:       str
    rol:          str
    empresa_id:   int


# ---------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------

class UsuarioBase(BaseModel):
    nombre:     str
    email:      EmailStr
    rol:        str = "supervisor"


class UsuarioCreate(UsuarioBase):
    password:   str
    empresa_id: int

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol:    Optional[str] = None
    activo: Optional[bool] = None


class UsuarioResponse(UsuarioBase):
    id:         int
    empresa_id: int
    activo:     bool

    model_config = {"from_attributes": True}


class UsuarioCampoCreate(BaseModel):
    usuario_id: int
    campo_id:   int


class UsuarioCampoResponse(BaseModel):
    id:         int
    usuario_id: int
    campo_id:   int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------

class EmpresaBase(BaseModel):
    razon_social:   str
    rut:            str
    email_contacto: EmailStr
    plan:           str = "basico"


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaResponse(EmpresaBase):
    id:     int
    activa: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Campo
# ---------------------------------------------------------------

class CampoBase(BaseModel):
    nombre:    str
    ubicacion: Optional[str] = None


class CampoCreate(CampoBase):
    empresa_id: int


class CampoUpdate(BaseModel):
    nombre:    Optional[str] = None
    ubicacion: Optional[str] = None
    activo:    Optional[bool] = None


class CampoResponse(CampoBase):
    id:         int
    empresa_id: int
    activo:     bool

    model_config = {"from_attributes": True}
