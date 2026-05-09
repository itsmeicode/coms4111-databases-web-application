from __future__ import annotations

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class Customer(BaseModel):
    """Pydantic model mirroring the classicmodels.customers table.

    NOT NULL columns are required; nullable columns default to None so they
    can be omitted from POST/PUT bodies. customerNumber is required because
    classicmodels.customers does not auto-increment its primary key.
    """

    customerNumber: int
    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: str | None = None
    city: str
    state: str | None = None
    postalCode: str | None = None
    country: str
    salesRepEmployeeNumber: int | None = None
    creditLimit: float | None = None


class CustomerCollection(BaseModel):
    items: list[Customer] = Field(default_factory=list)


class CustomerResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config: dict = {
            "table_name": str(cfg.get("table_name", "customers")),
            "primary_key_field": str(cfg.get("primary_key_field", "customerNumber")),
        }
        # Allow optional connection overrides; otherwise the service reads MYSQL_* env vars.
        for key in ("host", "port", "user", "password", "database"):
            if key in cfg:
                service_config[key] = cfg[key]
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> CustomerCollection:
        rows = self._service.retrieveByTemplate(template)
        return CustomerCollection(items=[Customer.model_validate(r) for r in rows])

    def get_by_id(self, id) -> Customer:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(int(id))
        if not row:
            raise ValueError(f"No customer with customerNumber {id!r}")
        return Customer.model_validate(row)

    def post(self, new_data: Customer) -> str:
        return self._service.create(new_data.model_dump())

    def put(self, customer_number, new_data: Customer) -> int:
        data = new_data.model_dump()
        # Identity comes from the URL — drop any conflicting PK in the body.
        data.pop("customerNumber", None)
        return self._service.updateByPrimaryKey(int(customer_number), data)

    def delete(self, id) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(int(id))
