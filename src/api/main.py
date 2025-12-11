"""
FastAPI skeleton with auth stub and upload/status/download endpoints.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from src.db.session import get_db
from src.db import models
from src.api.auth import create_access_token, require_admin, verify_admin_credentials
from src.workers.tasks import process_chapter
from src.utils.logger import logger

app = FastAPI(title="Manga Pipeline API", version="0.1.0")


# Simple audit middleware
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    user = "anonymous"
    try:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            user = "token_user"
    except Exception:
        pass
    response = await call_next(request)
    logger.info(f"[audit] {request.method} {request.url.path} user={user} status={response.status_code}")
    return response


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login", response_model=Token)
def login(body: LoginRequest):
    if not verify_admin_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=body.username, role="admin")
    return Token(access_token=token)


class UploadResponse(BaseModel):
    chapter_id: int
    status: str


@app.post("/series/{series_id}/chapters/upload", response_model=UploadResponse)
def upload_chapter(
    series_id: int,
    chapter_number: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    # Ensure series exists
    series = db.query(models.Series).filter(models.Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Basic validation: zip only, size limit
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    data = file.file.read()
    max_mb = int(os.getenv("UPLOAD_MAX_SIZE_MB", "200"))
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (>{max_mb}MB)")

    # Save uploaded zip to temp path
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"series{series_id}_ch{chapter_number}.zip"
    with temp_path.open("wb") as f:
        f.write(data)

    # Create or update chapter record
    chapter = (
        db.query(models.Chapter)
        .filter(models.Chapter.series_id == series_id, models.Chapter.number == chapter_number)
        .first()
    )
    if not chapter:
        chapter = models.Chapter(series_id=series_id, number=chapter_number, status="pending")
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
    else:
        chapter.status = "pending"
        db.commit()

    # Audit log
    audit = models.AuditLog(
        user_id=None,
        action="upload_chapter",
        series_id=series_id,
        chapter_id=chapter.id,
        detail={"filename": filename, "size": len(data)},
    )
    db.add(audit)
    db.commit()

    # Enqueue Celery job
    process_chapter.delay(series_id, chapter_number, str(temp_path), chapter.id)

    return UploadResponse(chapter_id=chapter.id, status="pending")


class StatusResponse(BaseModel):
    status: str
    json_path: Optional[str] = None
    rendered_zip_path: Optional[str] = None


@app.get("/chapters/{chapter_id}/status", response_model=StatusResponse)
def get_status(chapter_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    chapter = (
        db.query(models.Chapter)
        .join(models.Series, models.Series.id == models.Chapter.series_id)
        .filter(models.Chapter.id == chapter_id)
        .first()
    )
    if not chapter:
        raise HTTPException(status_code=404, detail="Not found")
    return StatusResponse(
        status=chapter.status,
        json_path=chapter.json_path,
        rendered_zip_path=chapter.rendered_zip_path,
    )


@app.get("/chapters/{chapter_id}/rendered-zip")
def download_zip(chapter_id: int, db=Depends(get_db), user=Depends(require_admin)):
    chapter = (
        db.query(models.Chapter)
        .join(models.Series, models.Series.id == models.Chapter.series_id)
        .filter(models.Chapter.id == chapter_id)
        .first()
    )
    if not chapter or not chapter.rendered_zip_path:
        raise HTTPException(status_code=404, detail="Not found")
    path = Path(chapter.rendered_zip_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(path, filename=path.name, media_type="application/zip")


@app.get("/chapters/{chapter_id}/json")
def get_json(chapter_id: int, db=Depends(get_db), user=Depends(require_admin)):
    chapter_json = db.query(models.ChapterJSON).filter(models.ChapterJSON.chapter_id == chapter_id).first()
    if not chapter_json:
        raise HTTPException(status_code=404, detail="Not found")
    return chapter_json.data
"""
FastAPI skeleton with auth stub and upload/status/download endpoints.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from src.db.session import get_db
from src.db import models
from src.db.models import Base
from src.api.auth import create_access_token, require_admin
from src.workers.tasks import process_chapter
from src.utils.logger import logger

app = FastAPI(title="Manga Pipeline API", version="0.1.0")

# OAuth2 stub (replace with real JWT implementation)
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login", response_model=Token)
def login(body: LoginRequest):
    # TODO: replace with real user lookup + password verify + JWT
    if body.username != "admin":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=body.username, role="admin")
    return Token(access_token=token)


class UploadResponse(BaseModel):
    chapter_id: int
    status: str


@app.post("/series/{series_id}/chapters/upload", response_model=UploadResponse)
def upload_chapter(
    series_id: int,
    chapter_number: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    # Ensure series exists
    series = db.query(models.Series).filter(models.Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Basic validation: zip only, size limit
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    data = file.file.read()
    max_mb = int(os.getenv("UPLOAD_MAX_SIZE_MB", "200"))
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (>{max_mb}MB)")

    # Save uploaded zip to temp path
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"series{series_id}_ch{chapter_number}.zip"
    with temp_path.open("wb") as f:
        f.write(data)

    # Create or update chapter record
    chapter = (
        db.query(models.Chapter)
        .filter(models.Chapter.series_id == series_id, models.Chapter.number == chapter_number)
        .first()
    )
    if not chapter:
        chapter = models.Chapter(
            series_id=series_id,
            number=chapter_number,
            status="pending",
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
    else:
        chapter.status = "pending"
        db.commit()

    # Audit log
    audit = models.AuditLog(
        user_id=None,
        action="upload_chapter",
        series_id=series_id,
        chapter_id=chapter.id,
        detail={"filename": filename, "size": len(data)},
    )
    db.add(audit)
    db.commit()

    # Enqueue Celery job
    process_chapter.delay(series_id, chapter_number, str(temp_path), chapter.id)

    return UploadResponse(chapter_id=chapter.id, status="pending")


class StatusResponse(BaseModel):
    status: str
    json_path: Optional[str] = None
    rendered_zip_path: Optional[str] = None


@app.get("/chapters/{chapter_id}/status", response_model=StatusResponse)
def get_status(chapter_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Not found")
    return StatusResponse(
        status=chapter.status,
        json_path=chapter.json_path,
        rendered_zip_path=chapter.rendered_zip_path,
    )


@app.get("/chapters/{chapter_id}/rendered-zip")
def download_zip(chapter_id: int, db=Depends(get_db), user=Depends(require_admin)):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter or not chapter.rendered_zip_path:
        raise HTTPException(status_code=404, detail="Not found")
    path = Path(chapter.rendered_zip_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(path, filename=path.name, media_type="application/zip")


@app.get("/chapters/{chapter_id}/json")
def get_json(chapter_id: int, db=Depends(get_db), user=Depends(require_admin)):
    chapter_json = db.query(models.ChapterJSON).filter(models.ChapterJSON.chapter_id == chapter_id).first()
    if not chapter_json:
        raise HTTPException(status_code=404, detail="Not found")
    return chapter_json.data

