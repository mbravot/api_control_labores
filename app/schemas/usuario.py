from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------

class LoginRequest(BaseModel):
    email:    str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    usuario_id:   int
    nombre:       str
    rol_id:       int
    rol:          str
    empresa_id:   int
    campo_id:     Optional[int] = None


class CampoSimpleResponse(BaseModel):
    id:        int
    nombre:    str
    ubicacion: Optional[str] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------

class UsuarioBase(BaseModel):
    nombre:  str
    usuario: str
    email:   EmailStr
    rol_id:  int


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
    nombre:    Optional[str] = None
    usuario:   Optional[str] = None
    rol_id:    Optional[int] = None
    estado_id: Optional[int] = None


class CambiarClaveRequest(BaseModel):
    clave_actual: str
    clave_nueva:  str

    @field_validator("clave_nueva")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")
        return v


class UsuarioResponse(UsuarioBase):
    id:         int
    empresa_id: int
    estado_id:  int
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
    id:        int
    estado_id: int
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
    estado_id: Optional[int] = None


class CampoResponse(CampoBase):
    id:         int
    empresa_id: int
    estado_id:  int
    model_config = {"from_attributes": True}
