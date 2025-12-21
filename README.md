## Manga Translation & Rendering Pipeline

Dự án này là một pipeline xử lý manga end‑to‑end:

- **Phát hiện panel + bubble, OCR, detect ngôn ngữ**
- **Caption panel bằng VLM**
- **Dịch hội thoại bằng LLM (context‑aware)**
- **Sinh JSON cấu trúc để lưu DB (PostgreSQL)**
- **Render text dịch ngược vào bubble (Pillow)**
- **Expose qua FastAPI + Celery + Redis cho xử lý async**

Kiến trúc code đã được tách tương đối sạch theo kiểu *layers* trong thư mục `src/` và có thêm tài liệu chi tiết trong thư mục `docs/`.

---

## 1. Cấu trúc thư mục chính

- **`src/`**: Mã nguồn chính
  - **`src/api/`**: FastAPI app
    - `main.py`: Khởi tạo FastAPI, endpoints upload/status/download, middleware audit đơn giản.
    - `auth.py`: Đăng nhập admin (dựa trên env), tạo/verify JWT.
  - **`src/core/`**
    - `pipeline_runner.py`: Wrapper gọi pipeline sinh JSON (hiện đang dùng script `notebooks/pipeline_generate_json.py` hoặc sẽ gọi `pipeline_impl` sau này).
  - **`src/models/`**
    - `vlm.py`: Wrapper gọi VLM (caption panel, mô tả cảnh).
    - `llm.py`: Wrapper gọi LLM (dịch text có context).
    - `prompts.py`: Hàm build prompt system/user cho VLM/LLM, `clean_translation`, v.v.
  - **`src/utils/`**
    - `logger.py`: Cấu hình logger dùng chung (thay cho `print()`).
    - `constants.py`: Các hằng số chung (ngôn ngữ, default, magic numbers…).
    - `image_processing.py`: Helper xử lý image.
    - `language_detection.py`: Wrapper detect ngôn ngữ (fast‑langdetect).
  - **`src/db/`**
    - `session.py`: Tạo SQLAlchemy engine + session (PostgreSQL).
    - `models.py`: ORM models `User`, `Series`, `Chapter`, `ChapterJSON`, `ChapterSummary`, `AuditLog`.
    - `state.py`: SQLite state DB cho tracking job (CLI tools).
  - **`src/workers/`**
    - `tasks.py`: Celery task `process_chapter` – unzip, chạy pipeline, lưu JSON/summary, render, zip kết quả, cập nhật DB.
  - **`src/config/`**
    - `config.py`: Dataclass `VLMConfig`, `LLMConfig`, `Config` để load config từ env.
- **`scripts/`**
  - `render_bubbles.py`: Đọc JSON, vẽ text dịch vào bubble (auto fit, font, padding).
  - `init_db.py`: Khởi tạo schema DB từ `src.db.models`.
  - `db_state_cli.py`: CLI xem/đổi trạng thái chapter trong SQLite state DB.
- **`notebooks/`**
  - `pipeline_generate_json.py`: Script pipeline gốc (panel detect + OCR + VLM + LLM + JSON). Đang là “implementation hiện tại” được gọi từ Celery/pipeline_runner.
  - Một số script test model/detection/benchmark khác (`test_model_det.py`, `text_classification.py`, …).
- **`docs/`**
  - `ENV_CONFIG_GUIDE.md`: Giải thích chi tiết các biến môi trường.
  - `HUONG_DAN_CHAY.md`: Hướng dẫn chạy, flow pipeline.
  - `PROJECT_STRUCTURE.md`: Diễn giải kiến trúc & layout file.
  - `MAGIV2_PARAMETERS_GUIDE.md`: Tham số model detection.
  - `CLEAN_CODE_AUDIT.md`, `CLEAN_CODE_IMPROVEMENTS.md`: Ghi chú code review & kế hoạch refactor.
- **`tests/`**
  - `test_utils.py`, `test_models.py`, `test_config.py`: Unit test cơ bản cho utils/models/config.

---

## 2. Yêu cầu môi trường & cài đặt

- **Python**: khuyến nghị 3.10+
- **PostgreSQL**: cho DB chính (metadata, JSON, summary).
- **Redis**: cho Celery broker/backend.
- **Pip packages**: cài qua `requirements.txt`.

### 2.1. Tạo virtualenv và cài dependency

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

Phiên bản `openai` đã được pin trong `requirements.txt` để đồng bộ với usage trong code (`openai==1.35.3`).

---

## 3. Cấu hình môi trường (`.env`)

Toàn bộ config đọc từ biến môi trường (xem chi tiết thêm ở `docs/ENV_CONFIG_GUIDE.md`). Gợi ý `.env` tối thiểu:

```bash
# DB
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/manga_db

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Admin auth (FastAPI)
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=...bcrypt-hash...
JWT_SECRET=change-me
JWT_ALGORITHM=HS256

# VLM (OpenAI-compatible)
OPENAI_BASE_URL=
OPENAI_API_KEY=
OPENAI_MODEL=

# LLM (translation)
LLM_API_BASE=
LLM_API_KEY=
LLM_MODEL_NAME=

# Pipeline flags
PIPELINE_DEVICE=cuda
PIPELINE_USE_VLM=true
PIPELINE_USE_LLM_TRANSLATE=true
PIPELINE_TARGET_LANG=en
PIPELINE_USE_SUMMARY_LLM=true
```

> **Lưu ý**: Không commit file `.env` thật vào git. Với môi trường production/dev khác nhau hãy tạo `.env.dev`, `.env.prod` riêng và load tương ứng.

---

## 4. Khởi tạo database (PostgreSQL)

Bạn có 2 lựa chọn:

- **Dùng Alembic migration** (khuyến nghị):

```bash
alembic upgrade head
```

- **Hoặc dùng script init_db**:

```bash
python scripts/init_db.py
```

Đảm bảo `DATABASE_URL` trong env trỏ đúng tới PostgreSQL instance.

---

## 5. Chạy API + Celery worker

### 5.1. Chạy FastAPI

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.2. Chạy Celery worker

```bash
celery -A src.workers.tasks.celery_app worker -l info
```

Celery sẽ nhận job `process_chapter` từ API upload.

---

## 6. Flow xử lý chương manga

1. **Admin login**:
   - Gửi POST `/auth/login` với `username` và `password`.
   - Nhận về JWT token, dùng `Authorization: Bearer <token>`.
2. **Upload chương**:
   - Endpoint: `POST /series/{series_id}/chapters/upload`
   - Upload 1 file ZIP cho **mỗi chương** (nếu nhiều chương trong 1 ZIP, cần tách ra các ZIP riêng hoặc tổ chức subfolder – xem thêm trong tài liệu).
   - API lưu file tạm, tạo record `Chapter`, enqueue Celery task `process_chapter`.
3. **Theo dõi trạng thái**:
   - `GET /chapters/{chapter_id}/status`
   - Trả về trạng thái `pending/processing/done/failed` + đường dẫn JSON nếu đã có.
4. **Tải kết quả render**:
   - `GET /chapters/{chapter_id}/rendered-zip`
   - Trả về ZIP ảnh đã được vẽ text dịch vào bubble.
5. **Lấy full JSON**:
   - `GET /chapters/{chapter_id}/json`
   - Trả về JSON từ bảng `ChapterJSON` (dùng cho debug, analytics hoặc training thêm).

---

## 7. Pipeline chi tiết (tầng core/models/utils)

- **Detection & OCR**:
  - Script chính hiện tại: `notebooks/pipeline_generate_json.py` (sẽ dần được port sạch vào `src/core/pipeline_impl.py`).
  - Dùng model detection + OCR (MAGI V2 / YOLO + OCR in-house) để tìm panel, bubble, text.
- **VLM caption**:
  - `src/models/vlm.py` + `src/models/prompts.py` build prompt và gọi VLM thông qua OpenAI‑compatible API.
  - Input: ảnh panel + hướng dẫn; Output: mô tả cảnh/ngữ cảnh dùng cho LLM translate.
- **LLM translation**:
  - `src/models/llm.py`:
    - Đọc context (character, caption, chapter/page/panel/bubble, text gốc, language).
    - Build prompt chi tiết để LLM dịch chuẩn ngữ điệu, bối cảnh.
    - `clean_translation()` xử lý response, lấy phần dịch “sạch”.
- **Render kết quả**:
  - `scripts/render_bubbles.py`:
    - Đọc JSON + ảnh gốc.
    - Với từng bubble: tô nền trắng trong bbox, auto‑fit text dịch, vẽ lại text (multi‑line, padding, line spacing).
    - Xuất ảnh mới (dùng trong ZIP kết quả).

---

## 8. Test & kiểm tra nhanh

Chạy toàn bộ test:

```bash
pytest -q
```

Một số test tập trung vào:

- Độ sạch của prompt builder + `clean_translation`.
- Config loading từ env (`src.config.config`).
- Utility functions (constants, image utils cơ bản).

---

## 9. Ghi chú roadmap / việc còn dang dở

- Port hoàn chỉnh pipeline từ `notebooks/pipeline_generate_json.py` vào `src/core/pipeline_impl.py`, dùng full `logger`, bỏ `print`.
- Thêm retry/backoff cho Celery worker, presigned URL (hoặc token-based) cho download ZIP.
- Bổ sung tests cho API, Celery task, pipeline runner.
- Nâng cấp auth/permission:
  - User thật trong DB, phân quyền series theo user.
  - Kiểm tra quyền khi xem status/download JSON/ZIP.
- Thêm Alembic migrations tiếp theo nếu schema thay đổi.


