from typing import List, Optional
from datetime import date

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
    EstadoActividad,
    Trabajador,
    Rendimiento,
)
from app.schemas.actividad import (
    ActividadCreate,
    ActividadUpdate,
    ActividadResponse,
    ActividadDetalleResponse,
    ActividadTrabajadorResponse,
)

router = APIRouter(prefix="/actividades", tags=["Actividades"])


# ---------------------------------------------------------------
# POST /actividades — Crear actividad + asignar trabajadores
# ---------------------------------------------------------------

@router.post(
    "",
    response_model=ActividadDetalleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_actividad(
    payload: ActividadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)

    # Validar que los trabajadores existen, pertenecen al campo y coinciden en tipo
    result = await db.execute(
        select(Trabajador).where(
            Trabajador.id.in_(payload.trabajador_ids),
            Trabajador.campo_id == payload.campo_id,
            Trabajador.activo == True,
        )
    )
    trabajadores = result.scalars().all()

    if len(trabajadores) != len(payload.trabajador_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más trabajadores no existen, no pertenecen al campo o están inactivos",
        )

    # Validar que el tipo del trabajador coincide con tipo_personal de la actividad
    for t in trabajadores:
        if t.tipo != payload.tipo_personal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El trabajador '{t.nombre}' es de tipo '{t.tipo}' "
                       f"pero la actividad requiere '{payload.tipo_personal}'",
            )

    actividad = Actividad(
        campo_id=payload.campo_id,
        usuario_id=current_user.id,
        ceco_id=payload.ceco_id,
        labor_id=payload.labor_id,
        unidad_medida_id=payload.unidad_medida_id,
        estado_id=1,
        fecha=payload.fecha,
        tipo_personal=payload.tipo_personal,
        tipo_rendimiento=payload.tipo_rendimiento,
        tarifa=payload.tarifa,
        hora_inicio=payload.hora_inicio,
        hora_fin=payload.hora_fin,
        observaciones=payload.observaciones,
    )
    db.add(actividad)
    await db.flush()

    for tid in payload.trabajador_ids:
        db.add(ActividadTrabajador(actividad_id=actividad.id, trabajador_id=tid))
    await db.flush()

    # Recargar con relaciones
    result = await db.execute(
        select(Actividad)
        .options(
            selectinload(Actividad.estado),
            selectinload(Actividad.trabajadores).selectinload(ActividadTrabajador.trabajador),
            selectinload(Actividad.rendimientos).selectinload(Rendimiento.trabajador),
        )
        .where(Actividad.id == actividad.id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# GET /actividades — Listar con filtros
# ---------------------------------------------------------------

@router.get("", response_model=List[ActividadResponse])
async def listar_actividades(
    campo_id: int = Query(...),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    estado_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)

    stmt = (
        select(Actividad)
        .options(selectinload(Actividad.estado))
        .where(Actividad.campo_id == campo_id)
    )

    if fecha_desde:
        stmt = stmt.where(Actividad.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(Actividad.fecha <= fecha_hasta)
    if estado_id:
        stmt = stmt.where(Actividad.estado_id == estado_id)

    stmt = stmt.order_by(Actividad.fecha.desc(), Actividad.id.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------
# GET /actividades/{id} — Detalle con trabajadores y rendimientos
# ---------------------------------------------------------------

@router.get("/{actividad_id}", response_model=ActividadDetalleResponse)
async def obtener_actividad(
    actividad_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad_con_detalle(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)
    return actividad


# ---------------------------------------------------------------
# PATCH /actividades/{id} — Actualizar campos editables
# ---------------------------------------------------------------

@router.patch("/{actividad_id}", response_model=ActividadResponse)
async def actualizar_actividad(
    actividad_id: int,
    payload: ActividadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

    update_data = payload.model_dump(exclude_none=True)

    # No permitir cambio de estado por este endpoint
    if "estado_id" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use el endpoint PATCH /actividades/{id}/estado para cambiar el estado",
        )

    for field, value in update_data.items():
        setattr(actividad, field, value)

    await db.flush()
    await db.refresh(actividad)

    # Recargar con estado
    result = await db.execute(
        select(Actividad)
        .options(selectinload(Actividad.estado))
        .where(Actividad.id == actividad.id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# DELETE /actividades/{id} — Solo si estado_id == 1 (creada)
# ---------------------------------------------------------------

@router.delete("/{actividad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_actividad(
    actividad_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

    if actividad.estado_id != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar actividades en estado 'creada'",
        )

    await db.delete(actividad)
    await db.flush()


# ---------------------------------------------------------------
# POST /actividades/{id}/trabajadores — Agregar trabajadores
# ---------------------------------------------------------------

@router.post(
    "/{actividad_id}/trabajadores",
    response_model=List[ActividadTrabajadorResponse],
    status_code=status.HTTP_201_CREATED,
)
async def agregar_trabajadores(
    actividad_id: int,
    trabajador_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

    # Obtener IDs ya asignados
    result = await db.execute(
        select(ActividadTrabajador.trabajador_id).where(
            ActividadTrabajador.actividad_id == actividad_id
        )
    )
    existentes = set(result.scalars().all())

    nuevos_ids = [tid for tid in trabajador_ids if tid not in existentes]
    if not nuevos_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todos los trabajadores ya están asignados a esta actividad",
        )

    # Validar trabajadores
    result = await db.execute(
        select(Trabajador).where(
            Trabajador.id.in_(nuevos_ids),
            Trabajador.campo_id == actividad.campo_id,
            Trabajador.activo == True,
        )
    )
    trabajadores = result.scalars().all()

    if len(trabajadores) != len(nuevos_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más trabajadores no existen, no pertenecen al campo o están inactivos",
        )

    for t in trabajadores:
        if t.tipo != actividad.tipo_personal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El trabajador '{t.nombre}' es de tipo '{t.tipo}' "
                       f"pero la actividad requiere '{actividad.tipo_personal}'",
            )

    asignaciones = []
    for tid in nuevos_ids:
        at = ActividadTrabajador(actividad_id=actividad_id, trabajador_id=tid)
        db.add(at)
        asignaciones.append(at)

    await db.flush()
    for at in asignaciones:
        await db.refresh(at)

    # Recargar con datos del trabajador
    result = await db.execute(
        select(ActividadTrabajador)
        .options(selectinload(ActividadTrabajador.trabajador))
        .where(ActividadTrabajador.id.in_([at.id for at in asignaciones]))
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# DELETE /actividades/{id}/trabajadores/{trabajador_id}
# ---------------------------------------------------------------

@router.delete(
    "/{actividad_id}/trabajadores/{trabajador_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def quitar_trabajador(
    actividad_id: int,
    trabajador_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

    # Verificar que no tenga rendimiento registrado
    result = await db.execute(
        select(Rendimiento).where(
            Rendimiento.actividad_id == actividad_id,
            Rendimiento.trabajador_id == trabajador_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede quitar un trabajador que ya tiene rendimiento registrado",
        )

    result = await db.execute(
        select(ActividadTrabajador).where(
            ActividadTrabajador.actividad_id == actividad_id,
            ActividadTrabajador.trabajador_id == trabajador_id,
        )
    )
    at = result.scalar_one_or_none()
    if at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El trabajador no está asignado a esta actividad",
        )

    await db.delete(at)
    await db.flush()


# ---------------------------------------------------------------
# PATCH /actividades/{id}/estado — Avanzar estado secuencial
# ---------------------------------------------------------------

@router.patch("/{actividad_id}/estado", response_model=ActividadResponse)
async def cambiar_estado(
    actividad_id: int,
    estado_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

    # Obtener estado actual y nuevo
    result = await db.execute(
        select(EstadoActividad).where(EstadoActividad.id == actividad.estado_id)
    )
    estado_actual = result.scalar_one()

    result = await db.execute(
        select(EstadoActividad).where(EstadoActividad.id == estado_id)
    )
    estado_nuevo = result.scalar_one_or_none()
    if estado_nuevo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado no válido",
        )

    # Solo avanzar (no retroceder), y debe ser el siguiente inmediato
    if estado_nuevo.orden != estado_actual.orden + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede avanzar al siguiente estado. "
                   f"Estado actual: '{estado_actual.nombre}' (orden {estado_actual.orden}), "
                   f"siguiente esperado: orden {estado_actual.orden + 1}",
        )

    actividad.estado_id = estado_id
    await db.flush()

    # Recargar con estado
    result = await db.execute(
        select(Actividad)
        .options(selectinload(Actividad.estado))
        .where(Actividad.id == actividad.id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_actividad(actividad_id: int, db: AsyncSession) -> Actividad:
    result = await db.execute(
        select(Actividad).where(Actividad.id == actividad_id)
    )
    actividad = result.scalar_one_or_none()
    if actividad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada",
        )
    return actividad


async def _get_actividad_con_detalle(actividad_id: int, db: AsyncSession) -> Actividad:
    result = await db.execute(
        select(Actividad)
        .options(
            selectinload(Actividad.estado),
            selectinload(Actividad.trabajadores).selectinload(ActividadTrabajador.trabajador),
            selectinload(Actividad.rendimientos).selectinload(Rendimiento.trabajador),
        )
        .where(Actividad.id == actividad_id)
    )
    actividad = result.scalar_one_or_none()
    if actividad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada",
        )
    return actividad
