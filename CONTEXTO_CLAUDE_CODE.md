# CONTEXTO DEL PROYECTO — Control de Labores
# Para uso con Claude Code — continuar desarrollo de la API

---

## 1. DESCRIPCIÓN DEL PROYECTO

Aplicación SaaS multi-tenant para el mundo agrícola. Permite a supervisores de campo
registrar actividades laborales y los rendimientos de los trabajadores.

**Stack:**
- Backend: Python 3.10, FastAPI, SQLAlchemy 2.0 async, aiomysql
- Base de datos: MySQL 8 — host 200.73.20.99:35026, DB: lahornilla_control_labores
- Auth: JWT con python-jose + passlib bcrypt
- Pydantic v2 para schemas

---

## 2. MODELO DE NEGOCIO

Jerarquía: Empresa → Campo → Usuario (un usuario puede acceder a N campos)

- Empresa: tenant raíz
- Campo: unidad operativa donde ocurre el trabajo
- Usuario: pertenece a una empresa, accede a campos vía tabla usuario_campo
- Roles: admin_empresa | supervisor | consultor
- Trabajador: propio o contratista, pertenece a un campo
- Actividad: registrada por supervisor en un campo. Tiene fecha, labor, ceco,
  unidad de medida, tarifa, hora inicio/fin, tipo_personal, tipo_rendimiento
- tipo_rendimiento: individual (un rendimiento por trabajador) o grupal (un total)
- estado_actividad: creada(1) → revisada(2) → aprobada(3) → finalizada(4)
- Rendimiento: cantidad producida por un trabajador en una actividad

---

## 3. ESTRUCTURA DE ARCHIVOS

```
app/
├── core/
│   ├── config.py       ✅ completo
│   ├── database.py     ✅ completo
│   ├── security.py     ✅ completo
│   └── deps.py         ✅ completo
├── models/
│   ├── __init__.py     ✅ completo
│   ├── usuario.py      ✅ completo
│   └── actividad.py    ✅ completo
├── schemas/
│   ├── usuario.py      ✅ completo
│   └── actividad.py    ✅ completo
└── routers/
    ├── auth.py         ✅ completo
    ├── empresa_campo.py ✅ completo
    ├── usuarios.py     ✅ completo
    ├── maestros.py     ✅ completo
    ├── actividades.py  ❌ PENDIENTE (archivo vacío)
    ├── rendimientos.py ❌ PENDIENTE (no creado)
    └── main.py         ❌ PENDIENTE (no creado)
requirements.txt        ✅ completo
.env.example            ✅ completo
```

---

## 4. ARCHIVOS COMPLETOS

### requirements.txt
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
aiomysql==0.2.0
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
```

### .env.example
```
DB_HOST=200.73.20.99
DB_PORT=35026
DB_USER=lahornilla_mbravo
DB_PASSWORD=tu_password_aqui
DB_NAME=lahornilla_control_labores
SECRET_KEY=cambia_esto_por_un_valor_seguro_generado_con_openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

---

### app/core/config.py
```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DB_HOST: str = "200.73.20.99"
    DB_PORT: int = 35026
    DB_USER: str = "lahornilla_mbravo"
    DB_PASSWORD: str
    DB_NAME: str = "lahornilla_control_labores"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

### app/core/database.py
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### app/core/security.py
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
```

### app/core/deps.py
```python
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    usuario_id: Optional[int] = payload.get("sub")
    if usuario_id is None:
        raise credentials_exception
    result = await db.execute(select(Usuario).where(Usuario.id == int(usuario_id)))
    usuario = result.scalar_one_or_none()
    if usuario is None or not usuario.activo:
        raise credentials_exception
    return usuario

async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    return current_user

async def require_admin(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if current_user.rol != "admin_empresa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol admin_empresa",
        )
    return current_user

async def verify_campo_access(
    campo_id: int,
    current_user: Usuario,
    db: AsyncSession,
) -> bool:
    from app.models.usuario import UsuarioCampo
    result = await db.execute(
        select(UsuarioCampo).where(
            UsuarioCampo.usuario_id == current_user.id,
            UsuarioCampo.campo_id == campo_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin acceso a este campo",
        )
    return True
```

