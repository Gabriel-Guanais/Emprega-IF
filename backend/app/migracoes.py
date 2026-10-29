"""Migrations: evolução do banco em scripts numerados.

Cada arquivo de `sql/migrations/` (001_..., 002_..., ...) roda uma única
vez, em ordem. Todas as pendentes rodam numa ÚNICA transação: se qualquer
uma falhar, nenhuma é aplicada e o banco continua exatamente como estava
(a versão anterior do sistema segue funcionando). A tabela
`schema_migrations` guarda quais já foram aplicadas.

Roda sozinho quando a API sobe (main.py). Para mudar o banco, crie o
próximo arquivo numerado; nunca edite um que já foi aplicado.
"""

import logging
from pathlib import Path

from app.db import get_pool

PASTA = Path(__file__).resolve().parent.parent / "sql" / "migrations"

# Número qualquer, fixo: impede que duas instâncias da API apliquem as
# migrations ao mesmo tempo (a segunda espera a primeira terminar).
_TRAVA = 4815162342

log = logging.getLogger("uvicorn.error")


async def aplicar_migrations() -> list[str]:
    aplicadas_agora: list[str] = []

    async with get_pool().connection() as conn:
        await conn.execute("SELECT pg_advisory_lock(%s)", (_TRAVA,))
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    versao       VARCHAR(10)  PRIMARY KEY,
                    arquivo      VARCHAR(200) NOT NULL,
                    aplicada_em  TIMESTAMPTZ  NOT NULL DEFAULT now()
                )
                """
            )
            await conn.commit()

            cur = await conn.execute("SELECT versao FROM schema_migrations")
            ja_aplicadas = {linha["versao"] for linha in await cur.fetchall()}
            await conn.commit()

            pendentes = [
                arquivo
                for arquivo in sorted(PASTA.glob("[0-9][0-9][0-9]_*.sql"))
                if arquivo.name[:3] not in ja_aplicadas
            ]
            async with conn.transaction():  # tudo ou nada
                for arquivo in pendentes:
                    await conn.execute(arquivo.read_text(encoding="utf-8"))
                    await conn.execute(
                        "INSERT INTO schema_migrations (versao, arquivo) VALUES (%s, %s)",
                        (arquivo.name[:3], arquivo.name),
                    )
                    aplicadas_agora.append(arquivo.name)
            for nome in aplicadas_agora:
                log.info("Migration aplicada: %s", nome)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(%s)", (_TRAVA,))
            await conn.commit()

    return aplicadas_agora
