from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.JSONFileDataService import JSONFileDataService

_DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "harry_potter_data.json"


class HarryPotterCharacter(BaseModel):
    id: str | None = None
    first_name: str = ""
    last_name: str = ""
    house_name: str = ""


class HarryPotterCollection(BaseModel):
    items: list[HarryPotterCharacter] = Field(default_factory=list)


class HarryPotterResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config: dict = {
            "file_path": str(cfg.get("file_path", _DEFAULT_DATA_PATH)),
            "primary_key_field": str(cfg.get("primary_key_field", "id")),
        }
        self._service = JSONFileDataService(service_config)

    def get(self, template: dict) -> HarryPotterCollection:
        rows = self._service.retrieveByTemplate(template)
        return HarryPotterCollection(
            items=[HarryPotterCharacter.model_validate(r) for r in rows]
        )

    def get_by_id(self, id: str) -> HarryPotterCharacter:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(str(id))
        if not row:
            raise ValueError(f"No character with id {id!r}")
        return HarryPotterCharacter.model_validate(row)

    def post(self, new_data: HarryPotterCharacter) -> str:
        data = new_data.model_dump()
        id_value = data.get("id")
        if id_value is None or str(id_value).strip() == "":
            data["id"] = str(uuid.uuid4())
        return self._service.create(data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(str(id))

    def put(self, character_id: str, new_data: HarryPotterCharacter) -> int:
        data = new_data.model_dump()
        data["id"] = character_id
        return self._service.updateByPrimaryKey(character_id, data)
