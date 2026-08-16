"""
Migra os arquivos antigos de modelos DOCX para o Cloudflare R2
e atualiza o campo caminho_arquivo no PostgreSQL.

Este script:
- não apaga os arquivos locais;
- ignora registros que já começam com r2://;
- confirma antes de alterar o PostgreSQL;
- pode ser executado novamente sem duplicar os objetos;
- atualiza o banco apenas depois do upload ser confirmado.

Variáveis necessárias no PowerShell:

    $env:POSTGRES_EXTERNAL_URL="NOVA_EXTERNAL_DATABASE_URL_DO_RENDER"
    $env:R2_ACCESS_KEY_ID="..."
    $env:R2_SECRET_ACCESS_KEY="..."
    $env:R2_ENDPOINT_URL="https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com"
    $env:R2_BUCKET_NAME="sistema-juridico-lucas"
    $env:R2_REGION="auto"

Execução:

    python scripts/migrar_modelos_para_r2.py
"""

import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from sqlalchemy import (
    create_engine,
    text,
)


RAIZ_PROJETO = Path(
    __file__
).resolve().parents[1]

URL_POSTGRES = os.getenv(
    "POSTGRES_EXTERNAL_URL",
    "",
).strip()

R2_ACCESS_KEY_ID = os.getenv(
    "R2_ACCESS_KEY_ID",
    "",
).strip()

R2_SECRET_ACCESS_KEY = os.getenv(
    "R2_SECRET_ACCESS_KEY",
    "",
).strip()

R2_ENDPOINT_URL = os.getenv(
    "R2_ENDPOINT_URL",
    "",
).strip()

R2_BUCKET_NAME = os.getenv(
    "R2_BUCKET_NAME",
    "",
).strip()

R2_REGION = (
    os.getenv(
        "R2_REGION",
        "auto",
    ).strip()
    or "auto"
)


def normalizar_url_postgres(url):
    if url.startswith("postgres://"):
        return url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return url


def validar_variaveis():
    faltando = []

    variaveis = {
        "POSTGRES_EXTERNAL_URL": URL_POSTGRES,
        "R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
        "R2_ENDPOINT_URL": R2_ENDPOINT_URL,
        "R2_BUCKET_NAME": R2_BUCKET_NAME,
    }

    for nome, valor in variaveis.items():
        if not valor:
            faltando.append(
                nome
            )

    if faltando:
        raise RuntimeError(
            "Estas variáveis não foram definidas:\n"
            + "\n".join(
                f"- {nome}"
                for nome in faltando
            )
        )


def criar_engine_postgres():
    return create_engine(
        normalizar_url_postgres(
            URL_POSTGRES
        ),
        pool_pre_ping=True,
        future=True,
    )


def criar_cliente_r2():
    return boto3.client(
        service_name="s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=(
            R2_SECRET_ACCESS_KEY
        ),
        region_name=R2_REGION,
        config=Config(
            signature_version="s3v4",
        ),
    )


def normalizar_referencia(
    referencia,
):
    return str(
        referencia or ""
    ).replace(
        "\\",
        "/",
    ).strip()


def localizar_arquivo_local(
    referencia,
):
    referencia = normalizar_referencia(
        referencia
    )

    if referencia.startswith(
        "local://"
    ):
        referencia = referencia[
            len("local://"):
        ]

    caminho = Path(
        referencia
    )

    candidatos = []

    if caminho.is_absolute():
        candidatos.append(
            caminho
        )
    else:
        candidatos.extend(
            [
                RAIZ_PROJETO / caminho,
                RAIZ_PROJETO
                / "uploads"
                / caminho,
            ]
        )

        if referencia.startswith(
            "uploads/"
        ):
            candidatos.append(
                RAIZ_PROJETO
                / referencia[
                    len("uploads/"):
                ]
            )

    for candidato in candidatos:
        candidato = candidato.resolve()

        if candidato.is_file():
            return candidato

    return None


def montar_chave_r2(
    referencia,
    caminho_local,
):
    referencia = normalizar_referencia(
        referencia
    )

    marcador = (
        "modelos_documentos/"
    )

    if marcador in referencia:
        sufixo = referencia.split(
            marcador,
            1,
        )[1]

        return (
            marcador
            + sufixo.lstrip("/")
        )

    return (
        marcador
        + caminho_local.name
    )


def objeto_existe(
    cliente_r2,
    chave,
):
    try:
        cliente_r2.head_object(
            Bucket=R2_BUCKET_NAME,
            Key=chave,
        )

        return True

    except ClientError as erro:
        codigo = str(
            erro.response.get(
                "Error",
                {},
            ).get(
                "Code",
                "",
            )
        )

        if codigo in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return False

        raise


def enviar_arquivo(
    cliente_r2,
    caminho_local,
    chave,
):
    content_type = (
        mimetypes.guess_type(
            caminho_local.name
        )[0]
        or (
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        )
    )

    cliente_r2.upload_file(
        str(caminho_local),
        R2_BUCKET_NAME,
        chave,
        ExtraArgs={
            "ContentType": content_type,
        },
    )


def listar_modelos(
    engine,
):
    consulta = text(
        """
        SELECT
            id,
            nome,
            nome_arquivo,
            caminho_arquivo
        FROM modelos_documentos
        ORDER BY nome ASC
        """
    )

    with engine.connect() as conexao:
        return [
            dict(
                linha._mapping
            )
            for linha
            in conexao.execute(
                consulta
            )
        ]


