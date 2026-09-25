from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from anu_kernel.db import Base


def test_all_kernel_tables_compile_for_postgresql():
    dialect = postgresql.dialect()
    compiled = []
    for table in Base.metadata.sorted_tables:
        compiled.append(str(CreateTable(table).compile(dialect=dialect)))
    sql = "\n".join(compiled)
    assert "trust_credential" in sql
    assert "signature_record" in sql
    assert "agent_attestation" in sql
    assert "authority_grant" in sql
