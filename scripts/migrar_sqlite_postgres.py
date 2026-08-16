"""
Migra todos os dados do SQLite local para o PostgreSQL do Render.

ATENÇÃO:
- O PostgreSQL de destino será LIMPO antes da cópia.
- O SQLite local não é alterado.
- Execute primeiro scripts/comparar_bancos.py.
- Faça backup do SQLite e da pasta uploads antes de usar.

Uso no PowerShell, na raiz do projeto:

    $env:POSTGRES_EXTERNAL_URL="NOVA_EXTERNAL_DATABASE_URL_DO_RENDER"
    python scripts/migrar_sqlite_postgres.py

Para remover a variável depois:

    Remove-Item Env:POSTGRES_EXTERNAL_URL
"""

import os
import sys
from collections import defaultdict, deque
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_SQLITE = RAIZ_PROJETO / "instance" / "sistema_lucas.db"

URL_POSTGRES = os.getenv(
    "POSTGRES_EXTERNAL_URL",
    "",
).strip()

TABELAS_IGNORADAS = {
    "alembic_version",
}

TAMANHO_LOTE = 500


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


def criar_engines():
    if not CAMINHO_SQLITE.is_file():
        raise FileNotFoundError(
            "O banco SQLite local não foi encontrado em:\n"
            f"{CAMINHO_SQLITE}"
        )

    if not URL_POSTGRES:
        raise RuntimeError(
            "A variável POSTGRES_EXTERNAL_URL não foi definida."
        )

    sqlite_engine = create_engine(
        f"sqlite:///{CAMINHO_SQLITE}",
        future=True,
    )

    postgres_engine = create_engine(
        normalizar_url_postgres(
            URL_POSTGRES
        ),
        pool_pre_ping=True,
        future=True,
    )

    return sqlite_engine, postgres_engine


def listar_tabelas(engine):
    return {
        tabela
        for tabela in inspect(engine).get_table_names()
        if tabela not in TABELAS_IGNORADAS
    }


def validar_estrutura(
    sqlite_engine,
    postgres_engine,
):
    tabelas_sqlite = listar_tabelas(
        sqlite_engine
    )

    tabelas_postgres = listar_tabelas(
        postgres_engine
    )

    ausentes = sorted(
        tabelas_sqlite
        - tabelas_postgres
    )

    if ausentes:
        raise RuntimeError(
            "Estas tabelas existem no SQLite, mas não no PostgreSQL:\n"
            + "\n".join(
                f"- {tabela}"
                for tabela in ausentes
            )
        )

    insp_sqlite = inspect(
        sqlite_engine
    )

    insp_postgres = inspect(
        postgres_engine
    )

    erros_colunas = []

    for tabela in sorted(
        tabelas_sqlite
    ):
        colunas_sqlite = {
            coluna["name"]
            for coluna in insp_sqlite.get_columns(
                tabela
            )
        }

        colunas_postgres = {
            coluna["name"]
            for coluna in insp_postgres.get_columns(
                tabela
            )
        }

        colunas_ausentes = sorted(
            colunas_sqlite
            - colunas_postgres
        )

        if colunas_ausentes:
            erros_colunas.append(
                (
                    tabela,
                    colunas_ausentes,
                )
            )

    if erros_colunas:
        linhas = [
            "Há colunas do SQLite que não existem no PostgreSQL:"
        ]

        for tabela, colunas in erros_colunas:
            linhas.append(
                f"- {tabela}: "
                + ", ".join(colunas)
            )

        raise RuntimeError(
            "\n".join(linhas)
        )

    return sorted(
        tabelas_sqlite
    )


