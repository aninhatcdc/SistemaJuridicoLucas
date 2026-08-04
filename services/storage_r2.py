import mimetypes
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from services.storage import ArquivoStorage, ErroStorage


class StorageR2:
    def __init__(self, *, endpoint_url, access_key_id, secret_access_key, bucket_name, region="auto"):
        self.bucket_name = bucket_name
        self.cliente = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def salvar_arquivo(self, origem, chave, *, content_type=None):
        extras = {}

        if content_type:
            extras["ContentType"] = content_type

        try:
            if hasattr(origem, "read"):
                origem.seek(0)
                self.cliente.upload_fileobj(
                    origem,
                    self.bucket_name,
                    chave,
                    ExtraArgs=extras or None,
                )
                tamanho = None
            else:
                caminho = Path(origem)

                if not caminho.is_file():
                    raise ErroStorage("O arquivo de origem não foi encontrado.")

                if not content_type:
                    tipo_detectado = mimetypes.guess_type(caminho.name)[0]
                    if tipo_detectado:
                        extras["ContentType"] = tipo_detectado

                self.cliente.upload_file(
                    str(caminho),
                    self.bucket_name,
                    chave,
                    ExtraArgs=extras or None,
                )
                tamanho = caminho.stat().st_size

        except ErroStorage:
            raise
        except (BotoCoreError, ClientError, OSError) as erro:
            raise ErroStorage("Não foi possível enviar o arquivo para o armazenamento.") from erro

        return ArquivoStorage(
            chave=chave,
            nome_original=Path(chave).name,
            content_type=content_type,
            tamanho_bytes=tamanho,
        )

    def baixar_para(self, chave, destino):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.cliente.download_file(self.bucket_name, chave, str(destino))
        except (BotoCoreError, ClientError, OSError) as erro:
            destino.unlink(missing_ok=True)
            raise ErroStorage("Não foi possível baixar o arquivo do armazenamento.") from erro

        return destino

    def remover(self, chave):
        try:
            self.cliente.delete_object(Bucket=self.bucket_name, Key=chave)
        except (BotoCoreError, ClientError) as erro:
            raise ErroStorage("Não foi possível remover o arquivo do armazenamento.") from erro

    def existe(self, chave):
        try:
            self.cliente.head_object(Bucket=self.bucket_name, Key=chave)
            return True
        except ClientError as erro:
            codigo = str(erro.response.get("Error", {}).get("Code", ""))

            if codigo in {"404", "NoSuchKey", "NotFound"}:
                return False

            raise ErroStorage("Não foi possível verificar o arquivo no armazenamento.") from erro
        except BotoCoreError as erro:
            raise ErroStorage("Não foi possível verificar o arquivo no armazenamento.") from erro

    def url_temporaria(self, chave, *, nome_download=None, expira_em=300):
        parametros = {
            "Bucket": self.bucket_name,
            "Key": chave,
        }

        if nome_download:
            parametros["ResponseContentDisposition"] = (
                "attachment; "
                f"filename*=UTF-8''{quote(nome_download)}"
            )

        try:
            return self.cliente.generate_presigned_url(
                "get_object",
                Params=parametros,
                ExpiresIn=max(1, min(int(expira_em), 604800)),
            )
        except (BotoCoreError, ClientError) as erro:
            raise ErroStorage("Não foi possível gerar o link temporário.") from erro