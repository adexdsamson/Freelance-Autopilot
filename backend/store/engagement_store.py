"""Abstract EngagementStore interface (D-01/D-02).

This is the ONLY persistence seam for Engagement Records. Exactly one
concrete implementation exists in this phase (FileEngagementStore); later
phases (e.g. Phase 8 AgentCore Memory) add a new concrete class here without
touching callers, because every caller depends on this interface, not on a
specific backend.
"""
from abc import ABC, abstractmethod
from uuid import UUID

from models.engagement_record import EngagementRecord


class EngagementStore(ABC):
    @abstractmethod
    def create(self, record: EngagementRecord) -> EngagementRecord:
        """Persist a brand-new EngagementRecord and return it."""
        raise NotImplementedError

    @abstractmethod
    def get(self, engagement_id: UUID) -> EngagementRecord | None:
        """Load an EngagementRecord by id, or None if it does not exist."""
        raise NotImplementedError

    @abstractmethod
    def save(self, record: EngagementRecord) -> None:
        """Persist an updated EngagementRecord (overwrite)."""
        raise NotImplementedError
