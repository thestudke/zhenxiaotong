from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from model import Base, engine
from route.chat import router as chat_router
from route.scenes import router as scenes_router
from route.sessions import router as sessions_router
from route.profile import router as profile_router
from route.appointments import router as appointments_router
from route.records import router as records_router
from route.encounters import router as encounters_router
from route.reports import router as reports_router
from route.settings import router as settings_router
from route.metrics import router as metrics_router
from route.departments import router as departments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="诊小通 Agent", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(chat_router)          # POST /api/chat（通用问诊）
app.include_router(scenes_router)        # POST /api/triage|consultation|medication
app.include_router(sessions_router)      # /api/sessions*
app.include_router(profile_router)       # /api/profile/{user_id}
app.include_router(appointments_router)  # /api/appointments*
app.include_router(records_router)       # GET /api/records
app.include_router(encounters_router)    # GET /api/encounters
app.include_router(reports_router)       # /api/reports*
app.include_router(settings_router)      # GET /api/settings
app.include_router(metrics_router)       # GET /api/metrics
app.include_router(departments_router)   # GET /api/departments


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8012)
