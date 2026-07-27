"""Reusable platform health service — consumable by Streamlit UI and FastAPI.

Wraps the existing ``check_health()`` function from ``src.app.main`` behind a
clean service interface so any application layer can consume health data without
importing the CLI entrypoint module directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger("eakap.app.health_service")


class HealthService:
    """Thin facade over the platform health check.

    Designed to be consumed by any application layer (Streamlit, FastAPI, CLI)
    without coupling them to ``src.app.main`` directly. The underlying
    ``check_health()`` call is deferred to method bodies so the import of
    ``src.app.main`` only happens on first invocation, keeping module load times
    low.

    Example::

        hs = HealthService()
        is_ok, details = hs.run()
        statuses = hs.get_component_statuses()
    """

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """Execute all platform health checks.

        Returns:
            Tuple of (overall_healthy: bool, details: dict) where ``details``
            maps component names to their health dictionaries.
        """
        from src.app.main import check_health  # lazy import to avoid side-effects

        is_healthy, details = check_health()
        logger.debug("Health check completed. overall_healthy=%s", is_healthy)
        return is_healthy, details

    def get_component_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return raw per-component health detail dictionaries.

        Returns:
            Mapping of component name → health detail dict (as returned by
            ``check_health()``).
        """
        _, details = self.run()
        return details

    def is_healthy(self) -> bool:
        """Return ``True`` only when all platform components report healthy."""
        healthy, _ = self.run()
        return healthy

    @staticmethod
    def extract_status(component_detail: Any) -> str:
        """Safely extract the ``status`` string from a component health dict.

        Args:
            component_detail: A component health value — expected to be a dict
                with a ``"status"`` key, but handled gracefully if not.

        Returns:
            Status string (``"healthy"``, ``"unhealthy"``, or ``"unknown"``).
        """
        if isinstance(component_detail, dict):
            return str(component_detail.get("status", "unknown"))
        return "unknown"
