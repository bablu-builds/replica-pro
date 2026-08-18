"""Compatibility exports for the orchestration composition root.

The implementation lives in :mod:`rmao.orchestration.orchestrator`; this
module keeps the historic ``rmao.core.execute`` import path working without
maintaining a second, incomplete orchestrator implementation.
"""

from ..orchestration.orchestrator import Orchestrator, build_orchestrator

__all__ = ["Orchestrator", "build_orchestrator"]