---

### app/models/usuario.py
```python
from typing import List, Optional
import enum
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, SmallInteger, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class RolUsuario(str, enum.Enum):
    admin_empresa = "admin_empresa"
    supervisor    = "supervisor"
    consultor     = "consultor"

class Empresa(Base):
    __tablename__ = "empresa"
    id:             Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    razon_social:   Mapped[str]  = mapped_column(String(150), nullable=False)
    rut:            Mapped[str]  = mapped_column(String(12), nullable=False, unique=True)
    email_contacto: Mapped[str]  = mapped_column(String(100), nullable=False)
    plan:           Mapped[str]  = mapped_column(String(30), nullable=False, default="basico")
    activa:         Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at:     Mapped[str]  = mapped_column(TIMESTAMP, server_default=func.now())
    campos:          Mapped[List["Campo"]]        = relationship(back_populates="empresa")
    usuarios:        Mapped[List["Usuario"]]      = relationship(back_populates="empresa")
    unidades_medida: Mapped[List["UnidadMedida"]] = relationship(back_populates="empresa")

class Campo(Base):
    __tablename__ = "campo"
    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int]           = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:     Mapped[str]           = mapped_column(String(100), nullable=False)
    ubicacion:  Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    activo:     Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str]           = mapped_column(TIMESTAMP, server_default=func.now())
    empresa:      Mapped["Empresa"]            = relationship(back_populates="campos")
    usuarios:     Mapped[List["UsuarioCampo"]] = relationship(back_populates="campo")
    trabajadores: Mapped[List["Trabajador"]]   = relationship(back_populates="campo")
    cecos:        Mapped[List["Ceco"]]         = relationship(back_populates="campo")
    labores:      Mapped[List["Labor"]]        = relationship(back_populates="campo")
    actividades:  Mapped[List["Actividad"]]    = relationship(back_populates="campo")

class Usuario(Base):
    __tablename__ = "usuario"
    id:            Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id:    Mapped[int]  = mapped_column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre:        Mapped[str]  = mapped_column(String(100), nullable=False)
    email:         Mapped[str]  = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str]  = mapped_column(String(255), nullable=False)
    rol:           Mapped[str]  = mapped_column(Enum(RolUsuario), nullable=False, default=RolUsuario.supervisor)
    activo:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at:    Mapped[str]  = mapped_column(TIMESTAMP, server_default=func.now())
    empresa:     Mapped["Empresa"]           = relationship(back_populates="usuarios")
    campos:      Mapped[List["UsuarioCampo"]] = relationship(back_populates="usuario")
    actividades: Mapped[List["Actividad"]]   = relationship(back_populates="usuario")

class UsuarioCampo(Base):
    __tablename__ = "usuario_campo"
    id:         Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuario.id"), nullable=False)
    campo_id:   Mapped[int] = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    usuario: Mapped["Usuario"] = relationship(back_populates="campos")
    campo:   Mapped["Campo"]   = relationship(back_populates="usuarios")
```

