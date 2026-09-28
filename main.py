"""Ponto de entrada compatível com `uvicorn main:app`."""

from app.api.main import app
from app.infrastructure.database import Base, engine

__all__ = ["app", "Base", "engine"]
