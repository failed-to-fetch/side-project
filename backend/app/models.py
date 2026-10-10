"""Import every model here so Alembic's autogenerate sees it on Base.metadata."""

from app.features.integrations.models import ProviderConnection

__all__ = ["ProviderConnection"]
