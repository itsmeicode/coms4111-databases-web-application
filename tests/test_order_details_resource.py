"""Tests for OrderDetailsResource against the live classicmodels database.

Skipped automatically when MySQL is not reachable, mirroring
tests/test_customer_resource.py and tests/test_order_resource.py.
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
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"MySQL not reachable: {exc}", allow_module_level=True)

from app.resources.OrderDetailsResource import (  # noqa: E402
    OrderDetail,
    OrderDetailsCollection,
    OrderDetailsResource,
)

# 10100 is an existing order, S10_1949 is an existing product but is NOT
# currently a line item on order 10100 — so we can insert without violating FKs
# and without colliding with sample data.
TEST_ORDER_NUMBER = 10100
TEST_PRODUCT_CODE = "S10_1949"
TEST_PK_DICT = {"orderNumber": TEST_ORDER_NUMBER, "productCode": TEST_PRODUCT_CODE}


def _new_detail(**overrides) -> OrderDetail:
    base = dict(
        orderNumber=TEST_ORDER_NUMBER,
        productCode=TEST_PRODUCT_CODE,
        quantityOrdered=5,
        priceEach=100.00,
        orderLineNumber=5,
    )
    base.update(overrides)
    return OrderDetail(**base)


@pytest.fixture
def resource():
    res = OrderDetailsResource()
    res._service.deleteByPrimaryKey(TEST_PK_DICT)
    yield res
    res._service.deleteByPrimaryKey(TEST_PK_DICT)


def test_get_returns_collection(resource):
    result = resource.get({})
    assert isinstance(result, OrderDetailsCollection)
    assert len(result.items) == 2996
    assert all(isinstance(d, OrderDetail) for d in result.items)


def test_get_with_template_filters(resource):
    """Filter by a single PK column should return that order's line items only."""
    result = resource.get({"orderNumber": 10100})
    assert len(result.items) == 4
    assert all(d.orderNumber == 10100 for d in result.items)


def test_get_by_id_with_dict(resource):
    od = resource.get_by_id({"orderNumber": 10100, "productCode": "S18_1749"})
    assert od.quantityOrdered == 30
    assert float(od.priceEach) == 136.00


def test_get_by_id_with_tuple(resource):
    od = resource.get_by_id((10100, "S18_2248"))
    assert od.quantityOrdered == 50


def test_get_by_composite_id(resource):
    od = resource.get_by_composite_id(10100, "S18_4409")
    assert od.quantityOrdered == 22


def test_get_by_id_miss_raises(resource):
    with pytest.raises(ValueError, match="No order detail"):
        resource.get_by_id({"orderNumber": 99999, "productCode": "NOPE"})


def test_get_by_id_rejects_bad_shape(resource):
    with pytest.raises(ValueError, match="must be a dict"):
        resource.get_by_id("just-a-string")


def test_get_by_id_rejects_partial_dict(resource):
    with pytest.raises(ValueError, match="missing keys"):
        resource.get_by_id({"orderNumber": 10100})


def test_post_creates_and_returns_json_pk(resource):
    new_id = resource.post(_new_detail())
    parsed = json.loads(new_id)
    assert parsed == TEST_PK_DICT
    od = resource.get_by_id(TEST_PK_DICT)
    assert od.quantityOrdered == 5
    assert float(od.priceEach) == 100.00


def test_put_updates_via_composite_pk(resource):
    resource.post(_new_detail())
    n = resource.put(TEST_PK_DICT, _new_detail(quantityOrdered=99, priceEach=50.00))
    assert n == 1
    od = resource.get_by_id(TEST_PK_DICT)
    assert od.quantityOrdered == 99
    assert float(od.priceEach) == 50.00


def test_put_drops_both_pk_columns_from_body(resource):
    """Body trying to change both PK columns should be silently ignored — row stays at TEST_PK."""
    resource.post(_new_detail())
    bad_pk_body = _new_detail(orderNumber=99999, productCode="WRONG", quantityOrdered=7)
    n = resource.put(TEST_PK_DICT, bad_pk_body)
    assert n == 1
    od = resource.get_by_id(TEST_PK_DICT)
    assert od.quantityOrdered == 7
    # The bogus PK from the body must NOT have created a new row
    with pytest.raises(ValueError):
        resource.get_by_id({"orderNumber": 99999, "productCode": "WRONG"})


def test_put_missing_returns_zero(resource):
    n = resource.put(
        {"orderNumber": 99999, "productCode": "NOPE"},
        _new_detail(orderNumber=99999, productCode="NOPE"),
    )
    assert n == 0


def test_delete_removes_row(resource):
    resource.post(_new_detail())
    assert resource.delete(TEST_PK_DICT) == 1
    with pytest.raises(ValueError):
        resource.get_by_id(TEST_PK_DICT)


def test_delete_with_tuple(resource):
    resource.post(_new_detail())
    assert resource.delete((TEST_ORDER_NUMBER, TEST_PRODUCT_CODE)) == 1


def test_delete_missing_returns_zero(resource):
    assert resource.delete({"orderNumber": 99999, "productCode": "NOPE"}) == 0


def test_pydantic_rejects_missing_required_field():
    with pytest.raises(Exception):
        OrderDetail(
            orderNumber=10100,
            productCode="S10_1949",
            # quantityOrdered intentionally omitted
            priceEach=100.00,
            orderLineNumber=5,
        )
