import os
import uuid

from PIL import Image, ImageDraw, ImageFont

from api.worker import celery_app
from api.database import SessionLocal
from api.models import Task, TaskStatus
from api.config import settings


def _resize(img: Image.Image) -> Image.Image:
    """Rasmni eng katta tomoni 800px bo'lishi uchun proporsional kichraytiradi."""
    max_size = 800
    ratio = min(max_size / img.width, max_size / img.height)
    if ratio >= 1:
        return img
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)


def _grayscale(img: Image.Image) -> Image.Image:
    """Rasmni oq-qora qiladi."""
    return img.convert("L")


def _load_scaled_font(image_width: int) -> ImageFont.ImageFont:
    """
    Shrift hajmini rasm kengligiga proporsional qiladi (kengligining ~4%i),
    shunda katta rasmda katta, kichik rasmda kichikroq matn chiqadi.
    """
    font_size = max(18, int(image_width * 0.04))
    candidate_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, font_size)
    return ImageFont.load_default()


def _watermark(img: Image.Image) -> Image.Image:
    """Rasmning pastki o'ng burchagiga shaffof matnli watermark qo'shadi."""
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    text = "Nurillo's Image Processor"
    font = _load_scaled_font(img.width)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = max(12, int(img.width * 0.02))
    position = (img.width - text_w - margin, img.height - text_h - margin)

    draw.text(position, text, font=font, fill=(255, 255, 255, 200))
    return Image.alpha_composite(img, overlay).convert("RGB")


OPERATIONS = {
    "resize": _resize,
    "grayscale": _grayscale,
    "watermark": _watermark,
}


@celery_app.task(name="api.tasks.process_image")
def process_image(task_id: str, input_path: str, operation: str):
    """
    RabbitMQ navbatidan olingan asosiy task.
    1. DB'da statusni "processing" qiladi
    2. Pillow bilan tanlangan operatsiyani bajaradi
    3. Natijani diskka saqlaydi, DB'da statusni "done" qiladi
    4. Xato bo'lsa, statusni "failed" qiladi va sababini yozadi
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
        if task is None:
            return

        task.status = TaskStatus.PROCESSING
        db.commit()

        img = Image.open(input_path)
        transform = OPERATIONS[operation]
        result_img = transform(img)

        os.makedirs(settings.result_dir, exist_ok=True)
        result_filename = f"{task_id}.jpg"
        result_path = os.path.join(settings.result_dir, result_filename)
        result_img.convert("RGB").save(result_path, "JPEG", quality=90)

        task.status = TaskStatus.DONE
        task.result_path = result_path
        db.commit()

    except Exception as exc:
        task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
        if task is not None:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            db.commit()
        raise

    finally:
        db.close()