### app/models/actividad.py
```python
from typing import List, Optional
import enum
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Date, Time, Numeric, TIMESTAMP, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class TipoPersonal(str, enum.Enum):
    propio      = "propio"
    contratista = "contratista"

class TipoRendimiento(str, enum.Enum):
    individual = "individual"
    grupal     = "grupal"

class TipoCeco(str, enum.Enum):
    agricola       = "agricola"
    administrativo = "administrativo"
    otro           = "otro"

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
    empresa:     Mapped["Empresa"]         = relationship(back_populates="unidades_medida")
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
    campo:        Mapped["Campo"]                     = relationship(back_populates="trabajadores")
    actividades:  Mapped[List["ActividadTrabajador"]] = relationship(back_populates="trabajador")
    rendimientos: Mapped[List["Rendimiento"]]          = relationship(back_populates="trabajador")

class Ceco(Base):
    __tablename__ = "ceco"
    id:       Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id: Mapped[int]  = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    tipo:     Mapped[str]  = mapped_column(Enum(TipoCeco), nullable=False, default=TipoCeco.agricola)
    codigo:   Mapped[str]  = mapped_column(String(30), nullable=False)
    nombre:   Mapped[str]  = mapped_column(String(100), nullable=False)
    activo:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    campo:       Mapped["Campo"]            = relationship(back_populates="cecos")
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="ceco")

class Labor(Base):
    __tablename__ = "labor"
    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    campo_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("campo.id"), nullable=False)
    nombre:      Mapped[str]           = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    campo:       Mapped["Campo"]           = relationship(back_populates="labores")
    actividades: Mapped[List["Actividad"]] = relationship(back_populates="labor")

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
    campo:         Mapped["Campo"]                     = relationship(back_populates="actividades")
    usuario:       Mapped["Usuario"]                   = relationship(back_populates="actividades")
    ceco:          Mapped["Ceco"]                      = relationship(back_populates="actividades")
    labor:         Mapped["Labor"]                     = relationship(back_populates="actividades")
    unidad_medida: Mapped["UnidadMedida"]              = relationship(back_populates="actividades")
    estado:        Mapped["EstadoActividad"]           = relationship(back_populates="actividades")
    trabajadores:  Mapped[List["ActividadTrabajador"]] = relationship(back_populates="actividad", cascade="all, delete-orphan")
    rendimientos:  Mapped[List["Rendimiento"]]          = relationship(back_populates="actividad", cascade="all, delete-orphan")

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
```

---

### app/schemas/usuario.py
```python
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator

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

class UsuarioBase(BaseModel):
    nombre: str
    email:  EmailStr
    rol:    str = "supervisor"

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
    nombre: Optional[str]  = None
    rol:    Optional[str]  = None
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

class CampoBase(BaseModel):
    nombre:    str
    ubicacion: Optional[str] = None

class CampoCreate(CampoBase):
    empresa_id: int

class CampoUpdate(BaseModel):
    nombre:    Optional[str]  = None
    ubicacion: Optional[str]  = None
    activo:    Optional[bool] = None

class CampoResponse(CampoBase):
    id:         int
    empresa_id: int
    activo:     bool
    model_config = {"from_attributes": True}
```

### app/schemas/actividad.py
```python
from typing import Optional, List
from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel, field_validator

class EstadoActividadResponse(BaseModel):
    id:     int
    nombre: str
    orden:  int
    model_config = {"from_attributes": True}

class UnidadMedidaBase(BaseModel):
    nombre:      str
    abreviatura: str

class UnidadMedidaCreate(UnidadMedidaBase):
    empresa_id: int

class UnidadMedidaResponse(UnidadMedidaBase):
    id:         int
    empresa_id: int
    model_config = {"from_attributes": True}

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
    nombre:              Optional[str]  = None
    rut:                 Optional[str]  = None
    empresa_contratista: Optional[str]  = None
    activo:              Optional[bool] = None

class TrabajadorResponse(TrabajadorBase):
    id:       int
    campo_id: int
    activo:   bool
    model_config = {"from_attributes": True}

class CecoBase(BaseModel):
    tipo:   str = "agricola"
    codigo: str
    nombre: str

class CecoCreate(CecoBase):
    campo_id: int

class CecoUpdate(BaseModel):
    tipo:   Optional[str]  = None
    nombre: Optional[str]  = None
    activo: Optional[bool] = None

class CecoResponse(CecoBase):
    id:       int
    campo_id: int
    activo:   bool
    model_config = {"from_attributes": True}

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
    trabajador_ids:   List[int]

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

class ActividadTrabajadorResponse(BaseModel):
    id:            int
    actividad_id:  int
    trabajador_id: int
    trabajador:    Optional[TrabajadorResponse] = None
    model_config = {"from_attributes": True}

class RendimientoBase(BaseModel):
    cantidad:    Decimal
    observacion: Optional[str] = None

class RendimientoCreate(RendimientoBase):
    actividad_id:  int
    trabajador_id: int

class RendimientoBulkCreate(BaseModel):
    actividad_id: int
    rendimientos: List[RendimientoCreate]

class RendimientoUpdate(BaseModel):
    cantidad:    Optional[Decimal] = None
    observacion: Optional[str]     = None

class RendimientoResponse(RendimientoBase):
    id:            int
    actividad_id:  int
    trabajador_id: int
    trabajador:    Optional[TrabajadorResponse] = None
    model_config = {"from_attributes": True}
```

