from __future__ import annotations

import json
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

    def _pk_fields(self) -> list[str]:
        """Always return PK columns as a list, whether config supplied a str or list."""
        if isinstance(self._primary_key_field, list):
            return list(self._primary_key_field)
        return [self._primary_key_field]

    def _normalize_pk(self, primary_key: Any) -> dict:
        """Coerce the caller's PK arg into a {column: value} dict matching the configured PK fields."""
        fields = self._pk_fields()
        if len(fields) == 1:
            if isinstance(primary_key, dict):
                if set(primary_key.keys()) != set(fields):
                    raise ValueError(f"PK dict keys {sorted(primary_key.keys())} do not match {fields}")
                return dict(primary_key)
            return {fields[0]: primary_key}
        if not isinstance(primary_key, dict):
            raise ValueError(
                f"Composite PK requires a dict with keys {fields}, got {type(primary_key).__name__}"
            )
        missing = [f for f in fields if f not in primary_key]
        if missing:
            raise ValueError(f"Composite PK dict missing keys: {missing}")
        return {f: primary_key[f] for f in fields}

    def _pk_where(self) -> str:
        """Build the parameterized WHERE fragment for the configured PK columns."""
        return " AND ".join(f"{_quote_identifier(c)} = %s" for c in self._pk_fields())

    def retrieveByPrimaryKey(self, primary_key) -> dict:
        pk = self._normalize_pk(primary_key)
        fields = self._pk_fields()
        table = _quote_identifier(self._table_name)
        sql = f"SELECT * FROM {table} WHERE {self._pk_where()}"
        params = tuple(pk[f] for f in fields)
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
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
        fields = self._pk_fields()
        if len(fields) > 1:
            missing = [f for f in fields if f not in payload]
            if missing:
                raise ValueError(f"create payload missing composite PK columns: {missing}")
        table = _quote_identifier(self._table_name)
        cols = [_quote_identifier(k) for k in payload.keys()]
        placeholders = ", ".join(["%s"] * len(payload))
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(payload.values()))
                if len(fields) == 1:
                    pk_value = payload.get(fields[0])
                    if pk_value is None:
                        pk_value = cur.lastrowid
                    result = str(pk_value)
                else:
                    # Composite PK: return JSON of {column: value} so callers can round-trip the key.
                    result = json.dumps({f: payload[f] for f in fields}, default=str)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def updateByPrimaryKey(self, primary_key, payload: dict) -> int:
        pk = self._normalize_pk(primary_key)
        fields = self._pk_fields()
        # PK changes via update are not allowed — drop any PK column from SET if present.
        update_fields = {k: v for k, v in payload.items() if k not in fields}
        if not update_fields:
            return 0
        table = _quote_identifier(self._table_name)
        set_clause = ", ".join(f"{_quote_identifier(k)} = %s" for k in update_fields.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {self._pk_where()}"
        params = tuple(update_fields.values()) + tuple(pk[f] for f in fields)
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
        pk = self._normalize_pk(primary_key)
        fields = self._pk_fields()
        table = _quote_identifier(self._table_name)
        sql = f"DELETE FROM {table} WHERE {self._pk_where()}"
        params = tuple(pk[f] for f in fields)
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
