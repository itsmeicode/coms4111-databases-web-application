from __future__ import annotations

import json
import uuid
from pathlib import Path

from .AbstractBaseDataService import AbstractBaseDataService


class JSONFileDataService(AbstractBaseDataService):
    """Persists records as a JSON array in a file. Config keys: `file_path`, `primary_key_field` (default `id`)."""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._file_path = Path(str(config["file_path"]))
        self._primary_key_field = str(config.get("primary_key_field", "id"))

    def _read_all(self) -> list[dict]:
        if not self._file_path.exists():
            return []
        raw = self._file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list of objects")
        return [dict(row) for row in data if isinstance(row, dict)]

    def _write_all(self, rows: list[dict]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    @staticmethod
    def _row_matches_template(row: dict, template: dict) -> bool:
        return all(row.get(k) == v for k, v in template.items())

    def retrieveByPrimaryKey(self, primary_key: str) -> dict:
        for row in self._read_all():
            if str(row.get(self._primary_key_field)) == primary_key:
                return dict(row)
        return {}

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        return [dict(row) for row in self._read_all() if self._row_matches_template(row, template)]

    def create(self, payload: dict) -> str:
        rows = self._read_all()
        item = dict(payload)
        pk = item.get(self._primary_key_field)
        if pk is not None:
            pk = str(pk)
        else:
            pk = str(uuid.uuid4())
            item[self._primary_key_field] = pk
        if any(str(r.get(self._primary_key_field)) == pk for r in rows):
            raise ValueError("Primary key already exists")
        rows.append(item)
        self._write_all(rows)
        return pk

    def updateByPrimaryKey(self, primary_key: str, payload: dict) -> int:
        rows = self._read_all()
        for i, row in enumerate(rows):
            if str(row.get(self._primary_key_field)) == primary_key:
                updated = {**row, **payload}
                updated[self._primary_key_field] = primary_key
                rows[i] = updated
                self._write_all(rows)
                return 1
        return 0

    def deleteByPrimaryKey(self, primary_key: str) -> int:
        rows = self._read_all()
        kept: list[dict] = [r for r in rows if str(r.get(self._primary_key_field)) != primary_key]
        if len(kept) == len(rows):
            return 0
        self._write_all(kept)
        return 1
