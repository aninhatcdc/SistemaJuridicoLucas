import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_SQLITE = RAIZ_PROJETO / "instance" / "sistema_lucas.db"
URL_POSTGRES = os.getenv("POSTGRES_EXTERNAL_URL", "").strip()
TABELAS_IGNORADAS = {"alembic_version"}


def normalizar_url_postgres(url):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def criar_engine_sqlite():
    if not CAMINHO_SQLITE.is_file():
        raise FileNotFoundError(
            f"Banco SQLite não encontrado em: {CAMINHO_SQLITE}"
        )

    return create_engine(
        f"sqlite:///{CAMINHO_SQLITE}",
        future=True,
    )


def criar_engine_postgres():
    if not URL_POSTGRES:
        raise RuntimeError(
            "Defina POSTGRES_EXTERNAL_URL com a External Database URL do Render."
        )

    return create_engine(
        normalizar_url_postgres(URL_POSTGRES),
        pool_pre_ping=True,
        future=True,
    )


def listar_tabelas(engine):
    return sorted(
        tabela
        for tabela in inspect(engine).get_table_names()
        if tabela not in TABELAS_IGNORADAS
    )


def contar_registros(engine, tabela):
    nome_seguro = tabela.replace('"', '""')

    with engine.connect() as conexao:
        return int(
            conexao.execute(
                text(f'SELECT COUNT(*) FROM "{nome_seguro}"')
            ).scalar_one()
        )


def coletar_contagens(engine):
    resultado = {}

    for tabela in listar_tabelas(engine):
        try:
            resultado[tabela] = contar_registros(engine, tabela)
        except Exception as erro:
            resultado[tabela] = f"ERRO: {erro.__class__.__name__}"

    return resultado


def imprimir_relatorio(sqlite, postgres):
    tabelas = sorted(set(sqlite) | set(postgres))
    largura = max([len("Tabela")] + [len(t) for t in tabelas])

    cabecalho = (
        f"{'Tabela':<{largura}}  "
        f"{'SQLite':>10}  "
        f"{'PostgreSQL':>12}  "
        f"{'Diferença':>10}  Situação"
    )

    print()
    print("=" * len(cabecalho))
    print("COMPARAÇÃO DE BANCOS — SOMENTE LEITURA")
    print("=" * len(cabecalho))
    print(cabecalho)
    print("-" * len(cabecalho))

    for tabela in tabelas:
        valor_sqlite = sqlite.get(tabela)
        valor_postgres = postgres.get(tabela)

        diferenca = "-"
        situacao = ""

        if isinstance(valor_sqlite, int) and isinstance(valor_postgres, int):
            diferenca = str(valor_sqlite - valor_postgres)

            if valor_sqlite == valor_postgres:
                situacao = "IGUAL"
            elif valor_sqlite > valor_postgres:
                situacao = "FALTAM NO POSTGRES"
            else:
                situacao = "POSTGRES TEM A MAIS"
        elif tabela not in sqlite:
            situacao = "SÓ NO POSTGRES"
        elif tabela not in postgres:
            situacao = "SÓ NO SQLITE"
        else:
            situacao = "VERIFICAR ERRO"

        print(
            f"{tabela:<{largura}}  "
            f"{str(valor_sqlite if valor_sqlite is not None else '-'):>10}  "
            f"{str(valor_postgres if valor_postgres is not None else '-'):>12}  "
            f"{diferenca:>10}  "
            f"{situacao}"
        )

    print("=" * len(cabecalho))
    print("Nenhum dado foi alterado.")
    print()


def executar():
    sqlite_engine = None
    postgres_engine = None

    try:
        print("Conectando ao SQLite local...")
        sqlite_engine = criar_engine_sqlite()

        print("Conectando ao PostgreSQL do Render...")
        postgres_engine = criar_engine_postgres()

        print("Lendo tabelas e contagens...")
        sqlite = coletar_contagens(sqlite_engine)
        postgres = coletar_contagens(postgres_engine)

        imprimir_relatorio(sqlite, postgres)

    except Exception as erro:
        print()
        print("Não foi possível comparar os bancos:")
        print(erro)
        sys.exit(1)

    finally:
        if sqlite_engine is not None:
            sqlite_engine.dispose()

        if postgres_engine is not None:
            postgres_engine.dispose()


if __name__ == "__main__":
    executar()