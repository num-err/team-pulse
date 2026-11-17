"""In-memory stand-in for the supabase-py client, covering exactly the query
builder surface this codebase uses. Installed via
app.integrations.supabase_client.set_supabase_override (see conftest.py)."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

_DEFAULTS = {
    "workspaces": lambda: {"timezone": "UTC", "digest_hour": 9, "digest_minute": 0},
    "workspace_members": lambda: {"role": "member"},
    "workspace_integrations": lambda: {"credentials": {}, "settings": {}},
}
_HAS_ID = {"workspaces", "activity_events", "actor_aliases", "job_runs"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _Query:
    def __init__(self, db: "FakeSupabase", table: str):
        self.db, self.table_name = db, table
        self.filters: list = []
        self.op = "select"
        self.payload = None
        self.on_conflict: list[str] = []
        self.ignore_duplicates = False
        self.order_by: tuple[str, bool] | None = None
        self.limit_n: int | None = None

    # -- builders
    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows if isinstance(rows, list) else [rows]
        return self

    def upsert(self, rows, on_conflict="", ignore_duplicates=False):
        self.op, self.payload = "upsert", rows if isinstance(rows, list) else [rows]
        self.on_conflict = [c.strip() for c in on_conflict.split(",") if c.strip()]
        self.ignore_duplicates = ignore_duplicates
        return self

    def update(self, changes):
        self.op, self.payload = "update", changes
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, field, value):
        self.filters.append(lambda r: _get(r, field) == value)
        return self

    def in_(self, field, values):
        values = list(values)
        self.filters.append(lambda r: r.get(field) in values)
        return self

    def gte(self, field, value):
        self.filters.append(lambda r: str(r.get(field, "")) >= str(value))
        return self

    def is_(self, field, value):
        assert value == "null"
        self.filters.append(lambda r: r.get(field) is None)
        return self

    def order(self, field, desc=False):
        self.order_by = (field, desc)
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    # -- execution
    def _matching(self):
        return [r for r in self.db.tables.setdefault(self.table_name, []) if all(f(r) for f in self.filters)]

    def execute(self):
        if self.db.fail_tables and self.table_name in self.db.fail_tables:
            raise RuntimeError(f"simulated failure on {self.table_name}")
        rows = self.db.tables.setdefault(self.table_name, [])
        if self.op == "select":
            out = self._matching()
            if self.order_by:
                field, desc = self.order_by
                out = sorted(out, key=lambda r: str(r.get(field, "")), reverse=desc)
            if self.limit_n is not None:
                out = out[: self.limit_n]
            return SimpleNamespace(data=[dict(r) for r in out])
        if self.op == "insert":
            created = [self.db._new_row(self.table_name, r) for r in self.payload]
            rows.extend(created)
            return SimpleNamespace(data=[dict(r) for r in created])
        if self.op == "upsert":
            out = []
            for r in self.payload:
                key = tuple(r.get(c) for c in self.on_conflict)
                existing = next(
                    (x for x in rows if self.on_conflict and None not in key and tuple(x.get(c) for c in self.on_conflict) == key),
                    None,
                )
                if existing is None:
                    new = self.db._new_row(self.table_name, r)
                    rows.append(new)
                    out.append(new)
                elif not self.ignore_duplicates:
                    existing.update(r)
                    out.append(existing)
            return SimpleNamespace(data=[dict(r) for r in out])
        if self.op == "update":
            matched = self._matching()
            for r in matched:
                r.update(self.payload)
            return SimpleNamespace(data=[dict(r) for r in matched])
        if self.op == "delete":
            matched = self._matching()
            self.db.tables[self.table_name] = [r for r in rows if r not in matched]
            return SimpleNamespace(data=[dict(r) for r in matched])
        raise AssertionError(self.op)


def _get(row: dict, field: str):
    if "->>" in field:
        col, key = field.split("->>")
        value = (row.get(col) or {}).get(key)
        return None if value is None else str(value).lower() if isinstance(value, bool) else str(value)
    return row.get(field)


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self.fail_tables: set[str] = set()

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def _new_row(self, table: str, row: dict) -> dict:
        new = {**_DEFAULTS.get(table, dict)(), **row}
        if table in _HAS_ID:
            new.setdefault("id", str(uuid.uuid4()))
        new.setdefault("created_at", _now())
        if table == "activity_events":
            new.setdefault("received_at", _now())
        return new
