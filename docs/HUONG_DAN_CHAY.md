# Hướng dẫn chạy nhanh

## Cài đặt
```bash
pip install -r requirements.txt
```

## Tạo DB
```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname \
python -m scripts.init_db
```

## Chạy API
```bash
JWT_SECRET=change-me DATABASE_URL=... \
uvicorn src.api.main:app --reload
```

## Chạy Celery worker
```bash
CELERY_BROKER_URL=redis://localhost:6379/0 \
CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
python -m celery -A src.workers.tasks worker -l info
```

## Upload chapter (admin)
- Đăng nhập `/auth/login` (user=ADMIN_USER, password khớp với ADMIN_PASSWORD_HASH).
- Gọi POST `/series/{series_id}/chapters/upload` với file ZIP (1 chapter).

## Theo dõi
- GET `/chapters/{chapter_id}/status`
- GET `/chapters/{chapter_id}/rendered-zip`
- GET `/chapters/{chapter_id}/json`

## Render lại từ JSON
```bash
python scripts/render_bubbles.py --json path/to.json --images-root path/to/images --output-dir outputs/rendered
```

