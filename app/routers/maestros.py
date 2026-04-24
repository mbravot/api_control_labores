from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin, verify_campo_access
from app.models.usuario import Usuario
from app.models.actividad import (
    Trabajador, Ceco, Labor, UnidadMedida, Contratista, Permiso, HorasPorDia,
)
from app.schemas.actividad import (
    TrabajadorCreate, TrabajadorUpdate, TrabajadorResponse,
    CecoCreate, CecoUpdate, CecoResponse,
    LaborCreate, LaborUpdate, LaborResponse,
    UnidadMedidaResponse,
    ContratistaCreate, ContratistaUpdate, ContratistaResponse,
    PermisoCreate, PermisoUpdate, PermisoResponse,
    HorasPorDiaResponse,
)

router = APIRouter(tags=["Maestros"])


# ---------------------------------------------------------------
# Contratistas
# ---------------------------------------------------------------

# Crear contratista
@router.post("/contratistas", response_model=ContratistaResponse, status_code=status.HTTP_201_CREATED)
async def crear_contratista(
    payload: ContratistaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(payload.campo_id, current_user, db)
    contratista = Contratista(**payload.model_dump())
    db.add(contratista)
    await db.flush()
    await db.refresh(contratista)
    return contratista

# Obtiene todos los contratistas de un campo
@router.get("/contratistas", response_model=List[ContratistaResponse])
async def listar_contratistas(
    campo_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    result = await db.execute(
        select(Contratista)
        .where(Contratista.campo_id == campo_id, Contratista.estado_id == 1)
        .order_by(Contratista.nombre)
    )
    return result.scalars().all()


# Obtiene un contratista por id
@router.get("/contratistas/{contratista_id}", response_model=ContratistaResponse)
async def obtener_contratista(
    contratista_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    contratista = await _get_contratista(contratista_id, db)
    await verify_campo_access(contratista.campo_id, current_user, db)
    return contratista


# Actualiza un contratista
@router.patch("/contratistas/{contratista_id}", response_model=ContratistaResponse)
async def actualizar_contratista(
    contratista_id: int,
    payload: ContratistaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    contratista = await _get_contratista(contratista_id, db)
    await verify_campo_access(contratista.campo_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(contratista, field, value)
    await db.flush()
    await db.refresh(contratista)
    return contratista


# Elimina un contratista
@router.delete("/contratistas/{contratista_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_contratista(
    contratista_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    contratista = await _get_contratista(contratista_id, db)
    await verify_campo_access(contratista.campo_id, current_user, db)
    contratista.estado_id = 2
    await db.flush()


# ---------------------------------------------------------------
# Trabajadores
# ---------------------------------------------------------------

# Crear trabajador
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
    result = await db.execute(
        select(Trabajador).options(selectinload(Trabajador.tipo_personal))
        .where(Trabajador.id == trabajador.id)
    )
    return result.scalar_one()


# Obtiene todos los trabajadores de un campo
@router.get("/trabajadores", response_model=List[TrabajadorResponse])
async def listar_trabajadores(
    campo_id: int = Query(...),
    tipotrabajador_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    stmt = (
        select(Trabajador)
        .options(selectinload(Trabajador.tipo_personal))
        .where(Trabajador.campo_id == campo_id, Trabajador.estado_id == 1)
    )
    if tipotrabajador_id:
        stmt = stmt.where(Trabajador.tipotrabajador_id == tipotrabajador_id)
    result = await db.execute(stmt.order_by(Trabajador.nombre))
    return result.scalars().all()

# Obtiene un trabajador por id
@router.get("/trabajadores/{trabajador_id}", response_model=TrabajadorResponse)
async def obtener_trabajador(
    trabajador_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Trabajador).options(selectinload(Trabajador.tipo_personal))
        .where(Trabajador.id == trabajador_id)
    )
    trabajador = result.scalar_one_or_none()
    if trabajador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajador no encontrado")
    await verify_campo_access(trabajador.campo_id, current_user, db)
    return trabajador


# Actualiza un trabajador
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
    result = await db.execute(
        select(Trabajador).options(selectinload(Trabajador.tipo_personal))
        .where(Trabajador.id == trabajador_id)
    )
    return result.scalar_one()


# Elimina un trabajador
@router.delete("/trabajadores/{trabajador_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_trabajador(
    trabajador_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    trabajador = await _get_trabajador(trabajador_id, db)
    await verify_campo_access(trabajador.campo_id, current_user, db)
    trabajador.estado_id = 2
    await db.flush()


# ---------------------------------------------------------------
# CECOs
# ---------------------------------------------------------------

# Crear ceco
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

# Obtiene todos los cecos de un campo
@router.get("/cecos", response_model=List[CecoResponse])
async def listar_cecos(
    campo_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    result = await db.execute(
        select(Ceco)
        .where(Ceco.campo_id == campo_id, Ceco.estado_id == 1)
        .order_by(Ceco.nombre)
    )
    return result.scalars().all()

# Actualiza un ceco
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
# Labores (de empresa, no de campo)
# ---------------------------------------------------------------

# Crear labor
@router.post("/labores", response_model=LaborResponse, status_code=status.HTTP_201_CREATED)
async def crear_labor(
    payload: LaborCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    labor = Labor(**payload.model_dump())
    db.add(labor)
    await db.flush()
    await db.refresh(labor)
    return labor

# Obtiene todas las labores de una empresa
@router.get("/labores", response_model=List[LaborResponse])
async def listar_labores(
    empresa_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    eid = empresa_id or current_user.empresa_id
    result = await db.execute(
        select(Labor)
        .options(selectinload(Labor.unidad))
        .where(Labor.empresa_id == eid, Labor.estado_id == 1)
        .order_by(Labor.nombre)
    )
    return result.scalars().all()

# Actualiza una labor
@router.patch("/labores/{labor_id}", response_model=LaborResponse)
async def actualizar_labor(
    labor_id: int,
    payload: LaborUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    labor = await _get_labor(labor_id, db)
    if labor.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta labor")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(labor, field, value)
    await db.flush()
    await db.refresh(labor)
    return labor


# ---------------------------------------------------------------
# Unidades de medida (catálogo global, solo lectura)
# ---------------------------------------------------------------
# Obtiene todas las unidades de medida
@router.get("/unidades-medida", response_model=List[UnidadMedidaResponse])
async def listar_unidades_medida(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre))
    return result.scalars().all()


# ---------------------------------------------------------------
# Horas por día (configuración de jornada por empresa)
# ---------------------------------------------------------------
# Obtiene las horas por día de la empresa del usuario logueado
@router.get("/horas-por-dia", response_model=List[HorasPorDiaResponse])
async def listar_horas_por_dia(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    result = await db.execute(
        select(HorasPorDia)
        .options(selectinload(HorasPorDia.nombre_dia))
        .where(HorasPorDia.empresa_id == current_user.empresa_id)
        .order_by(HorasPorDia.nombredia_id)
    )
    return result.scalars().all()


# ---------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------
# Crear permiso (solo trabajadores propios)
@router.post("/permisos", response_model=PermisoResponse, status_code=status.HTTP_201_CREATED)
async def crear_permiso(
    payload: PermisoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    trabajador = await _get_trabajador(payload.trabajador_id, db)
    await verify_campo_access(trabajador.campo_id, current_user, db)
    _verificar_trabajador_propio(trabajador)
    permiso = Permiso(**payload.model_dump())
    db.add(permiso)
    await db.flush()
    return await _get_permiso_detalle(permiso.id, db)


# Obtiene todos los permisos de un campo (solo trabajadores propios)
@router.get("/permisos", response_model=List[PermisoResponse])
async def listar_permisos(
    campo_id: int = Query(...),
    trabajador_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    await verify_campo_access(campo_id, current_user, db)
    stmt = (
        select(Permiso)
        .join(Permiso.trabajador)
        .options(
            selectinload(Permiso.trabajador),
            selectinload(Permiso.estado_permiso),
        )
        .where(
            Trabajador.campo_id == campo_id,
            Trabajador.tipotrabajador_id == 1,
        )
    )
    if trabajador_id:
        stmt = stmt.where(Permiso.trabajador_id == trabajador_id)
    result = await db.execute(stmt.order_by(Permiso.fecha.desc()))
    return result.scalars().all()

# Obtiene un permiso por id (solo trabajadores propios)
@router.get("/permisos/{permiso_id}", response_model=PermisoResponse)
async def obtener_permiso(
    permiso_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    permiso = await _get_permiso_detalle(permiso_id, db)
    await verify_campo_access(permiso.trabajador.campo_id, current_user, db)
    _verificar_trabajador_propio(permiso.trabajador)
    return permiso


# Actualiza un permiso (solo trabajadores propios)
@router.patch("/permisos/{permiso_id}", response_model=PermisoResponse)
async def actualizar_permiso(
    permiso_id: int,
    payload: PermisoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    permiso = await _get_permiso(permiso_id, db)
    trabajador = await _get_trabajador(permiso.trabajador_id, db)
    await verify_campo_access(trabajador.campo_id, current_user, db)
    _verificar_trabajador_propio(trabajador)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(permiso, field, value)
    await db.flush()
    return await _get_permiso_detalle(permiso_id, db)


# Elimina un permiso (solo trabajadores propios)
@router.delete("/permisos/{permiso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_permiso(
    permiso_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    permiso = await _get_permiso(permiso_id, db)
    trabajador = await _get_trabajador(permiso.trabajador_id, db)
    await verify_campo_access(trabajador.campo_id, current_user, db)
    _verificar_trabajador_propio(trabajador)
    await db.delete(permiso)
    await db.flush()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_contratista(contratista_id: int, db: AsyncSession) -> Contratista:
    result = await db.execute(select(Contratista).where(Contratista.id == contratista_id))
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contratista no encontrado")
    return c


async def _get_trabajador(trabajador_id: int, db: AsyncSession) -> Trabajador:
    result = await db.execute(select(Trabajador).where(Trabajador.id == trabajador_id))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajador no encontrado")
    return t


def _verificar_trabajador_propio(trabajador: Trabajador) -> None:
    if trabajador.tipotrabajador_id != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los permisos solo aplican a trabajadores propios",
        )


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


async def _get_permiso(permiso_id: int, db: AsyncSession) -> Permiso:
    result = await db.execute(select(Permiso).where(Permiso.id == permiso_id))
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permiso no encontrado")
    return p


async def _get_permiso_detalle(permiso_id: int, db: AsyncSession) -> Permiso:
    result = await db.execute(
        select(Permiso)
        .options(
            selectinload(Permiso.trabajador),
            selectinload(Permiso.estado_permiso),
        )
        .where(Permiso.id == permiso_id)
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permiso no encontrado")
    return p
