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
        check=AsyncConnectionPool.check_connection,
        max_idle=120,
        open=False,
    )
    await _pool.open()


async def executar_script(caminho: Path) -> None:
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
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            yield cur


@asynccontextmanager
async def transacao():
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
    async with cursor() as cur:
        await cur.execute(sql, params)
        if returning:
            return await cur.fetchone()
        return cur.rowcount