def ordenar_por_dependencias(
    postgres_engine,
    tabelas,
):
    tabelas_set = set(
        tabelas
    )

    inspector = inspect(
        postgres_engine
    )

    dependencias = {
        tabela: set()
        for tabela in tabelas
    }

    dependentes = defaultdict(
        set
    )

    for tabela in tabelas:
        for fk in inspector.get_foreign_keys(
            tabela
        ):
            referenciada = fk.get(
                "referred_table"
            )

            if (
                referenciada
                and referenciada in tabelas_set
                and referenciada != tabela
            ):
                dependencias[tabela].add(
                    referenciada
                )

                dependentes[referenciada].add(
                    tabela
                )

    fila = deque(
        sorted(
            tabela
            for tabela, deps
            in dependencias.items()
            if not deps
        )
    )

    ordem = []

    while fila:
        tabela = fila.popleft()
        ordem.append(
            tabela
        )

        for dependente in sorted(
            dependentes[tabela]
        ):
            dependencias[dependente].discard(
                tabela
            )

            if not dependencias[dependente]:
                fila.append(
                    dependente
                )

    if len(ordem) != len(tabelas):
        restantes = sorted(
            set(tabelas)
            - set(ordem)
        )

        raise RuntimeError(
            "Não foi possível determinar a ordem das tabelas "
            "por causa de dependências circulares:\n"
            + "\n".join(
                f"- {tabela}"
                for tabela in restantes
            )
        )

    return ordem


def contar_registros(
    engine,
    tabela,
):
    nome_seguro = tabela.replace(
        '"',
        '""',
    )

    with engine.connect() as conexao:
        return int(
            conexao.execute(
                text(
                    f'SELECT COUNT(*) '
                    f'FROM "{nome_seguro}"'
                )
            ).scalar_one()
        )


def exibir_resumo_origem(
    sqlite_engine,
    ordem,
):
    print("")
    print("=" * 72)
    print("DADOS QUE SERÃO COPIADOS DO SQLITE")
    print("=" * 72)

    total = 0

    for tabela in ordem:
        quantidade = contar_registros(
            sqlite_engine,
            tabela,
        )

        total += quantidade

        print(
            f"{tabela:<34} "
            f"{quantidade:>10} registro(s)"
        )

    print("-" * 72)
    print(
        f"{'TOTAL':<34} "
        f"{total:>10} registro(s)"
    )
    print("=" * 72)
    print("")


def confirmar_execucao():
    print(
        "ATENÇÃO: todos os registros atuais do PostgreSQL "
        "serão apagados e substituídos pela cópia do SQLite."
    )

    print(
        "O SQLite local e a pasta uploads não serão alterados."
    )

    resposta = input(
        "\nDigite MIGRAR para continuar: "
    ).strip()

    if resposta != "MIGRAR":
        print("")
        print(
            "Migração cancelada. Nenhum dado foi alterado."
        )
        print("")
        sys.exit(0)


def refletir_metadados(
    sqlite_engine,
    postgres_engine,
):
    metadata_sqlite = MetaData()
    metadata_sqlite.reflect(
        bind=sqlite_engine
    )

    metadata_postgres = MetaData()
    metadata_postgres.reflect(
        bind=postgres_engine
    )

    return (
        metadata_sqlite,
        metadata_postgres,
    )


def limpar_postgres(
    conexao,
    tabelas,
):
    nomes = ", ".join(
        f'"{tabela.replace(chr(34), chr(34) * 2)}"'
        for tabela in tabelas
    )

    if not nomes:
        return

    conexao.execute(
        text(
            f"TRUNCATE TABLE {nomes} "
            "RESTART IDENTITY CASCADE"
        )
    )


def copiar_tabela(
    conexao_sqlite,
    conexao_postgres,
    tabela_sqlite,
    tabela_postgres,
    ids_honorarios_validos,
):
    colunas_origem = [
        coluna.name
        for coluna in tabela_sqlite.columns
        if coluna.name in tabela_postgres.c
    ]

    consulta = select(
        *[
            tabela_sqlite.c[nome]
            for nome in colunas_origem
        ]
    )

    resultado = conexao_sqlite.execute(
        consulta
    )

    quantidade = 0
    ignorados = 0

    while True:
        linhas = resultado.fetchmany(
            TAMANHO_LOTE
        )

        if not linhas:
            break

        dados = []

        for linha in linhas:
            registro = {
                nome: linha._mapping[nome]
                for nome in colunas_origem
            }

            if tabela_sqlite.name == "parcelas_honorario":
                honorario_id = registro.get(
                    "honorario_id"
                )

                if (
                    honorario_id
                    and honorario_id
                    not in ids_honorarios_validos
                ):
                    ignorados += 1
                    continue

            dados.append(
                registro
            )

        if dados:
            conexao_postgres.execute(
                tabela_postgres.insert(),
                dados,
            )

            quantidade += len(
                dados
            )

    return quantidade, ignorados


