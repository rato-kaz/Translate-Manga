# Clean Code Audit (summary)

## Strengths
- Đã tách modules: utils, config, models (VLM/LLM), db, api, workers.
- Dùng logger tập trung, constants, prompt builders.
- Typing và dataclass cho config.

## Issues / Needed
- Auth stub (env-based), chưa user DB, chưa middleware audit.
- Chưa Alembic migration.
- Pipeline impl còn nhiều `print`, chưa dùng logger sâu, phụ thuộc nặng.
- Celery task giả định 1 chapter/ZIP; chưa retry/backoff; chưa presigned download.
- Tests mới tối thiểu; thiếu API/worker/pipeline tests.
- README/.env.example chưa đầy đủ.

## Next
- Thêm Alembic.
- Hoàn thiện auth + audit log middleware.
- Refactor pipeline_impl: dùng logger, giảm import khi không chạy model.
- Mở rộng worker: multi-chapter ZIP hoặc cảnh báo rõ, retry/backoff.
- Viết docs chạy (FastAPI, Celery, env).

