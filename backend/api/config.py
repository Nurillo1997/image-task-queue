from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL ulanish manzili. Lokal ishlash uchun docker-compose'dagi
    # "postgres" xost nomi ishlatiladi, Render'da bu qiymat Render tomonidan beriladi.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/image_tasks"

    # RabbitMQ ulanish manzili (Celery broker sifatida ishlatiladi)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"

    # Yuklangan va natija fayllar saqlanadigan papka
    upload_dir: str = "/app/storage/uploads"
    result_dir: str = "/app/storage/results"

    class Config:
        env_file = ".env"


settings = Settings()
