from __future__ import annotations

import os
import re
from typing import Any

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from .AbstractBaseDataService import AbstractBaseDataService

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(name: str) -> str:
    """Backtick-quote a MySQL identifier after validating it is a safe column/table name."""
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f"`{name}`"


class MySQLDataService(AbstractBaseDataService):
    """Persists records in a MySQL table.

    Required config keys:
      - `table_name`: the table this service operates on.
      - `primary_key_field`: column name (str) for a single PK, or list[str] for composite.

    Optional config keys (override env vars MYSQL_HOST / PORT / USER / PASSWORD / DATABASE):
      - `host`, `port`, `user`, `password`, `database`.

    Connection credentials come from environment variables by design — never hard-coded.
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        if "table_name" not in config:
            raise ValueError("MySQLDataService config requires 'table_name'")
        if "primary_key_field" not in config:
            raise ValueError("MySQLDataService config requires 'primary_key_field'")

        self._table_name: str = str(config["table_name"])
        self._primary_key_field = config["primary_key_field"]

        self._conn_params: dict[str, Any] = {
            "host": config.get("host") or os.environ.get("MYSQL_HOST", "localhost"),
            "port": int(config.get("port") or os.environ.get("MYSQL_PORT", "3306")),
            "user": config.get("user") or os.environ["MYSQL_USER"],
            "password": config.get("password") or os.environ["MYSQL_PASSWORD"],
            "database": config.get("database") or os.environ["MYSQL_DATABASE"],
        }

    def _connect(self) -> Connection:
        return pymysql.connect(cursorclass=DictCursor, autocommit=False, **self._conn_params)

    def retrieveByPrimaryKey(self, primary_key) -> dict:
        if isinstance(self._primary_key_field, list):
            raise NotImplementedError("Composite primary keys: implemented in Task 1.5")
        table = _quote_identifier(self._table_name)
        pk_col = _quote_identifier(self._primary_key_field)
        sql = f"SELECT * FROM {table} WHERE {pk_col} = %s"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (primary_key,))
                row = cur.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        table = _quote_identifier(self._table_name)
        if not template:
            sql = f"SELECT * FROM {table}"
            params: tuple = ()
        else:
            cols = [_quote_identifier(k) for k in template.keys()]
            where = " AND ".join(f"{c} = %s" for c in cols)
            sql = f"SELECT * FROM {table} WHERE {where}"
            params = tuple(template.values())
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create(self, payload: dict) -> str:
        if not payload:
            raise ValueError("create requires a non-empty payload")
        if isinstance(self._primary_key_field, list):
            raise NotImplementedError("Composite primary keys: implemented in Task 1.5")
        table = _quote_identifier(self._table_name)
        cols = [_quote_identifier(k) for k in payload.keys()]
        placeholders = ", ".join(["%s"] * len(payload))
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(payload.values()))
                pk_value = payload.get(self._primary_key_field)
                if pk_value is None:
                    pk_value = cur.lastrowid
            conn.commit()
            return str(pk_value)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def updateByPrimaryKey(self, primary_key, payload: dict) -> int:
        if isinstance(self._primary_key_field, list):
            raise NotImplementedError("Composite primary keys: implemented in Task 1.5")
        # PK changes via update are not allowed — drop the PK column from SET if present.
        update_fields = {k: v for k, v in payload.items() if k != self._primary_key_field}
        if not update_fields:
            return 0
        table = _quote_identifier(self._table_name)
        pk_col = _quote_identifier(self._primary_key_field)
        set_clause = ", ".join(f"{_quote_identifier(k)} = %s" for k in update_fields.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = %s"
        params = tuple(update_fields.values()) + (primary_key,)
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rowcount = cur.rowcount
            conn.commit()
            return rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def deleteByPrimaryKey(self, primary_key) -> int:
        if isinstance(self._primary_key_field, list):
            raise NotImplementedError("Composite primary keys: implemented in Task 1.5")
        table = _quote_identifier(self._table_name)
        pk_col = _quote_identifier(self._primary_key_field)
        sql = f"DELETE FROM {table} WHERE {pk_col} = %s"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (primary_key,))
                rowcount = cur.rowcount
            conn.commit()
            return rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