def analisar_modelos(
    modelos,
):
    prontos = []
    pendentes = []
    ausentes = []

    for modelo in modelos:
        referencia = normalizar_referencia(
            modelo.get(
                "caminho_arquivo"
            )
        )

        if referencia.startswith(
            "r2://"
        ):
            prontos.append(
                modelo
            )
            continue

        caminho_local = (
            localizar_arquivo_local(
                referencia
            )
        )

        if not caminho_local:
            ausentes.append(
                modelo
            )
            continue

        chave = montar_chave_r2(
            referencia,
            caminho_local,
        )

        pendentes.append(
            {
                **modelo,
                "caminho_local": (
                    caminho_local
                ),
                "chave_r2": chave,
                "nova_referencia": (
                    f"r2://{chave}"
                ),
            }
        )

    return (
        prontos,
        pendentes,
        ausentes,
    )


def imprimir_relatorio(
    prontos,
    pendentes,
    ausentes,
):
    print("")
    print("=" * 78)
    print(
        "MIGRAÇÃO DOS MODELOS DOCX PARA O R2"
    )
    print("=" * 78)
    print(
        f"Já no R2:                 "
        f"{len(prontos)}"
    )
    print(
        f"Prontos para migrar:      "
        f"{len(pendentes)}"
    )
    print(
        f"Arquivo local não achado: "
        f"{len(ausentes)}"
    )
    print("-" * 78)

    if pendentes:
        print(
            "MODELOS QUE SERÃO MIGRADOS:"
        )

        for modelo in pendentes:
            print(
                f"- {modelo['nome']} "
                f"-> {modelo['chave_r2']}"
            )

    if ausentes:
        print("")
        print(
            "MODELOS SEM ARQUIVO LOCAL:"
        )

        for modelo in ausentes:
            print(
                f"- {modelo['nome']} | "
                f"{modelo['caminho_arquivo']}"
            )

    print("=" * 78)
    print("")


def confirmar():
    resposta = input(
        "Digite MIGRAR para enviar os arquivos e atualizar o PostgreSQL: "
    ).strip()

    if resposta != "MIGRAR":
        print("")
        print(
            "Operação cancelada. "
            "Nenhum dado foi alterado."
        )
        print("")

        sys.exit(0)


def atualizar_referencia(
    engine,
    modelo_id,
    nova_referencia,
):
    consulta = text(
        """
        UPDATE modelos_documentos
        SET caminho_arquivo = :caminho
        WHERE id = :modelo_id
        """
    )

    with engine.begin() as conexao:
        conexao.execute(
            consulta,
            {
                "caminho": nova_referencia,
                "modelo_id": modelo_id,
            },
        )


def executar():
    engine = None

    try:
        validar_variaveis()

        print("")
        print(
            "Conectando ao PostgreSQL..."
        )

        engine = criar_engine_postgres()

        with engine.connect() as conexao:
            conexao.execute(
                text("SELECT 1")
            )

        print(
            "Conectando ao Cloudflare R2..."
        )

        cliente_r2 = criar_cliente_r2()

        cliente_r2.head_bucket(
            Bucket=R2_BUCKET_NAME
        )

        print(
            "Lendo os modelos cadastrados..."
        )

        modelos = listar_modelos(
            engine
        )

        (
            prontos,
            pendentes,
            ausentes,
        ) = analisar_modelos(
            modelos
        )

        imprimir_relatorio(
            prontos,
            pendentes,
            ausentes,
        )

        if not pendentes:
            print(
                "Não há modelos locais prontos para migrar."
            )

            if ausentes:
                print(
                    "Confira os caminhos dos arquivos "
                    "listados como ausentes."
                )

            return

        confirmar()

        enviados = 0
        atualizados = 0

        print("")
        print(
            "Iniciando a migração..."
        )

        for modelo in pendentes:
            chave = modelo[
                "chave_r2"
            ]

            caminho_local = modelo[
                "caminho_local"
            ]

            try:
                if objeto_existe(
                    cliente_r2,
                    chave,
                ):
                    print(
                        f"- {modelo['nome']}: "
                        "objeto já existia no R2."
                    )
                else:
                    enviar_arquivo(
                        cliente_r2,
                        caminho_local,
                        chave,
                    )

                    enviados += 1

                    print(
                        f"- {modelo['nome']}: "
                        "arquivo enviado."
                    )

                if not objeto_existe(
                    cliente_r2,
                    chave,
                ):
                    raise RuntimeError(
                        "O upload não pôde ser confirmado."
                    )

                atualizar_referencia(
                    engine,
                    modelo["id"],
                    modelo[
                        "nova_referencia"
                    ],
                )

                atualizados += 1

                print(
                    "  PostgreSQL atualizado para "
                    f"{modelo['nova_referencia']}"
                )

            except (
                BotoCoreError,
                ClientError,
                OSError,
                RuntimeError,
            ) as erro:
                print(
                    f"  ERRO em {modelo['nome']}: "
                    f"{erro}"
                )

        print("")
        print("=" * 78)
        print(
            "MIGRAÇÃO FINALIZADA"
        )
        print("=" * 78)
        print(
            f"Arquivos enviados agora: "
            f"{enviados}"
        )
        print(
            f"Registros atualizados:    "
            f"{atualizados}"
        )
        print(
            f"Arquivos não encontrados: "
            f"{len(ausentes)}"
        )
        print("=" * 78)
        print("")
        print(
            "Os arquivos locais foram mantidos."
        )
        print("")

    except Exception as erro:
        print("")
        print("=" * 78)
        print(
            "NÃO FOI POSSÍVEL EXECUTAR A MIGRAÇÃO"
        )
        print("=" * 78)
        print(str(erro))
        print("=" * 78)
        print("")

        sys.exit(1)

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    executar()