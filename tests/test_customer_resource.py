"""Tests for CustomerResource against the live classicmodels database.

Skipped automatically when MySQL is not reachable, mirroring
tests/test_mysql_data_service.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

pymysql = pytest.importorskip("pymysql")

_REQUIRED_ENV = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
_missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
if _missing:
    pytest.skip(f"MySQL env vars not set: {_missing}", allow_module_level=True)

try:
    _probe = pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        connect_timeout=2,
    )
    _probe.close()
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"MySQL not reachable: {exc}", allow_module_level=True)

from app.resources.CustomerResource import Customer, CustomerCollection, CustomerResource  # noqa: E402

TEST_CUSTOMER_NUMBER = 9999


def _new_customer(**overrides) -> Customer:
    base = dict(
        customerNumber=TEST_CUSTOMER_NUMBER,
        customerName="Test Customer",
        contactLastName="Doe",
        contactFirstName="Jane",
        phone="555-0000",
        addressLine1="1 Test St",
        city="Testville",
        country="USA",
    )
    base.update(overrides)
    return Customer(**base)


@pytest.fixture
def resource():
    res = CustomerResource()
    res._service.deleteByPrimaryKey(TEST_CUSTOMER_NUMBER)
    yield res
    res._service.deleteByPrimaryKey(TEST_CUSTOMER_NUMBER)


def test_get_returns_collection(resource):
    result = resource.get({})
    assert isinstance(result, CustomerCollection)
    assert len(result.items) == 122
    assert all(isinstance(c, Customer) for c in result.items)


def test_get_with_template_filters(resource):
    result = resource.get({"country": "USA"})
    assert len(result.items) > 0
    assert all(c.country == "USA" for c in result.items)


def test_get_by_id_hit(resource):
    cust = resource.get_by_id(103)
    assert cust.customerName == "Atelier graphique"
    assert cust.country == "France"


def test_get_by_id_accepts_string_id(resource):
    cust = resource.get_by_id("103")
    assert cust.customerNumber == 103


def test_get_by_id_miss_raises(resource):
    with pytest.raises(ValueError, match="No customer"):
        resource.get_by_id(999999)


def test_post_creates_and_returns_id(resource):
    new_id = resource.post(_new_customer())
    assert new_id == str(TEST_CUSTOMER_NUMBER)
    cust = resource.get_by_id(TEST_CUSTOMER_NUMBER)
    assert cust.customerName == "Test Customer"


def test_post_persists_optional_fields_as_null(resource):
    resource.post(_new_customer(addressLine2=None, state=None, creditLimit=None))
    cust = resource.get_by_id(TEST_CUSTOMER_NUMBER)
    assert cust.addressLine2 is None
    assert cust.state is None
    assert cust.creditLimit is None


def test_put_updates_and_ignores_pk_in_body(resource):
    resource.post(_new_customer())
    updated = _new_customer(customerNumber=5555, phone="555-9999", city="NewCity")
    n = resource.put(TEST_CUSTOMER_NUMBER, updated)
    assert n == 1
    # row stays at TEST_CUSTOMER_NUMBER, body's PK is ignored
    cust = resource.get_by_id(TEST_CUSTOMER_NUMBER)
    assert cust.phone == "555-9999"
    assert cust.city == "NewCity"
    with pytest.raises(ValueError):
        resource.get_by_id(5555)


def test_put_missing_returns_zero(resource):
    n = resource.put(999998, _new_customer(customerNumber=999998))
    assert n == 0


def test_delete_removes_row(resource):
    resource.post(_new_customer())
    assert resource.delete(TEST_CUSTOMER_NUMBER) == 1
    with pytest.raises(ValueError):
        resource.get_by_id(TEST_CUSTOMER_NUMBER)


def test_delete_missing_returns_zero(resource):
    assert resource.delete(999999) == 0


def test_pydantic_rejects_missing_required_field():
    with pytest.raises(Exception):
        Customer(
            customerNumber=1,
            # customerName intentionally omitted
            contactLastName="x",
            contactFirstName="x",
            phone="x",
            addressLine1="x",
            city="x",
            country="USA",
        )
