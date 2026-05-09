"""Tests for OrderResource against the live classicmodels database.

Skipped automatically when MySQL is not reachable, mirroring
tests/test_customer_resource.py.
"""
from __future__ import annotations

import os
import sys
from datetime import date
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

from app.resources.OrderResource import Order, OrderCollection, OrderResource  # noqa: E402

# Well above the highest existing orderNumber (10425), and 103 is an existing
# customer so the customerNumber FK is satisfied.
TEST_ORDER_NUMBER = 99999
TEST_CUSTOMER_NUMBER = 103


def _new_order(**overrides) -> Order:
    base = dict(
        orderNumber=TEST_ORDER_NUMBER,
        orderDate=date(2026, 1, 1),
        requiredDate=date(2026, 1, 15),
        shippedDate=None,
        status="In Process",
        comments=None,
        customerNumber=TEST_CUSTOMER_NUMBER,
    )
    base.update(overrides)
    return Order(**base)


@pytest.fixture
def resource():
    res = OrderResource()
    res._service.deleteByPrimaryKey(TEST_ORDER_NUMBER)
    yield res
    res._service.deleteByPrimaryKey(TEST_ORDER_NUMBER)


def test_get_returns_collection(resource):
    result = resource.get({})
    assert isinstance(result, OrderCollection)
    assert len(result.items) == 326
    assert all(isinstance(o, Order) for o in result.items)


def test_get_with_template_filters(resource):
    result = resource.get({"status": "Shipped"})
    assert len(result.items) > 0
    assert all(o.status == "Shipped" for o in result.items)


def test_get_by_id_hit(resource):
    order = resource.get_by_id(10100)
    assert order.customerNumber == 363
    assert order.status == "Shipped"
    # PyMySQL returns native date objects; Pydantic preserves them.
    assert order.orderDate == date(2003, 1, 6)
    assert isinstance(order.orderDate, date)


def test_get_by_id_accepts_string_id(resource):
    order = resource.get_by_id("10100")
    assert order.orderNumber == 10100


def test_get_by_id_miss_raises(resource):
    with pytest.raises(ValueError, match="No order"):
        resource.get_by_id(999999)


def test_post_creates_with_dates(resource):
    new_id = resource.post(_new_order())
    assert new_id == str(TEST_ORDER_NUMBER)
    order = resource.get_by_id(TEST_ORDER_NUMBER)
    assert order.orderDate == date(2026, 1, 1)
    assert order.requiredDate == date(2026, 1, 15)
    assert order.shippedDate is None
    assert order.status == "In Process"


def test_post_persists_optional_fields_as_null(resource):
    resource.post(_new_order(shippedDate=None, comments=None))
    order = resource.get_by_id(TEST_ORDER_NUMBER)
    assert order.shippedDate is None
    assert order.comments is None


def test_iso_string_dates_are_accepted_in_model():
    """Pydantic should parse ISO-8601 strings (the JSON wire format) into date objects."""
    order = Order(
        orderNumber=1,
        orderDate="2003-01-06",  # type: ignore[arg-type]
        requiredDate="2003-01-13",  # type: ignore[arg-type]
        shippedDate="2003-01-10",  # type: ignore[arg-type]
        status="Shipped",
        customerNumber=363,
    )
    assert order.orderDate == date(2003, 1, 6)
    assert order.shippedDate == date(2003, 1, 10)


def test_put_updates_and_ignores_pk_in_body(resource):
    resource.post(_new_order())
    updated = _new_order(
        orderNumber=5555,  # should be silently dropped
        shippedDate=date(2026, 1, 10),
        status="Shipped",
        comments="delivered",
    )
    n = resource.put(TEST_ORDER_NUMBER, updated)
    assert n == 1
    order = resource.get_by_id(TEST_ORDER_NUMBER)
    assert order.status == "Shipped"
    assert order.shippedDate == date(2026, 1, 10)
    assert order.comments == "delivered"
    with pytest.raises(ValueError):
        resource.get_by_id(5555)


def test_put_missing_returns_zero(resource):
    n = resource.put(999998, _new_order(orderNumber=999998))
    assert n == 0


def test_delete_removes_row(resource):
    resource.post(_new_order())
    assert resource.delete(TEST_ORDER_NUMBER) == 1
    with pytest.raises(ValueError):
        resource.get_by_id(TEST_ORDER_NUMBER)


def test_delete_missing_returns_zero(resource):
    assert resource.delete(999999) == 0


def test_pydantic_rejects_missing_required_field():
    with pytest.raises(Exception):
        Order(
            orderNumber=1,
            orderDate=date(2026, 1, 1),
            # requiredDate intentionally omitted
            status="In Process",
            customerNumber=103,
        )
