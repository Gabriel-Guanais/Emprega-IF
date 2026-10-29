"""Acesso ao PostgreSQL com SQL puro (psycopg 3, pool assíncrono).

A doc cita Psycopg2 na seção 4.10; aqui usamos o psycopg 3, que é a
versão atual da mesma biblioteca e tem suporte nativo a async, o que
combina com o FastAPI.

Uso nas rotas:

    from app.db import query_all, query_one, execute

    vagas = await query_all("SELECT * FROM vagas WHERE situacao = %s", ("Ativa",))
    estudante = await query_one("SELECT * FROM estudantes WHERE id = %s", (id_,))
    novo = await execute(
        "INSERT INTO estudantes (nome) VALUES (%s) RETURNING id",
        (nome,),
        returning=True,
    )

Regra que não se quebra: valor sempre entra como parâmetro (%s), nunca
concatenado na string de SQL. É isso que protege contra SQL injection.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import settings

_pool: AsyncConnectionPool | None = None


async def abrir_pool() -> None:
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
        kwargs={"row_factory": dict_row},
        # Testa cada conexão antes de entregar para a rota. Bancos na nuvem
        # (como o Neon) "dormem" e derrubam conexões paradas; sem este
        # teste, a primeira requisição depois disso daria erro.
        check=AsyncConnectionPool.check_connection,
        # fecha conexões paradas há mais de 2 minutos
        max_idle=120,
        open=False,
    )
    await _pool.open()


async def executar_script(caminho: Path) -> None:
    """Roda um arquivo .sql inteiro (vários comandos) numa transação."""
    sql = caminho.read_text(encoding="utf-8")
    async with get_pool().connection() as conn:
        await conn.execute(sql)


async def fechar_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Pool não inicializado: verifique o lifespan em main.py.")
    return _pool


@asynccontextmanager
async def cursor():
    """Cursor dentro de uma transação: commit no fim do bloco,
    rollback se subir exceção."""
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            yield cur


@asynccontextmanager
async def transacao():
    """Várias gravações que precisam acontecer juntas (tudo ou nada).
    Ex.: a vaga e as suas listas de requisitos e benefícios."""
    async with get_pool().connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                yield cur


async def query_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    async with cursor() as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


async def query_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    async with cursor() as cur:
        await cur.execute(sql, params)
        return await cur.fetchone()


async def execute(
    sql: str, params: tuple | dict | None = None, returning: bool = False
) -> dict | int | None:
    """INSERT/UPDATE/DELETE. Com returning=True devolve a linha do
    RETURNING; sem ele, a quantidade de linhas afetadas."""
    async with cursor() as cur:
        await cur.execute(sql, params)
        if returning:
            return await cur.fetchone()
        return cur.rowcount
