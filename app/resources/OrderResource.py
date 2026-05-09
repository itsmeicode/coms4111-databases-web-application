from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class Order(BaseModel):
    """Pydantic model mirroring the classicmodels.orders table.

    Date columns map to datetime.date and are accepted as ISO-8601 strings in
    JSON (e.g. "2003-01-06"). status is a free-form string in the schema but
    in practice takes values like "Shipped" / "In Process" / "Cancelled".
    customerNumber is a foreign key into customers; the DB enforces it.
    """

    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: date | None = None
    status: str
    comments: str | None = None
    customerNumber: int


class OrderCollection(BaseModel):
    items: list[Order] = Field(default_factory=list)


class OrderResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config: dict = {
            "table_name": str(cfg.get("table_name", "orders")),
            "primary_key_field": str(cfg.get("primary_key_field", "orderNumber")),
        }
        for key in ("host", "port", "user", "password", "database"):
            if key in cfg:
                service_config[key] = cfg[key]
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderCollection(items=[Order.model_validate(r) for r in rows])

    def get_by_id(self, id) -> Order:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(int(id))
        if not row:
            raise ValueError(f"No order with orderNumber {id!r}")
        return Order.model_validate(row)

    def post(self, new_data: Order) -> str:
        return self._service.create(new_data.model_dump())

    def put(self, order_number, new_data: Order) -> int:
        data = new_data.model_dump()
        # Identity comes from the URL — drop any conflicting PK in the body.
        data.pop("orderNumber", None)
        return self._service.updateByPrimaryKey(int(order_number), data)

    def delete(self, id) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(int(id))
