from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user, verify_campo_access
from app.models.usuario import Usuario
from app.models.actividad import (
    Actividad,
    ActividadTrabajador,
    Rendimiento,
)
from app.schemas.actividad import (
    RendimientoCreate,
    RendimientoBulkCreate,
    RendimientoUpdate,
    RendimientoResponse,
)

router = APIRouter(prefix="/rendimientos", tags=["Rendimientos"])


# ---------------------------------------------------------------
# POST /rendimientos/bulk — Carga masiva (uso principal desde app móvil)
# ---------------------------------------------------------------

@router.post("/bulk", response_model=List[RendimientoResponse], status_code=status.HTTP_201_CREATED)
async def crear_rendimientos_bulk(
    payload: RendimientoBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad_con_acceso(payload.actividad_id, current_user, db)

    # Obtener trabajadores asignados a la actividad
    asignados = await _get_trabajadores_asignados(actividad.id, db)

    creados = []
    for item in payload.rendimientos:
        if item.actividad_id != payload.actividad_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos los rendimientos deben pertenecer a la misma actividad",
            )

        if item.trabajador_id not in asignados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El trabajador {item.trabajador_id} no está asignado a esta actividad",
            )

        # Verificar duplicado
        await _verificar_duplicado(actividad.id, item.trabajador_id, db)

        rendimiento = Rendimiento(
            actividad_id=actividad.id,
            trabajador_id=item.trabajador_id,
            cantidad=item.cantidad,
            observacion=item.observacion,
        )
        db.add(rendimiento)
        creados.append(rendimiento)

    await db.flush()

    # Recargar con datos del trabajador
    ids = [r.id for r in creados]
    result = await db.execute(
        select(Rendimiento)
        .options(selectinload(Rendimiento.trabajador))
        .where(Rendimiento.id.in_(ids))
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# POST /rendimientos — Crear individual
# ---------------------------------------------------------------

@router.post("", response_model=RendimientoResponse, status_code=status.HTTP_201_CREATED)
async def crear_rendimiento(
    payload: RendimientoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad_con_acceso(payload.actividad_id, current_user, db)

    # Verificar que el trabajador está asignado
    asignados = await _get_trabajadores_asignados(actividad.id, db)
    if payload.trabajador_id not in asignados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El trabajador no está asignado a esta actividad",
        )

    # Verificar duplicado
    await _verificar_duplicado(actividad.id, payload.trabajador_id, db)

    rendimiento = Rendimiento(
        actividad_id=actividad.id,
        trabajador_id=payload.trabajador_id,
        cantidad=payload.cantidad,
        observacion=payload.observacion,
    )
    db.add(rendimiento)
    await db.flush()

    # Recargar con datos del trabajador
    result = await db.execute(
        select(Rendimiento)
        .options(selectinload(Rendimiento.trabajador))
        .where(Rendimiento.id == rendimiento.id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# GET /rendimientos?actividad_id= — Listar por actividad
# ---------------------------------------------------------------

@router.get("", response_model=List[RendimientoResponse])
async def listar_rendimientos(
    actividad_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await _get_actividad_con_acceso(actividad_id, current_user, db)

    result = await db.execute(
        select(Rendimiento)
        .options(selectinload(Rendimiento.trabajador))
        .where(Rendimiento.actividad_id == actividad_id)
        .order_by(Rendimiento.id)
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# PATCH /rendimientos/{id} — Actualizar rendimiento
# ---------------------------------------------------------------

@router.patch("/{rendimiento_id}", response_model=RendimientoResponse)
async def actualizar_rendimiento(
    rendimiento_id: int,
    payload: RendimientoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    rendimiento = await _get_rendimiento(rendimiento_id, db)
    await _get_actividad_con_acceso(rendimiento.actividad_id, current_user, db)

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(rendimiento, field, value)

    await db.flush()

    # Recargar con datos del trabajador
    result = await db.execute(
        select(Rendimiento)
        .options(selectinload(Rendimiento.trabajador))
        .where(Rendimiento.id == rendimiento.id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# DELETE /rendimientos/{id} — Solo si actividad en estado 1 o 2
# ---------------------------------------------------------------

@router.delete("/{rendimiento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_rendimiento(
    rendimiento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    rendimiento = await _get_rendimiento(rendimiento_id, db)
    actividad = await _get_actividad_con_acceso(rendimiento.actividad_id, current_user, db)

    if actividad.estado_id not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar rendimientos de actividades en estado 'creada' o 'revisada'",
        )

    await db.delete(rendimiento)
    await db.flush()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_actividad_con_acceso(
    actividad_id: int,
    current_user: Usuario,
    db: AsyncSession,
) -> Actividad:
    result = await db.execute(
        select(Actividad).where(Actividad.id == actividad_id)
    )
    actividad = result.scalar_one_or_none()
    if actividad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada",
        )
    await verify_campo_access(actividad.campo_id, current_user, db)
    return actividad


async def _get_rendimiento(rendimiento_id: int, db: AsyncSession) -> Rendimiento:
    result = await db.execute(
        select(Rendimiento).where(Rendimiento.id == rendimiento_id)
    )
    rendimiento = result.scalar_one_or_none()
    if rendimiento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendimiento no encontrado",
        )
    return rendimiento


async def _get_trabajadores_asignados(actividad_id: int, db: AsyncSession) -> set:
    result = await db.execute(
        select(ActividadTrabajador.trabajador_id).where(
            ActividadTrabajador.actividad_id == actividad_id
        )
    )
    return set(result.scalars().all())


async def _verificar_duplicado(
    actividad_id: int, trabajador_id: int, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Rendimiento).where(
            Rendimiento.actividad_id == actividad_id,
            Rendimiento.trabajador_id == trabajador_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un rendimiento para el trabajador {trabajador_id} en esta actividad",
        )
