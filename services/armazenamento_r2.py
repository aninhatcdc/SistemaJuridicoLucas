"""
Serviço de armazenamento de arquivos usando Cloudflare R2.

O R2 é compatível com a API do Amazon S3, então usamos o boto3
apontando para o endpoint do R2 configurado nas variáveis de ambiente.

Todas as funções aqui assumem que estão sendo chamadas dentro de um
contexto de aplicação Flask (current_app disponível).
"""

from io import BytesIO

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app


class ErroArmazenamento(Exception):
    """Erro genérico ao falar com o armazenamento (R2)."""


def obter_cliente_r2():
    endpoint = current_app.config.get("R2_ENDPOINT_URL")
    access_key = current_app.config.get("R2_ACCESS_KEY_ID")
    secret_key = current_app.config.get("R2_SECRET_ACCESS_KEY")

    if not endpoint or not access_key or not secret_key:
        raise ErroArmazenamento(
            "Configuração do R2 incompleta. Verifique as variáveis de "
            "ambiente R2_ENDPOINT_URL, R2_ACCESS_KEY_ID e "
            "R2_SECRET_ACCESS_KEY."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def obter_nome_bucket():
    bucket = current_app.config.get("R2_BUCKET_NAME")

    if not bucket:
        raise ErroArmazenamento(
            "Nome do bucket do R2 não configurado (R2_BUCKET_NAME)."
        )

    return bucket


def enviar_arquivo(arquivo, chave, content_type=None):
    """
    Envia um arquivo (objeto com .read(), ex: FileStorage do Flask)
    para o R2, salvando-o com a chave (caminho) informada.
    """
    cliente = obter_cliente_r2()
    bucket = obter_nome_bucket()

    extra_args = {}

    if content_type:
        extra_args["ContentType"] = content_type

    try:
        arquivo.seek(0)

        cliente.upload_fileobj(
            arquivo,
            bucket,
            chave,
            ExtraArgs=extra_args or None,
        )

    except ClientError as erro:
        raise ErroArmazenamento(
            f"Falha ao enviar arquivo para o R2: {erro}"
        ) from erro


def baixar_arquivo_para_memoria(chave):
    """
    Baixa um objeto do R2 e devolve um BytesIO pronto para uso
    (ex: em conjunto com send_file).
    Levanta ErroArmazenamento se o arquivo não existir.
    """
    cliente = obter_cliente_r2()
    bucket = obter_nome_bucket()

    buffer = BytesIO()

    try:
        cliente.download_fileobj(bucket, chave, buffer)

    except ClientError as erro:
        codigo = erro.response.get("Error", {}).get("Code", "")

        if codigo in ("404", "NoSuchKey", "NotFound"):
            raise ErroArmazenamento(
                f"Arquivo não encontrado no R2: {chave}"
            ) from erro

        raise ErroArmazenamento(
            f"Falha ao baixar arquivo do R2: {erro}"
        ) from erro

    buffer.seek(0)

    return buffer


def arquivo_existe(chave):
    cliente = obter_cliente_r2()
    bucket = obter_nome_bucket()

    try:
        cliente.head_object(Bucket=bucket, Key=chave)
        return True

    except ClientError as erro:
        codigo = erro.response.get("Error", {}).get("Code", "")

        if codigo in ("404", "NoSuchKey", "NotFound"):
            return False

        raise ErroArmazenamento(
            f"Falha ao verificar arquivo no R2: {erro}"
        ) from erro


def excluir_arquivo(chave):
    cliente = obter_cliente_r2()
    bucket = obter_nome_bucket()

    try:
        cliente.delete_object(Bucket=bucket, Key=chave)

    except ClientError as erro:
        raise ErroArmazenamento(
            f"Falha ao excluir arquivo do R2: {erro}"
        ) from erro