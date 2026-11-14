from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.errors import register_error_handlers
from app.db import init_db

# Router imports
from app.routers.auth import user_router
from app.routers.fields import router as fields_router
from app.routers.seasons import router as seasons_router
from app.routers.plans import router as plans_router
from app.routers.reports import router as reports_router
from app.routers.reference import router as reference_router
from app.routers.system import router as system_router

app = FastAPI(
    title="Field Shift API",
    description="Adapting smallholder farms with NASA Earth observations and local ground truth",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS Middleware (used for local direct inspection; in production requests proxy through Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
register_error_handlers(app)

# Include API v1 routers
prefix = "/api/v1"
app.include_router(user_router, prefix=prefix)
app.include_router(fields_router, prefix=prefix)
app.include_router(seasons_router, prefix=prefix)
app.include_router(plans_router, prefix=prefix)
app.include_router(reports_router, prefix=prefix)
app.include_router(reference_router, prefix=prefix)
app.include_router(system_router, prefix=prefix)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def root():
    return {
        "project": "Field Shift: Adapting Farms with NASA Data",
        "challenge": "NASA Space Apps Challenge 2026",
        "api_docs": "/docs",
        "version": "1.0.0",
    }
