from __future__ import annotations

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class OrderDetail(BaseModel):
    """Pydantic model mirroring the classicmodels.orderdetails table.

    Identity is the composite PK (orderNumber, productCode). All columns are
    NOT NULL in the schema, so every field is required. orderNumber FKs into
    orders and productCode FKs into products; both are enforced by MySQL.
    """

    orderNumber: int
    productCode: str
    quantityOrdered: int
    priceEach: float
    orderLineNumber: int


class OrderDetailsCollection(BaseModel):
    items: list[OrderDetail] = Field(default_factory=list)


class OrderDetailsResource(AbstractBaseResource):
    """Resource for orderdetails. Composite PK requires (orderNumber, productCode)."""

    PK_FIELDS = ("orderNumber", "productCode")

    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config: dict = {
            "table_name": str(cfg.get("table_name", "orderdetails")),
            "primary_key_field": list(cfg.get("primary_key_field", self.PK_FIELDS)),
        }
        for key in ("host", "port", "user", "password", "database"):
            if key in cfg:
                service_config[key] = cfg[key]
        self._service = MySQLDataService(service_config)

    @classmethod
    def _coerce_pk(cls, pk) -> dict:
        """Normalize the PK arg into {orderNumber: int, productCode: str}.

        Accepts either a dict (typical from routes that build it from path params)
        or a (orderNumber, productCode) tuple/list (handy in tests / scripts).
        """
        if isinstance(pk, dict):
            missing = [f for f in cls.PK_FIELDS if f not in pk]
            if missing:
                raise ValueError(f"OrderDetail PK missing keys: {missing}")
            return {"orderNumber": int(pk["orderNumber"]), "productCode": str(pk["productCode"])}
        if isinstance(pk, (tuple, list)) and len(pk) == 2:
            return {"orderNumber": int(pk[0]), "productCode": str(pk[1])}
        raise ValueError(
            f"OrderDetail PK must be a dict with keys {list(cls.PK_FIELDS)} or a (orderNumber, productCode) "
            f"tuple, got {type(pk).__name__}"
        )

    def get(self, template: dict) -> OrderDetailsCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderDetailsCollection(items=[OrderDetail.model_validate(r) for r in rows])

    def get_by_id(self, id) -> OrderDetail:  # noqa: A002
        pk = self._coerce_pk(id)
        row = self._service.retrieveByPrimaryKey(pk)
        if not row:
            raise ValueError(f"No order detail with {pk}")
        return OrderDetail.model_validate(row)

    def get_by_composite_id(self, order_number, product_code) -> OrderDetail:
        """Convenience accessor mirroring how route handlers receive the parts separately."""
        return self.get_by_id({"orderNumber": order_number, "productCode": product_code})

    def post(self, new_data: OrderDetail) -> str:
        return self._service.create(new_data.model_dump())

    def put(self, pk, new_data: OrderDetail) -> int:
        pk_dict = self._coerce_pk(pk)
        data = new_data.model_dump()
        # Identity comes from the URL — drop both PK columns from the body.
        for f in self.PK_FIELDS:
            data.pop(f, None)
        return self._service.updateByPrimaryKey(pk_dict, data)

    def delete(self, id) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(self._coerce_pk(id))
