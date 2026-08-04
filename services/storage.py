from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


class ErroStorage(Exception):
    """Erro controlado durante uma operação de armazenamento."""


@dataclass(frozen=True)
class ArquivoStorage:
    chave: str
    nome_original: str
    content_type: str | None = None
    tamanho_bytes: int | None = None


class StorageBackend(Protocol):
    def salvar_arquivo(self, origem: str | Path | BinaryIO, chave: str, *, content_type: str | None = None) -> ArquivoStorage:
        ...

    def baixar_para(self, chave: str, destino: str | Path) -> Path:
        ...

    def remover(self, chave: str) -> None:
        ...

    def existe(self, chave: str) -> bool:
        ...

    def url_temporaria(self, chave: str, *, nome_download: str | None = None, expira_em: int = 300) -> str | None:
        ...