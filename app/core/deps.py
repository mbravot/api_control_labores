from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Verifica que el usuario tenga acceso al campo solicitado."""
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