def validar_resultado(
    postgres_engine,
    esperados,
):
    divergencias = []

    for tabela, esperado in esperados.items():
        destino = contar_registros(
            postgres_engine,
            tabela,
        )

        if esperado != destino:
            divergencias.append(
                (
                    tabela,
                    esperado,
                    destino,
                )
            )

    if divergencias:
        linhas = [
            "A migração terminou, mas estas contagens divergiram:"
        ]

        for tabela, esperado, destino in divergencias:
            linhas.append(
                f"- {tabela}: "
                f"esperado={esperado}, "
                f"PostgreSQL={destino}"
            )

        raise RuntimeError(
            "\n".join(linhas)
        )


def executar():
    sqlite_engine = None
    postgres_engine = None

    try:
        print("")
        print(
            "Conectando ao SQLite local..."
        )

        (
            sqlite_engine,
            postgres_engine,
        ) = criar_engines()

        print(
            "Conectando ao PostgreSQL do Render..."
        )

        with postgres_engine.connect() as conexao:
            conexao.execute(
                text("SELECT 1")
            )

        print(
            "Validando tabelas e colunas..."
        )

        tabelas = validar_estrutura(
            sqlite_engine,
            postgres_engine,
        )

        ordem = ordenar_por_dependencias(
            postgres_engine,
            tabelas,
        )

        exibir_resumo_origem(
            sqlite_engine,
            ordem,
        )

        confirmar_execucao()

        (
            metadata_sqlite,
            metadata_postgres,
        ) = refletir_metadados(
            sqlite_engine,
            postgres_engine,
        )

        print("")
        print(
            "Iniciando migração..."
        )

        esperados = {}
        total_ignorados = 0

        with sqlite_engine.connect() as origem:
            ids_honorarios_validos = {
                linha[0]
                for linha in origem.execute(
                    select(
                        metadata_sqlite
                        .tables["honorarios_caso"]
                        .c.id
                    )
                )
            }

            with postgres_engine.begin() as destino:
                print(
                    "Limpando somente o PostgreSQL..."
                )

                limpar_postgres(
                    destino,
                    list(reversed(ordem)),
                )

                for tabela in ordem:
                    quantidade, ignorados = copiar_tabela(
                        origem,
                        destino,
                        metadata_sqlite.tables[tabela],
                        metadata_postgres.tables[tabela],
                        ids_honorarios_validos,
                    )

                    esperados[tabela] = quantidade
                    total_ignorados += ignorados

                    complemento = ""

                    if ignorados:
                        complemento = (
                            f" | {ignorados} órfão(s) ignorado(s)"
                        )

                    print(
                        f"  {tabela:<32} "
                        f"{quantidade:>8} copiado(s)"
                        f"{complemento}"
                    )

        print("")
        print(
            "Validando contagens finais..."
        )

        validar_resultado(
            postgres_engine,
            esperados,
        )

        if total_ignorados:
            print("")
            print(
                f"Atenção: {total_ignorados} registro(s) órfão(s) "
                "foram ignorados porque apontavam para contratos "
                "de honorários que já não existem no SQLite."
            )

        print("")
        print("=" * 72)
        print(
            "MIGRAÇÃO CONCLUÍDA COM SUCESSO"
        )
        print("=" * 72)
        print(
            "Os dados do PostgreSQL agora correspondem "
            "ao SQLite local."
        )
        print(
            "A pasta uploads ainda precisa ser tratada separadamente."
        )
        print("=" * 72)
        print("")

    except Exception as erro:
        print("")
        print("=" * 72)
        print(
            "A MIGRAÇÃO NÃO FOI CONCLUÍDA"
        )
        print("=" * 72)
        print(str(erro))
        print("")
        print(
            "Se o erro ocorreu durante a cópia, "
            "a transação do PostgreSQL foi revertida."
        )
        print("=" * 72)
        print("")

        sys.exit(1)

    finally:
        if sqlite_engine is not None:
            sqlite_engine.dispose()

        if postgres_engine is not None:
            postgres_engine.dispose()


if __name__ == "__main__":
    executar()