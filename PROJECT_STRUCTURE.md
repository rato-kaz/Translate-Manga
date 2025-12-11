# Project Structure (khôi phục)

- `src/`
  - `api/` (FastAPI endpoints, auth)
  - `core/` (pipeline runner, pipeline impl)
  - `models/` (VLM/LLM wrappers, prompts)
  - `utils/` (logger, constants, image/lang utils)
  - `db/` (SQLAlchemy models, session, state sqlite)
  - `workers/` (Celery tasks)
  - `config/` (config dataclasses)
- `scripts/` (render_bubbles, init_db, db_state_cli)
- `tests/` (unit tests utils/models/config)
- `output/`, `uploads/` (runtime output)
- `requirements.txt`
- `ENV_CONFIG_GUIDE.md`, `HUONG_DAN_CHAY.md`, `CLEAN_CODE_*`

