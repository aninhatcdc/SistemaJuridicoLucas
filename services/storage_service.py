import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path

from flask import current_app

from services.storage import ErroStorage
from services.storage_local import StorageLocal
from services.storage_r2 import StorageR2


PREFIXO_R2 = "r2://"
PREFIXO_LOCAL = "local://"


def normalizar_chave(chave):
    chave = str(chave or "").replace("\\", "/").strip()

    if chave.startswith(PREFIXO_R2):
        return chave[len(PREFIXO_R2):]

    if chave.startswith(PREFIXO_LOCAL):
        return chave[len(PREFIXO_LOCAL):]

    return chave.lstrip("/")


def eh_referencia_r2(referencia):
    return str(referencia or "").startswith(PREFIXO_R2)


def r2_configurado():
    nomes = (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT_URL",
        "R2_BUCKET_NAME",
    )

    return all(os.getenv(nome, "").strip() for nome in nomes)


@lru_cache(maxsize=1)
def _backend_r2():
    if not r2_configurado():
        raise ErroStorage("O armazenamento R2 não está configurado.")

    return StorageR2(
        endpoint_url=os.environ["R2_ENDPOINT_URL"].strip(),
        access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
        bucket_name=os.environ["R2_BUCKET_NAME"].strip(),
        region=os.getenv("R2_REGION", "auto").strip() or "auto",
    )


def _backend_local():
    return StorageLocal(current_app.config["UPLOAD_FOLDER"])


def salvar(origem, chave, *, content_type=None):
    chave = normalizar_chave(chave)

    if r2_configurado():
        arquivo = _backend_r2().salvar_arquivo(
            origem,
            chave,
            content_type=content_type,
        )
        return PREFIXO_R2 + arquivo.chave

    arquivo = _backend_local().salvar_arquivo(
        origem,
        chave,
        content_type=content_type,
    )
    return PREFIXO_LOCAL + arquivo.chave


def baixar_para(referencia, destino):
    chave = normalizar_chave(referencia)

    if eh_referencia_r2(referencia):
        return _backend_r2().baixar_para(chave, destino)

    caminho_antigo = Path(referencia)

    if caminho_antigo.is_absolute():
        if not caminho_antigo.is_file():
            raise ErroStorage("O arquivo solicitado não foi encontrado.")

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(caminho_antigo, destino)
        return destino

    if not str(referencia).startswith(PREFIXO_LOCAL):
        candidato = Path(current_app.root_path) / referencia

        if candidato.is_file():
            destino = Path(destino)
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidato, destino)
            return destino

    return _backend_local().baixar_para(chave, destino)


def remover(referencia):
    if not referencia:
        return

    chave = normalizar_chave(referencia)

    if eh_referencia_r2(referencia):
        _backend_r2().remover(chave)
        return

    caminho_antigo = Path(referencia)

    if caminho_antigo.is_absolute():
        caminho_antigo.unlink(missing_ok=True)
        return

    if not str(referencia).startswith(PREFIXO_LOCAL):
        candidato = Path(current_app.root_path) / referencia

        if candidato.is_file():
            candidato.unlink(missing_ok=True)
            return

    _backend_local().remover(chave)


def existe(referencia):
    if not referencia:
        return False

    chave = normalizar_chave(referencia)

    if eh_referencia_r2(referencia):
        return _backend_r2().existe(chave)

    caminho_antigo = Path(referencia)

    if caminho_antigo.is_absolute():
        return caminho_antigo.is_file()

    if not str(referencia).startswith(PREFIXO_LOCAL):
        candidato = Path(current_app.root_path) / referencia

        if candidato.is_file():
            return True

    return _backend_local().existe(chave)


def url_temporaria(referencia, *, nome_download=None, expira_em=300):
    if not eh_referencia_r2(referencia):
        return None

    return _backend_r2().url_temporaria(
        normalizar_chave(referencia),
        nome_download=nome_download,
        expira_em=expira_em,
    )


def baixar_temporariamente(referencia, *, sufixo=""):
    arquivo = tempfile.NamedTemporaryFile(suffix=sufixo, delete=False)
    caminho = Path(arquivo.name)
    arquivo.close()

    try:
        baixar_para(referencia, caminho)
        return caminho
    except Exception:
        caminho.unlink(missing_ok=True)
        raise