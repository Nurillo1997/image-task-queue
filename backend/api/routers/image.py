import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Task, TaskStatus
from api.tasks import process_image, OPERATIONS
from api.config import settings

router = APIRouter(prefix="/api/v1/images", tags=["images"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    operation: str = Form(...),
    db: Session = Depends(get_db),
):
    if operation not in OPERATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Noma'lum operatsiya: {operation}. Mavjud: {list(OPERATIONS.keys())}",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Faqat JPEG yoki PNG formatdagi rasmlar qabul qilinadi",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Fayl hajmi 10MB dan oshmasligi kerak")

    task_id = uuid.uuid4()

    os.makedirs(settings.upload_dir, exist_ok=True)
    extension = os.path.splitext(file.filename)[1]
    input_path = os.path.join(settings.upload_dir, f"{task_id}{extension}")
    with open(input_path, "wb") as f:
        f.write(contents)

    task = Task(
        id=task_id,
        original_filename=file.filename,
        operation=operation,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()

    process_image.delay(str(task_id), input_path, operation)

    return {"task_id": str(task_id), "status": task.status}


@router.get("/status/{task_id}")
def get_status(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task topilmadi")

    return {
        "task_id": str(task.id),
        "status": task.status,
        "original_filename": task.original_filename,
        "operation": task.operation,
        "error_message": task.error_message,
    }


@router.get("/result/{task_id}")
def get_result(task_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task topilmadi")
    if task.status != TaskStatus.DONE:
        raise HTTPException(status_code=409, detail=f"Task hali tayyor emas: {task.status}")

    return FileResponse(task.result_path)
