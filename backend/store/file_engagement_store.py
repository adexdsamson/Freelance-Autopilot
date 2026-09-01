"""FileEngagementStore: the single concrete EngagementStore implementation (D-02).

One JSON file per engagement_id under `base_dir` (default data/engagements/).
Writes are atomic (temp file + os.replace) so an interrupted write can never
leave a torn/partial JSON record (T-01-03). `_path()` only ever accepts a
`UUID` (Pydantic-validated at the model boundary) — never a raw string — so
path-traversal via a crafted engagement_id is structurally impossible
(T-01-01).
"""
import os
from pathlib import Path
from uuid import UUID

from models.engagement_record import EngagementRecord
from store.engagement_store import EngagementStore


class FileEngagementStore(EngagementStore):
    def __init__(self, base_dir: Path = Path("data/engagements")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, engagement_id: UUID) -> Path:
        if not isinstance(engagement_id, UUID):
            raise TypeError(
                f"FileEngagementStore._path() requires a UUID, got {type(engagement_id).__name__}"
            )
        return self.base_dir / f"{engagement_id}.json"

    def create(self, record: EngagementRecord) -> EngagementRecord:
        self.save(record)
        return record

    def get(self, engagement_id: UUID) -> EngagementRecord | None:
        path = self._path(engagement_id)
        if not path.exists():
            return None
        return EngagementRecord.model_validate_json(path.read_text())

    def save(self, record: EngagementRecord) -> None:
        path = self._path(record.engagement_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(record.model_dump_json(indent=2))
        os.replace(tmp_path, path)  # atomic on POSIX
