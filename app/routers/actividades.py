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
    Actividad, ActividadTrabajador, EstadoActividad, Trabajador, Rendimiento, RendimientoGrupal, Ceco,
)
from app.schemas.actividad import (
    ActividadCreate, ActividadUpdate, ActividadResponse,
    ActividadDetalleResponse, ActividadTrabajadorResponse,
)
from app.routers.rendimientos import _calcular_horas

router = APIRouter(prefix="/actividades", tags=["Actividades"])


# ---------------------------------------------------------------
# POST /actividades
# ---------------------------------------------------------------

@router.post("", response_model=ActividadDetalleResponse, status_code=status.HTTP_201_CREATED)
async def crear_actividad(
    payload: ActividadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)

    result = await db.execute(select(Ceco).where(Ceco.id == payload.ceco_id, Ceco.campo_id == payload.campo_id))
    ceco = result.scalar_one_or_none()
    if ceco is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ceco no encontrado o no pertenece al campo")

    result = await db.execute(
        select(Trabajador).where(
            Trabajador.id.in_(payload.trabajador_ids),
            Trabajador.campo_id == payload.campo_id,
            Trabajador.estado_id == 1,
        )
    )
    trabajadores = result.scalars().all()

    if len(trabajadores) != len(payload.trabajador_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más trabajadores no existen, no pertenecen al campo o están inactivos",
        )

    contratista_ids = set()
    for t in trabajadores:
        if t.tipotrabajador_id != payload.tipopersonal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El trabajador '{t.nombre}' no coincide con el tipo de personal de la actividad",
            )
        if t.contratista_id is not None:
            contratista_ids.add(t.contratista_id)

    if len(contratista_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todos los trabajadores deben pertenecer al mismo contratista",
        )

    personal_id = contratista_ids.pop() if contratista_ids else None

    actividad = Actividad(
        campo_id=payload.campo_id,
        usuario_id=current_user.id,
        fecha=payload.fecha,
        tipopersonal_id=payload.tipopersonal_id,
        personal_id=personal_id,
        tiporendimiento_id=payload.tiporendimiento_id,
        labor_id=payload.labor_id,
        unidad_medida_id=payload.unidad_medida_id,
        cecotipo_id=ceco.cecotipo_id,
        ceco_id=payload.ceco_id,
        tarifa=payload.tarifa,
        hora_inicio=payload.hora_inicio,
        hora_fin=payload.hora_fin,
        estado_id=1,
    )
    db.add(actividad)
    await db.flush()

    for tid in payload.trabajador_ids:
        db.add(ActividadTrabajador(actividad_id=actividad.id, trabajador_id=tid))
    await db.flush()
    await db.commit()

    return await _get_actividad_con_detalle(actividad.id, db)


# ---------------------------------------------------------------
# GET /actividades
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
        .where(Actividad.campo_id == campo_id, Actividad.estado_id == (estado_id or 1))
    )
    if fecha_desde:
        stmt = stmt.where(Actividad.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(Actividad.fecha <= fecha_hasta)

    result = await db.execute(stmt.order_by(Actividad.fecha.desc(), Actividad.id.desc()))
    return result.scalars().all()


# ---------------------------------------------------------------
# GET /actividades/{id}
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
# PATCH /actividades/{id}
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

    cambios = payload.model_dump(exclude_none=True)
    for field, value in cambios.items():
        setattr(actividad, field, value)
    await db.flush()

    if "hora_inicio" in cambios or "hora_fin" in cambios:
        horas, extras = _calcular_horas(actividad)
        await db.execute(
            Rendimiento.__table__.update()
            .where(Rendimiento.actividad_id == actividad_id)
            .values(horas_trabajadas=horas, horas_extras=extras)
        )
        await db.execute(
            RendimientoGrupal.__table__.update()
            .where(RendimientoGrupal.actividad_id == actividad_id)
            .values(horas_trabajadas=horas, horas_extras=extras)
        )
        await db.flush()

    result = await db.execute(
        select(Actividad).options(selectinload(Actividad.estado))
        .where(Actividad.id == actividad_id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# DELETE /actividades/{id}
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
# POST /actividades/{id}/trabajadores
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

    result = await db.execute(
        select(Trabajador).where(
            Trabajador.id.in_(nuevos_ids),
            Trabajador.campo_id == actividad.campo_id,
            Trabajador.estado_id == 1,
        )
    )
    trabajadores = result.scalars().all()

    if len(trabajadores) != len(nuevos_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más trabajadores no existen, no pertenecen al campo o están inactivos",
        )

    for t in trabajadores:
        if t.tipotrabajador_id != actividad.tipopersonal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El trabajador '{t.nombre}' no coincide con el tipo de personal de la actividad",
            )

    asignaciones = []
    for tid in nuevos_ids:
        at = ActividadTrabajador(actividad_id=actividad_id, trabajador_id=tid)
        db.add(at)
        asignaciones.append(at)

    await db.flush()
    for at in asignaciones:
        await db.refresh(at)

    ids = [at.id for at in asignaciones]
    result = await db.execute(
        select(ActividadTrabajador)
        .options(selectinload(ActividadTrabajador.trabajador).selectinload(Trabajador.tipo_personal))
        .where(ActividadTrabajador.id.in_(ids))
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# DELETE /actividades/{id}/trabajadores/{trabajador_id}
# ---------------------------------------------------------------

@router.delete("/{actividad_id}/trabajadores/{trabajador_id}", status_code=status.HTTP_204_NO_CONTENT)
async def quitar_trabajador(
    actividad_id: int,
    trabajador_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    actividad = await _get_actividad(actividad_id, db)
    await verify_campo_access(actividad.campo_id, current_user, db)

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
# PATCH /actividades/{id}/estado
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

    result = await db.execute(select(EstadoActividad).where(EstadoActividad.id == actividad.estado_id))
    estado_actual = result.scalar_one()

    result = await db.execute(select(EstadoActividad).where(EstadoActividad.id == estado_id))
    estado_nuevo = result.scalar_one_or_none()
    if estado_nuevo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado no válido")

    if estado_nuevo.orden != estado_actual.orden + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede avanzar al siguiente estado. Actual: '{estado_actual.nombre}' (orden {estado_actual.orden})",
        )

    actividad.estado_id = estado_id
    await db.flush()

    result = await db.execute(
        select(Actividad).options(selectinload(Actividad.estado))
        .where(Actividad.id == actividad_id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_actividad(actividad_id: int, db: AsyncSession) -> Actividad:
    result = await db.execute(select(Actividad).where(Actividad.id == actividad_id))
    actividad = result.scalar_one_or_none()
    if actividad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return actividad


async def _get_actividad_con_detalle(actividad_id: int, db: AsyncSession) -> Actividad:
    result = await db.execute(
        select(Actividad)
        .options(
            selectinload(Actividad.estado),
            selectinload(Actividad.trabajadores).selectinload(ActividadTrabajador.trabajador).selectinload(Trabajador.tipo_personal),
            selectinload(Actividad.rendimientos).selectinload(Rendimiento.trabajador).selectinload(Trabajador.tipo_personal),
        )
        .where(Actividad.id == actividad_id)
    )
    actividad = result.scalar_one_or_none()
    if actividad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return actividad
