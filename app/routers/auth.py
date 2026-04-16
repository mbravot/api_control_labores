from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.usuario import Usuario
from app.schemas.usuario import TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario).where(Usuario.email == form_data.username)
    )
    usuario = result.scalar_one_or_none()

    if usuario is None or not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
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
        rol=usuario.rol,
        empresa_id=usuario.empresa_id,
    )
