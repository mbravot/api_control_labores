from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin
from app.models.usuario import Empresa, Campo, Usuario, UsuarioCampo
from app.schemas.usuario import (
    EmpresaCreate,
    EmpresaResponse,
    CampoCreate,
    CampoUpdate,
    CampoResponse,
    UsuarioCampoCreate,
    UsuarioCampoResponse,
)

router = APIRouter(tags=["Empresa y Campos"])


# ---------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------

@router.post("/empresas", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
async def crear_empresa(
    payload: EmpresaCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    result = await db.execute(select(Empresa).where(Empresa.rut == payload.rut))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una empresa con ese RUT")

    empresa = Empresa(**payload.model_dump())
    db.add(empresa)
    await db.flush()
    await db.refresh(empresa)
    return empresa


@router.get("/empresas", response_model=List[EmpresaResponse])
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    result = await db.execute(select(Empresa).order_by(Empresa.razon_social))
    return result.scalars().all()


@router.get("/empresas/{empresa_id}", response_model=EmpresaResponse)
async def obtener_empresa(
    empresa_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    empresa = await _get_empresa(empresa_id, db)
    return empresa


# ---------------------------------------------------------------
# Campos
# ---------------------------------------------------------------

@router.post("/campos", response_model=CampoResponse, status_code=status.HTTP_201_CREATED)
async def crear_campo(
    payload: CampoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    campo = Campo(**payload.model_dump())
    db.add(campo)
    await db.flush()
    await db.refresh(campo)
    return campo


@router.get("/campos", response_model=List[CampoResponse])
async def listar_campos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Campo)
        .where(Campo.empresa_id == current_user.empresa_id)
        .order_by(Campo.nombre)
    )
    return result.scalars().all()


@router.get("/campos/{campo_id}", response_model=CampoResponse)
async def obtener_campo(
    campo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    return await _get_campo(campo_id, db)


@router.patch("/campos/{campo_id}", response_model=CampoResponse)
async def actualizar_campo(
    campo_id: int,
    payload: CampoUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    campo = await _get_campo(campo_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(campo, field, value)
    await db.flush()
    await db.refresh(campo)
    return campo


# ---------------------------------------------------------------
# Asignación usuario-campo
# ---------------------------------------------------------------

@router.post("/usuario-campo", response_model=UsuarioCampoResponse, status_code=status.HTTP_201_CREATED)
async def asignar_usuario_campo(
    payload: UsuarioCampoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    result = await db.execute(
        select(UsuarioCampo).where(
            UsuarioCampo.usuario_id == payload.usuario_id,
            UsuarioCampo.campo_id == payload.campo_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario ya tiene acceso a este campo")

    uc = UsuarioCampo(**payload.model_dump())
    db.add(uc)
    await db.flush()
    await db.refresh(uc)
    return uc


@router.delete("/usuario-campo/{uc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def quitar_usuario_campo(
    uc_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    result = await db.execute(select(UsuarioCampo).where(UsuarioCampo.id == uc_id))
    uc = result.scalar_one_or_none()
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asignación no encontrada")
    await db.delete(uc)
    await db.flush()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_empresa(empresa_id: int, db: AsyncSession) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    return empresa


async def _get_campo(campo_id: int, db: AsyncSession) -> Campo:
    result = await db.execute(select(Campo).where(Campo.id == campo_id))
    campo = result.scalar_one_or_none()
    if campo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campo no encontrado")
    return campo
