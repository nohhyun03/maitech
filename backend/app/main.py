from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import action_records, anomalies, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MAITECH API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(anomalies.router)
app.include_router(action_records.router)
