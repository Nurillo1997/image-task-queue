import os
import io
import uuid

from PIL import Image, ImageDraw, ImageFont

from api.worker import celery_app
from api.database import SessionLocal
from api.models import Task, TaskStatus


def _resize(img: Image.Image) -> Image.Image:
    max_size = 800
    ratio = min(max_size / img.width, max_size / img.height)
    if ratio >= 1:
        return img
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)


def _grayscale(img: Image.Image) -> Image.Image:
    return img.convert("L")


def _load_scaled_font(image_width: int) -> ImageFont.ImageFont:
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
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    text = "image-task-queue"
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
def process_image(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
        if task is None:
            return

        task.status = TaskStatus.PROCESSING
        db.commit()

        img = Image.open(io.BytesIO(task.original_image_data))
        transform = OPERATIONS[task.operation]
        result_img = transform(img)

        buffer = io.BytesIO()
        result_img.convert("RGB").save(buffer, "JPEG", quality=90)

        task.status = TaskStatus.DONE
        task.result_image_data = buffer.getvalue()
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
