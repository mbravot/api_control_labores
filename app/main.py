from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, empresa_campo, usuarios, maestros, actividades, rendimientos

app = FastAPI(
    title="Control de Labores API",
    description="API para gestión de labores agrícolas — AxionaTek",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"

app.include_router(auth.router, prefix=API_V1)
app.include_router(empresa_campo.router, prefix=API_V1)
app.include_router(usuarios.router, prefix=API_V1)
app.include_router(maestros.router, prefix=API_V1)
app.include_router(actividades.router, prefix=API_V1)
app.include_router(rendimientos.router, prefix=API_V1)


@app.get("/health")
async def health():
    return {"status": "ok"}
