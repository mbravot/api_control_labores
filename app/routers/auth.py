from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.security import verify_password, create_access_token
from app.models.usuario import Usuario, UsuarioCampo, Campo
from app.schemas.usuario import TokenResponse, CampoSimpleResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.rol))
        .where(
            (Usuario.email == form_data.username) |
            (Usuario.usuario == form_data.username)
        )
    )
    usuario = result.scalar_one_or_none()

    if usuario is None or not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if usuario.estado_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token = create_access_token(data={"sub": str(usuario.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        rol_id=usuario.rol_id,
        rol=usuario.rol.nombre,
        empresa_id=usuario.empresa_id,
    )


@router.get("/mis-campos", response_model=List[CampoSimpleResponse])
async def mis_campos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna los campos autorizados para el usuario autenticado."""
    result = await db.execute(
        select(Campo)
        .join(UsuarioCampo, UsuarioCampo.campo_id == Campo.id)
        .where(UsuarioCampo.usuario_id == current_user.id)
        .order_by(Campo.nombre)
    )
    return result.scalars().all()


@router.post("/seleccionar-campo/{campo_id}", response_model=TokenResponse)
async def seleccionar_campo(
    campo_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Emite un nuevo token con el campo activo seleccionado."""
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

    access_token = create_access_token(
        data={"sub": str(current_user.id), "campo_id": campo_id}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        usuario_id=current_user.id,
        nombre=current_user.nombre,
        rol_id=current_user.rol_id,
        rol=current_user.rol.nombre,
        empresa_id=current_user.empresa_id,
        campo_id=campo_id,
    )
