import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def obter_database_url():
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://",
                "postgresql://",
                1,
            )

        return database_url

    return f"sqlite:///{BASE_DIR / 'instance' / 'sistema_lucas.db'}"


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "troque-esta-chave-antes-de-publicar",
    )

    SQLALCHEMY_DATABASE_URI = obter_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "uploads"

    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME = os.environ.get(
        "R2_BUCKET_NAME",
        "sistema-juridico-lucas",
    )