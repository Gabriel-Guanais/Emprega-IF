import os

from dotenv import load_dotenv

load_dotenv()


def _lista(valor: str) -> list[str]:
    return [item.strip() for item in valor.split(",") if item.strip()]


class Settings:
    # Banco
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/emprega_if",
    )
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", 1))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", 10))

    # Autenticação (RN-05)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chave-de-desenvolvimento-troque-em-producao")
    JWT_ALGORITMO: str = "HS256"
    JWT_EXPIRA_MINUTOS: int = int(os.getenv("JWT_EXPIRA_MINUTOS", 480))

    # Origens liberadas para o frontend React
    CORS_ORIGINS: list[str] = _lista(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    # Alternativa a CORS_ORIGINS para quando o endereço do site muda
    # (ex.: subdomínios do Render). Vazio = desligado.
    CORS_ORIGIN_REGEX: str | None = os.getenv("CORS_ORIGIN_REGEX") or None

    # Ao subir, a API aplica as migrations pendentes (sql/migrations) e,
    # se pedido, carrega os dados de exemplo. Os dois podem rodar várias
    # vezes sem duplicar nada.
    MIGRAR_AO_INICIAR: bool = os.getenv("MIGRAR_AO_INICIAR", "true").lower() == "true"
    CARREGAR_DADOS_EXEMPLO: bool = os.getenv("CARREGAR_DADOS_EXEMPLO", "").lower() == "true"

    # E-mail (Brevo, via API HTTPS). Sem a chave, nenhum e-mail é enviado.
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    EMAIL_REMETENTE: str = os.getenv("EMAIL_REMETENTE", "")
    EMAIL_REMETENTE_NOME: str = os.getenv("EMAIL_REMETENTE_NOME", "Emprega-IF")
    # Endereço do site, usado nos links dos e-mails
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:5173").rstrip("/")

    # Validação de vínculo com o IF (UC01, passo 3).
    # Vazio = aceita qualquer domínio (útil para testar).
    DOMINIOS_EMAIL_PERMITIDOS: list[str] = _lista(
        os.getenv("DOMINIOS_EMAIL_PERMITIDOS", "")
    )


settings = Settings()
