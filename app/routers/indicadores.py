from typing import List, Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, verify_campo_access
from app.models.usuario import Usuario
from app.models.actividad import (
    Actividad, ActividadTrabajador, Rendimiento, RendimientoGrupal,
    Trabajador, HorasPorDia, Permiso,
)
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

    # 1. Config de horas por día de la empresa → {nombredia_id: horas}
    res_hpd = await db.execute(
        select(HorasPorDia.nombredia_id, HorasPorDia.horas_dias)
        .where(HorasPorDia.empresa_id == current_user.empresa_id)
    )
    horas_por_dia: dict[int, float] = {row[0]: row[1] for row in res_hpd.all()}

    # Filtros comunes sobre actividad (rendimientos individuales y grupales)
    filtros_actividad = [
        Actividad.campo_id == campo_id,
        Actividad.usuario_id == current_user.id,
        Actividad.tipopersonal_id == 1,
        Actividad.estado_id == 1,
    ]
    if fecha_desde:
        filtros_actividad.append(Actividad.fecha >= fecha_desde)
    if fecha_hasta:
        filtros_actividad.append(Actividad.fecha <= fecha_hasta)

    # 2. Rendimientos individuales agregados por (trabajador, fecha)
    stmt_ind = (
        select(
            Rendimiento.trabajador_id.label("trabajador_id"),
            Actividad.fecha.label("fecha"),
            func.sum(Rendimiento.horas_trabajadas).label("horas"),
        )
        .join(Actividad, Rendimiento.actividad_id == Actividad.id)
        .where(*filtros_actividad)
        .group_by(Rendimiento.trabajador_id, Actividad.fecha)
    )
    res_ind = await db.execute(stmt_ind)

    # 3. Rendimientos grupales expandidos por cada trabajador asignado a la actividad
    stmt_grp = (
        select(
            ActividadTrabajador.trabajador_id.label("trabajador_id"),
            Actividad.fecha.label("fecha"),
            func.sum(RendimientoGrupal.horas_trabajadas).label("horas"),
        )
        .join(Actividad, RendimientoGrupal.actividad_id == Actividad.id)
        .join(ActividadTrabajador, ActividadTrabajador.actividad_id == Actividad.id)
        .where(*filtros_actividad)
        .group_by(ActividadTrabajador.trabajador_id, Actividad.fecha)
    )
    res_grp = await db.execute(stmt_grp)

    # 4. Permisos de propios del campo (independiente del usuario supervisor)
    filtros_permiso = [
        Trabajador.campo_id == campo_id,
        Trabajador.tipotrabajador_id == 1,
    ]
    if fecha_desde:
        filtros_permiso.append(Permiso.fecha >= fecha_desde)
    if fecha_hasta:
        filtros_permiso.append(Permiso.fecha <= fecha_hasta)

    stmt_perm = (
        select(
            Permiso.trabajador_id.label("trabajador_id"),
            Permiso.fecha.label("fecha"),
            func.sum(Permiso.horas_permiso).label("horas"),
        )
        .join(Trabajador, Permiso.trabajador_id == Trabajador.id)
        .where(*filtros_permiso)
        .group_by(Permiso.trabajador_id, Permiso.fecha)
    )
    res_perm = await db.execute(stmt_perm)

    # 5. Merge en un dict: {(trabajador_id, fecha): {ind, grp, perm}}
    agregados: dict[tuple[int, date_type], dict[str, float]] = {}

    def _acumular(rows, campo: str):
        for r in rows:
            key = (r.trabajador_id, r.fecha)
            if key not in agregados:
                agregados[key] = {"ind": 0.0, "grp": 0.0, "perm": 0.0}
            agregados[key][campo] += float(r.horas or 0.0)

    _acumular(res_ind.all(), "ind")
    _acumular(res_grp.all(), "grp")
    _acumular(res_perm.all(), "perm")

    if not agregados:
        return []

    # 6. Datos de trabajador en un solo query
    trabajador_ids = {k[0] for k in agregados.keys()}
    res_trab = await db.execute(
        select(Trabajador.id, Trabajador.nombre, Trabajador.rut)
        .where(Trabajador.id.in_(trabajador_ids))
    )
    info_trab = {row.id: (row.nombre, row.rut) for row in res_trab.all()}

    # 7. Construir respuesta
    items: List[IndicadorHorasDiariasPropio] = []
    for (trabajador_id, fecha), h in agregados.items():
        nombre, rut = info_trab.get(trabajador_id, (f"#{trabajador_id}", None))
        nombredia_id = fecha.isoweekday()
        horas_esperadas = horas_por_dia.get(nombredia_id)

        horas_individual = round(h["ind"], 2)
        horas_grupal = round(h["grp"], 2)
        horas_trabajadas = round(horas_individual + horas_grupal, 2)
        horas_permiso = round(h["perm"], 2)
        total_horas = round(horas_trabajadas + horas_permiso, 2)

        if horas_esperadas is None:
            diferencia = None
            cumple = None
        else:
            diferencia = round(total_horas - horas_esperadas, 2)
            cumple = total_horas <= horas_esperadas

        items.append(IndicadorHorasDiariasPropio(
            trabajador_id=trabajador_id,
            trabajador_nombre=nombre,
            trabajador_rut=rut,
            fecha=fecha,
            nombredia_id=nombredia_id,
            horas_individual=horas_individual,
            horas_grupal=horas_grupal,
            horas_trabajadas=horas_trabajadas,
            horas_permiso=horas_permiso,
            total_horas=total_horas,
            horas_extras=0.0,
            horas_esperadas=horas_esperadas,
            diferencia=diferencia,
            cumple=cumple,
        ))

    items.sort(key=lambda x: (x.fecha, x.trabajador_nombre), reverse=False)
    items.sort(key=lambda x: x.fecha, reverse=True)
    return items
