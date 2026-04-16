from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin
from app.core.security import get_password_hash
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    payload: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email")

    usuario = Usuario(
        nombre=payload.nombre,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        rol=payload.rol,
        empresa_id=payload.empresa_id,
    )
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)
    return usuario


@router.get("", response_model=List[UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    result = await db.execute(
        select(Usuario)
        .where(Usuario.empresa_id == current_user.empresa_id)
        .order_by(Usuario.nombre)
    )
    return result.scalars().all()


@router.get("/me", response_model=UsuarioResponse)
async def obtener_perfil(current_user: Usuario = Depends(get_current_active_user)):
    return current_user


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obtener_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    return await _get_usuario(usuario_id, db)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    usuario = await _get_usuario(usuario_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(usuario, field, value)
    await db.flush()
    await db.refresh(usuario)
    return usuario


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_usuario(usuario_id: int, db: AsyncSession) -> Usuario:
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario
