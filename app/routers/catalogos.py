from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.usuario import Usuario
from app.models.actividad import (
    TipoPersonal, TipoRendimiento, CecoTipo, PorcentajeContratista, EstadoActividad,
)
from app.schemas.actividad import (
    TipoPersonalResponse, TipoRendimientoResponse,
    CecoTipoResponse, PorcentajeContratistaResponse,
    EstadoActividadResponse,
)

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])

#Obtiene todos los tipos de personal
@router.get("/tipos-personal", response_model=List[TipoPersonalResponse])
async def listar_tipos_personal(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(TipoPersonal).order_by(TipoPersonal.id))
    return result.scalars().all()

#Obtiene todos los tipos de rendimiento
@router.get("/tipos-rendimiento", response_model=List[TipoRendimientoResponse])
async def listar_tipos_rendimiento(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(TipoRendimiento).order_by(TipoRendimiento.id))
    return result.scalars().all()

#Obtiene todos los ceco-tipos
@router.get("/ceco-tipos", response_model=List[CecoTipoResponse])
async def listar_ceco_tipos(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(CecoTipo).order_by(CecoTipo.id))
    return result.scalars().all()

#Obtiene todos los porcentajes de contratista
@router.get("/porcentajes-contratista", response_model=List[PorcentajeContratistaResponse])
async def listar_porcentajes_contratista(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(PorcentajeContratista).order_by(PorcentajeContratista.porcentaje))
    return result.scalars().all()

#Obtiene todos los estados de actividad
@router.get("/estados-actividad", response_model=List[EstadoActividadResponse])
async def listar_estados_actividad(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(EstadoActividad).order_by(EstadoActividad.orden))
    return result.scalars().all()
