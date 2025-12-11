# Clean Code Improvements (planned)

- Logging: đã có `src/utils/logger.py`, cần dùng logger trong pipeline_impl.
- Constants: đã tách `src/utils/constants.py`.
- Hàm ngắn: đã tách prompt builders, VLM/LLM wrappers; cần rút gọn pipeline_impl.
- DRY: gom config/env parse, tránh lặp trong tasks.
- Error handling: thêm log và fallback cho LLM summary, pipeline runner.
- Testing: đã có tests tối thiểu (utils/models/config); cần thêm API/worker/pipeline.
- Architecture: modules tách core/api/workers/db/utils/models; cần Alembic, auth chuẩn, state store tích hợp.

