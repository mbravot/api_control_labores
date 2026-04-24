from typing import List, Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, verify_campo_access
from app.models.usuario import Usuario
from app.models.actividad import Actividad, Rendimiento, Trabajador, HorasPorDia
from app.schemas.actividad import IndicadorHorasDiariasPropio

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])


# ---------------------------------------------------------------
# GET /indicadores/horas-diarias-propios?campo_id=
# ---------------------------------------------------------------

@router.get("/horas-diarias-propios", response_model=List[IndicadorHorasDiariasPropio])
async def horas_diarias_propios(
    campo_id: int = Query(...),
    fecha_desde: Optional[date_type] = Query(None),
    fecha_hasta: Optional[date_type] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)

    # 1. Cargar config de horas por día de la empresa → {nombredia_id: horas}
    res_hpd = await db.execute(
        select(HorasPorDia.nombredia_id, HorasPorDia.horas_dias)
        .where(HorasPorDia.empresa_id == current_user.empresa_id)
    )
    horas_por_dia: dict[int, float] = {row[0]: row[1] for row in res_hpd.all()}

    # 2. Agregar horas trabajadas por trabajador y fecha
    filtros = [
        Actividad.campo_id == campo_id,
        Actividad.usuario_id == current_user.id,
        Actividad.tipopersonal_id == 1,
        Actividad.estado_id == 1,
    ]
    if fecha_desde:
        filtros.append(Actividad.fecha >= fecha_desde)
    if fecha_hasta:
        filtros.append(Actividad.fecha <= fecha_hasta)

    stmt = (
        select(
            Trabajador.id.label("trabajador_id"),
            Trabajador.nombre.label("trabajador_nombre"),
            Trabajador.rut.label("trabajador_rut"),
            Actividad.fecha.label("fecha"),
            func.sum(Rendimiento.horas_trabajadas).label("horas_trabajadas"),
            func.sum(Rendimiento.horas_extras).label("horas_extras"),
        )
        .join(Actividad, Rendimiento.actividad_id == Actividad.id)
        .join(Trabajador, Rendimiento.trabajador_id == Trabajador.id)
        .where(*filtros)
        .group_by(Trabajador.id, Trabajador.nombre, Trabajador.rut, Actividad.fecha)
        .order_by(Actividad.fecha.desc(), Trabajador.nombre)
    )
    result = await db.execute(stmt)

    # 3. Armar respuesta con cálculo cumple/diferencia
    items: List[IndicadorHorasDiariasPropio] = []
    for row in result.all():
        nombredia_id = row.fecha.isoweekday()  # 1=lunes ... 7=domingo
        horas_esperadas = horas_por_dia.get(nombredia_id)
        horas_trabajadas = float(row.horas_trabajadas or 0.0)
        horas_extras = float(row.horas_extras or 0.0)

        if horas_esperadas is None:
            diferencia = None
            cumple = None
        else:
            diferencia = round(horas_trabajadas - horas_esperadas, 2)
            cumple = horas_trabajadas <= horas_esperadas

        items.append(IndicadorHorasDiariasPropio(
            trabajador_id=row.trabajador_id,
            trabajador_nombre=row.trabajador_nombre,
            trabajador_rut=row.trabajador_rut,
            fecha=row.fecha,
            nombredia_id=nombredia_id,
            horas_trabajadas=round(horas_trabajadas, 2),
            horas_extras=round(horas_extras, 2),
            horas_esperadas=horas_esperadas,
            diferencia=diferencia,
            cumple=cumple,
        ))

    return items
