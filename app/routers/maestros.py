from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin, verify_campo_access
from app.models.usuario import Usuario
from app.models.actividad import Trabajador, Ceco, Labor, UnidadMedida
from app.schemas.actividad import (
    TrabajadorCreate,
    TrabajadorUpdate,
    TrabajadorResponse,
    CecoCreate,
    CecoUpdate,
    CecoResponse,
    LaborCreate,
    LaborUpdate,
    LaborResponse,
    UnidadMedidaCreate,
    UnidadMedidaResponse,
)

router = APIRouter(tags=["Maestros"])


# ---------------------------------------------------------------
# Trabajadores
# ---------------------------------------------------------------

@router.post("/trabajadores", response_model=TrabajadorResponse, status_code=status.HTTP_201_CREATED)
async def crear_trabajador(
    payload: TrabajadorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)
    trabajador = Trabajador(**payload.model_dump())
    db.add(trabajador)
    await db.flush()
    await db.refresh(trabajador)
    return trabajador


@router.get("/trabajadores", response_model=List[TrabajadorResponse])
async def listar_trabajadores(
    campo_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    result = await db.execute(
        select(Trabajador)
        .where(Trabajador.campo_id == campo_id)
        .order_by(Trabajador.nombre)
    )
    return result.scalars().all()


@router.patch("/trabajadores/{trabajador_id}", response_model=TrabajadorResponse)
async def actualizar_trabajador(
    trabajador_id: int,
    payload: TrabajadorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    trabajador = await _get_trabajador(trabajador_id, db)
    await verify_campo_access(trabajador.campo_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(trabajador, field, value)
    await db.flush()
    await db.refresh(trabajador)
    return trabajador


# ---------------------------------------------------------------
# CECOs
# ---------------------------------------------------------------

@router.post("/cecos", response_model=CecoResponse, status_code=status.HTTP_201_CREATED)
async def crear_ceco(
    payload: CecoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)
    ceco = Ceco(**payload.model_dump())
    db.add(ceco)
    await db.flush()
    await db.refresh(ceco)
    return ceco


@router.get("/cecos", response_model=List[CecoResponse])
async def listar_cecos(
    campo_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    result = await db.execute(
        select(Ceco).where(Ceco.campo_id == campo_id).order_by(Ceco.nombre)
    )
    return result.scalars().all()


@router.patch("/cecos/{ceco_id}", response_model=CecoResponse)
async def actualizar_ceco(
    ceco_id: int,
    payload: CecoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    ceco = await _get_ceco(ceco_id, db)
    await verify_campo_access(ceco.campo_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ceco, field, value)
    await db.flush()
    await db.refresh(ceco)
    return ceco


# ---------------------------------------------------------------
# Labores
# ---------------------------------------------------------------

@router.post("/labores", response_model=LaborResponse, status_code=status.HTTP_201_CREATED)
async def crear_labor(
    payload: LaborCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)
    labor = Labor(**payload.model_dump())
    db.add(labor)
    await db.flush()
    await db.refresh(labor)
    return labor


@router.get("/labores", response_model=List[LaborResponse])
async def listar_labores(
    campo_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    result = await db.execute(
        select(Labor).where(Labor.campo_id == campo_id).order_by(Labor.nombre)
    )
    return result.scalars().all()


@router.patch("/labores/{labor_id}", response_model=LaborResponse)
async def actualizar_labor(
    labor_id: int,
    payload: LaborUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    labor = await _get_labor(labor_id, db)
    await verify_campo_access(labor.campo_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(labor, field, value)
    await db.flush()
    await db.refresh(labor)
    return labor


# ---------------------------------------------------------------
# Unidades de medida
# ---------------------------------------------------------------

@router.post("/unidades-medida", response_model=UnidadMedidaResponse, status_code=status.HTTP_201_CREATED)
async def crear_unidad_medida(
    payload: UnidadMedidaCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    unidad = UnidadMedida(**payload.model_dump())
    db.add(unidad)
    await db.flush()
    await db.refresh(unidad)
    return unidad


@router.get("/unidades-medida", response_model=List[UnidadMedidaResponse])
async def listar_unidades_medida(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(
        select(UnidadMedida)
        .where(UnidadMedida.empresa_id == current_user.empresa_id)
        .order_by(UnidadMedida.nombre)
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_trabajador(trabajador_id: int, db: AsyncSession) -> Trabajador:
    result = await db.execute(select(Trabajador).where(Trabajador.id == trabajador_id))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajador no encontrado")
    return t


async def _get_ceco(ceco_id: int, db: AsyncSession) -> Ceco:
    result = await db.execute(select(Ceco).where(Ceco.id == ceco_id))
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CECO no encontrado")
    return c


async def _get_labor(labor_id: int, db: AsyncSession) -> Labor:
    result = await db.execute(select(Labor).where(Labor.id == labor_id))
    l = result.scalar_one_or_none()
    if l is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Labor no encontrada")
    return l
