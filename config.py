import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def obter_database_url():
    database_url = os.getenv(
        "DATABASE_URL",
        "",
    ).strip()

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://",
                "postgresql://",
                1,
            )

        return database_url

    return (
        "sqlite:///"
        f"{BASE_DIR / 'instance' / 'sistema_lucas.db'}"
    )


class Config:
    SQLALCHEMY_DATABASE_URI = obter_database_url()