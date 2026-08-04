import mimetypes
import shutil
from pathlib import Path
from typing import BinaryIO

from services.storage import ArquivoStorage, ErroStorage


class StorageLocal:
    def __init__(self, pasta_base: str | Path):
        self.pasta_base = Path(pasta_base).resolve()
        self.pasta_base.mkdir(parents=True, exist_ok=True)

    def _caminho(self, chave: str) -> Path:
        chave_limpa = str(chave or "").replace("\\", "/").lstrip("/")
        caminho = (self.pasta_base / chave_limpa).resolve()

        try:
            caminho.relative_to(self.pasta_base)
        except ValueError as erro:
            raise ErroStorage("A chave do arquivo é inválida.") from erro

        return caminho

    def salvar_arquivo(self, origem, chave, *, content_type=None):
        destino = self._caminho(chave)
        destino.parent.mkdir(parents=True, exist_ok=True)

        try:
            if hasattr(origem, "read"):
                origem.seek(0)
                with destino.open("wb") as arquivo_destino:
                    shutil.copyfileobj(origem, arquivo_destino)
            else:
                shutil.copy2(Path(origem), destino)
        except OSError as erro:
            raise ErroStorage("Não foi possível salvar o arquivo localmente.") from erro

        tipo = content_type or mimetypes.guess_type(destino.name)[0]

        return ArquivoStorage(
            chave=chave,
            nome_original=destino.name,
            content_type=tipo,
            tamanho_bytes=destino.stat().st_size,
        )

    def baixar_para(self, chave, destino):
        origem = self._caminho(chave)

        if not origem.is_file():
            raise ErroStorage("O arquivo solicitado não foi encontrado.")

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(origem, destino)
        except OSError as erro:
            raise ErroStorage("Não foi possível copiar o arquivo.") from erro

        return destino

    def remover(self, chave):
        caminho = self._caminho(chave)

        try:
            if caminho.is_file():
                caminho.unlink()
        except OSError as erro:
            raise ErroStorage("Não foi possível remover o arquivo.") from erro

    def existe(self, chave):
        return self._caminho(chave).is_file()

    def url_temporaria(self, chave, *, nome_download=None, expira_em=300):
        return None