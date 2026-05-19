from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.web.fastapi_app import app  # noqa: E402

__all__ = ["app"]
