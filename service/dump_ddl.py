"""Dump PostgreSQL DDL from ORM metadata (for Supabase setup). Run: uv run python dump_ddl.py"""

from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSON as PG_JSON

from app.models import Base  # noqa: F401  (registers all models)

# JSON 泛型列在 PostgreSQL 上编译为 JSON；如需 JSONB 可手动替换
lines = []

for table in Base.metadata.sorted_tables:
    ddl = str(
        CreateTable(table).compile(dialect=postgresql.dialect()).statement
    ).strip()
    lines.append(f"-- ===== 表: {table.name} =====")
    lines.append(ddl.rstrip(";") + ";")
    for index in table.indexes:
        idx_ddl = str(
            CreateIndex(index).compile(dialect=postgresql.dialect()).statement
        ).strip()
        lines.append(idx_ddl + ";")
    lines.append("")

print("\n".join(lines))