---

### app/routers/auth.py  ✅ completo
### app/routers/empresa_campo.py  ✅ completo
### app/routers/usuarios.py  ✅ completo
### app/routers/maestros.py  ✅ completo

---

## 5. LO QUE FALTA CREAR

### app/routers/actividades.py  ← CREAR ESTE ARCHIVO

Endpoints requeridos:
- POST   /actividades              → crear actividad + asignar trabajadores (ActividadCreate incluye trabajador_ids)
- GET    /actividades?campo_id=&fecha_desde=&fecha_hasta=&estado_id= → listar con filtros
- GET    /actividades/{id}         → detalle con trabajadores y rendimientos (ActividadDetalleResponse)
- PATCH  /actividades/{id}         → actualizar campos editables (ActividadUpdate)
- DELETE /actividades/{id}         → solo si estado_id == 1 (creada)
- POST   /actividades/{id}/trabajadores → agregar trabajadores adicionales
- DELETE /actividades/{id}/trabajadores/{trabajador_id} → quitar trabajador (solo si sin rendimiento)
- PATCH  /actividades/{id}/estado  → avanzar estado respetando flujo secuencial (1→2→3→4)

Validaciones clave:
- verify_campo_access antes de cualquier operación
- Al crear: trabajador_ids debe coincidir con tipo_personal de la actividad
- Al cambiar estado: solo avanzar (no retroceder), validar con estado.orden
- Al eliminar: solo permitir si estado_id == 1
- Usar selectinload para cargar relaciones en respuestas de detalle

### app/routers/rendimientos.py  ← CREAR ESTE ARCHIVO

Endpoints requeridos:
- POST   /rendimientos/bulk        → RendimientoBulkCreate (carga masiva, el más usado desde la app móvil)
- POST   /rendimientos             → RendimientoCreate (individual)
- GET    /rendimientos?actividad_id= → listar rendimientos de una actividad con datos del trabajador
- PATCH  /rendimientos/{id}        → RendimientoUpdate
- DELETE /rendimientos/{id}        → solo si actividad en estado creada(1) o revisada(2)

Validaciones clave:
- El trabajador_id debe estar en actividad_trabajador para esa actividad
- Solo un rendimiento por trabajador por actividad (upsert o validar duplicado)
- Verificar acceso al campo de la actividad antes de operar

### app/main.py  ← CREAR ESTE ARCHIVO

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, empresa_campo, usuarios, maestros, actividades, rendimientos

app = FastAPI(
    title="Control de Labores API",
    description="API para gestión de labores agrícolas — AxionaTek",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(empresa_campo.router)
app.include_router(usuarios.router)
app.include_router(maestros.router)
app.include_router(actividades.router)
app.include_router(rendimientos.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 6. CONVENCIONES DEL PROYECTO

- Todos los routers usan `await db.flush()` + `await db.refresh()` (no commit — lo hace get_db al salir)
- `verify_campo_access(campo_id, current_user, db)` se llama manualmente (no como Depends) porque recibe db como parámetro directo
- Paginación: no implementada aún, agregar skip/limit si se necesita
- Todos los errores usan HTTPException con detail en español
- `model_dump(exclude_none=True)` para PATCHes parciales
- `selectinload` para eager loading de relaciones en respuestas de detalle
- Los archivos __init__.py de routers y schemas están vacíos
