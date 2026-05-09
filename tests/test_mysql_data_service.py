"""Tests for MySQLDataService against the live classicmodels database.

The whole module is skipped automatically if MySQL isn't reachable with the
current MYSQL_* env vars, so the suite stays runnable without a database
(e.g. in CI without service containers).
"""
from __future__ import annotations

import json
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
except Exception as exc:  # noqa: BLE001 — broad on purpose to skip on any reachability failure
    pytest.skip(f"MySQL not reachable: {exc}", allow_module_level=True)

from app.services.MySQLDataService import MySQLDataService  # noqa: E402

# PKs we own and clean up. High ints so they cannot collide with sample data.
TEST_CUSTOMER_NUMBER = 9999
TEST_ORDER_NUMBER = 10100  # existing order — FK-safe
TEST_PRODUCT_CODE = "S10_1949"  # existing product, not currently in this order — FK-safe


@pytest.fixture
def customer_service():
    svc = MySQLDataService({"table_name": "customers", "primary_key_field": "customerNumber"})
    svc.deleteByPrimaryKey(TEST_CUSTOMER_NUMBER)
    yield svc
    svc.deleteByPrimaryKey(TEST_CUSTOMER_NUMBER)


@pytest.fixture
def orderdetails_service():
    svc = MySQLDataService(
        {"table_name": "orderdetails", "primary_key_field": ["orderNumber", "productCode"]}
    )
    pk = {"orderNumber": TEST_ORDER_NUMBER, "productCode": TEST_PRODUCT_CODE}
    svc.deleteByPrimaryKey(pk)
    yield svc
    svc.deleteByPrimaryKey(pk)


def _new_customer_payload(**overrides) -> dict:
    base = {
        "customerNumber": TEST_CUSTOMER_NUMBER,
        "customerName": "Test Customer",
        "contactLastName": "Doe",
        "contactFirstName": "Jane",
        "phone": "555-0000",
        "addressLine1": "1 Test St",
        "city": "Testville",
        "country": "USA",
    }
    base.update(overrides)
    return base


# --- single PK: reads ---

def test_retrieve_by_primary_key_hit(customer_service):
    row = customer_service.retrieveByPrimaryKey(103)
    assert row["customerName"] == "Atelier graphique"
    assert row["country"] == "France"


def test_retrieve_by_primary_key_miss(customer_service):
    assert customer_service.retrieveByPrimaryKey(999999) == {}


def test_retrieve_by_template_empty_returns_all(customer_service):
    assert len(customer_service.retrieveByTemplate({})) == 122


def test_retrieve_by_template_filtered(customer_service):
    rows = customer_service.retrieveByTemplate({"country": "USA"})
    assert len(rows) > 0
    assert all(r["country"] == "USA" for r in rows)


def test_retrieve_by_template_multi_column(customer_service):
    rows = customer_service.retrieveByTemplate({"country": "USA", "state": "NY"})
    assert len(rows) > 0
    assert all(r["country"] == "USA" and r["state"] == "NY" for r in rows)


# --- single PK: writes ---

def test_single_pk_crud_round_trip(customer_service):
    new_id = customer_service.create(_new_customer_payload())
    assert new_id == str(TEST_CUSTOMER_NUMBER)

    assert customer_service.updateByPrimaryKey(TEST_CUSTOMER_NUMBER, {"phone": "555-9999"}) == 1
    assert customer_service.retrieveByPrimaryKey(TEST_CUSTOMER_NUMBER)["phone"] == "555-9999"

    assert customer_service.deleteByPrimaryKey(TEST_CUSTOMER_NUMBER) == 1
    assert customer_service.retrieveByPrimaryKey(TEST_CUSTOMER_NUMBER) == {}


def test_update_missing_returns_zero(customer_service):
    assert customer_service.updateByPrimaryKey(999999, {"phone": "x"}) == 0


def test_update_empty_payload_returns_zero(customer_service):
    assert customer_service.updateByPrimaryKey(103, {}) == 0


def test_update_with_pk_in_payload_drops_pk(customer_service):
    customer_service.create(_new_customer_payload())
    n = customer_service.updateByPrimaryKey(
        TEST_CUSTOMER_NUMBER, {"customerNumber": 5555, "city": "NewCity"}
    )
    assert n == 1
    assert customer_service.retrieveByPrimaryKey(TEST_CUSTOMER_NUMBER)["city"] == "NewCity"
    assert customer_service.retrieveByPrimaryKey(5555) == {}


def test_delete_missing_returns_zero(customer_service):
    assert customer_service.deleteByPrimaryKey(999999) == 0


def test_create_empty_payload_raises(customer_service):
    with pytest.raises(ValueError, match="non-empty"):
        customer_service.create({})


def test_invalid_identifier_in_template_raises(customer_service):
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        customer_service.retrieveByTemplate({"col; DROP TABLE x; --": "x"})


# --- composite PK ---

def test_composite_retrieve_existing(orderdetails_service):
    row = orderdetails_service.retrieveByPrimaryKey(
        {"orderNumber": 10100, "productCode": "S18_1749"}
    )
    assert row["quantityOrdered"] == 30


def test_composite_retrieve_miss(orderdetails_service):
    assert (
        orderdetails_service.retrieveByPrimaryKey({"orderNumber": 99999, "productCode": "NOPE"})
        == {}
    )


def test_composite_crud_round_trip(orderdetails_service):
    pk = {"orderNumber": TEST_ORDER_NUMBER, "productCode": TEST_PRODUCT_CODE}
    new_id = orderdetails_service.create(
        {**pk, "quantityOrdered": 5, "priceEach": 100.00, "orderLineNumber": 5}
    )
    assert json.loads(new_id) == pk

    assert orderdetails_service.updateByPrimaryKey(pk, {"quantityOrdered": 99}) == 1
    assert orderdetails_service.retrieveByPrimaryKey(pk)["quantityOrdered"] == 99

    assert orderdetails_service.deleteByPrimaryKey(pk) == 1
    assert orderdetails_service.retrieveByPrimaryKey(pk) == {}


def test_composite_pk_scalar_arg_rejected(orderdetails_service):
    with pytest.raises(ValueError, match="Composite PK requires a dict"):
        orderdetails_service.retrieveByPrimaryKey("just-a-string")


def test_composite_pk_partial_dict_rejected(orderdetails_service):
    with pytest.raises(ValueError, match="missing keys"):
        orderdetails_service.retrieveByPrimaryKey({"orderNumber": 10100})


def test_composite_create_missing_pk_column_rejected(orderdetails_service):
    with pytest.raises(ValueError, match="missing composite PK columns"):
        orderdetails_service.create(
            {"orderNumber": 10100, "quantityOrdered": 1, "priceEach": 1.0, "orderLineNumber": 99}
        )


# --- config validation ---

def test_missing_table_name_raises():
    with pytest.raises(ValueError, match="table_name"):
        MySQLDataService({"primary_key_field": "id"})


def test_missing_primary_key_field_raises():
    with pytest.raises(ValueError, match="primary_key_field"):
        MySQLDataService({"table_name": "customers"})
