
from sqlalchemy import inspect, text

from app import app
from models import db


COLUNAS_NOVAS = {
    "tipo_documento": "VARCHAR(100)",
    "observacoes_uso": "TEXT",
    "versao": "VARCHAR(30) NOT NULL DEFAULT '1.0'",
    "variaveis_json": "TEXT",
}


def obter_colunas_existentes():
    inspetor = inspect(db.engine)

    return {
        coluna["name"]
        for coluna in inspetor.get_columns(
            "modelos_documentos"
        )
    }


def migrar():
    with app.app_context():
        inspetor = inspect(db.engine)

        if not inspetor.has_table(
            "modelos_documentos"
        ):
            print(
                "A tabela modelos_documentos ainda não existe."
            )
            print(
                "Execute python app.py primeiro."
            )
            return

        colunas_existentes = (
            obter_colunas_existentes()
        )

        colunas_adicionadas = []

        for nome_coluna, definicao in COLUNAS_NOVAS.items():
            if nome_coluna in colunas_existentes:
                print(
                    f"Coluna já existente: {nome_coluna}"
                )
                continue

            comando = (
                "ALTER TABLE modelos_documentos "
                f"ADD COLUMN {nome_coluna} {definicao}"
            )

            db.session.execute(
                text(comando)
            )

            colunas_adicionadas.append(
                nome_coluna
            )

            print(
                f"Coluna adicionada: {nome_coluna}"
            )

        db.session.commit()

        if colunas_adicionadas:
            print()
            print(
                "Migração concluída com sucesso."
            )
        else:
            print()
            print(
                "Nenhuma alteração foi necessária."
            )


if __name__ == "__main__":
    migrar()