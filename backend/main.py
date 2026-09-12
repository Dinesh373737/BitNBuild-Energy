"""
GridMind — FastAPI Application Entry Point
=============================================
Minimal app setup. Registers all module routers when they're built.
For now, provides /api/health, /api/status, and initializes the DB.

Run:  uvicorn backend.main:app --reload --port 8000
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.config import settings
from backend.common.feature_flags import flags
from backend.common.api_registry import api_registry
from backend.common.init_db import initialize_database
from backend.common.logger import logger
from backend.common.schemas.base import HealthResponse, StatusResponse

# ── Track uptime ──────────────────────────────────────────────────────
_start_time = time.time()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    # STARTUP
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Mode: {settings.APP_MODE} | DB: {settings.DATABASE_MODE}")
    logger.info("=" * 60)

    initialize_database()

    logger.info(f"Enabled agents: {flags.get_enabled_agents()}")
    logger.info(f"Server starting on {settings.HOST}:{settings.PORT}")

    yield

    # SHUTDOWN
    logger.info("GridMind shutting down...")


# ── Create FastAPI App ────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Multi-Agent AI for Resilient Microgrid Coordination",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
#  CORE ROUTES (always available)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        uptime_seconds=round(time.time() - _start_time, 2),
        database="connected",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/api/status", response_model=StatusResponse, tags=["System"])
def system_status():
    """Full system status including feature flags and API registry."""
    return StatusResponse(
        health=HealthResponse(
            status="healthy",
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            uptime_seconds=round(time.time() - _start_time, 2),
            database="connected",
            timestamp=datetime.now(timezone.utc),
        ),
        feature_flags=flags.get_status_summary(),
        apis=api_registry.list_all(),
        enabled_agents=flags.get_enabled_agents(),
        enabled_forecasts=flags.get_enabled_forecasts(),
    )


# ══════════════════════════════════════════════════════════════════════
#  MODULE ROUTER REGISTRATION
#  ─────────────────────────────────────────────────────────────────────
#  As modules are built, register their routers here:
#
#  from backend.modules.data_connectors.router import router as data_router
#  app.include_router(data_router, prefix="/api", tags=["Data"])
#
#  from backend.modules.ml_forecasting.router import router as forecast_router
#  app.include_router(forecast_router, prefix="/api", tags=["Forecasting"])
#
#  from backend.modules.simulation.router import router as sim_router
#  app.include_router(sim_router, prefix="/api", tags=["Simulation"])
#
#  ... etc for each module
# ══════════════════════════════════════════════════════════════════════

# ── Module 6: Agents ─────────────────────────────────────────────────
from backend.modules.agents.router import router as agents_router
from backend.modules.safety.router import router as safety_router

app.include_router(agents_router, prefix="/api", tags=["Agents"])
app.include_router(safety_router, prefix="/api", tags=["Safety"])
