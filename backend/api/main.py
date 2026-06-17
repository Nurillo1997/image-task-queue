from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import Base, engine
from api.routers import image

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Image Task Queue API",
    description="FastAPI + RabbitMQ + Celery + PostgreSQL orqali asinxron rasm qayta ishlash xizmati",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(image.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "image-task-queue"}
