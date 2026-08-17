import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = "de38bb9433d41462a9c5ddacd0a8e5b0"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'sistema_lucas.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mantido para partes do sistema que ainda usam disco local
    # (ex.: modelos de documento em routes/modelos.py). Os documentos
    # de casos (routes/documentos_caso.py) já usam o Cloudflare R2,
    # configurado abaixo.
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    # Cloudflare R2 - armazenamento dos documentos dos casos.
    # As credenciais NUNCA ficam no código: são lidas de variáveis de
    # ambiente configuradas no painel do Render (Settings > Environment).
    R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME = os.environ.get(
        "R2_BUCKET_NAME",
        "sistema-juridico-lucas",
    )