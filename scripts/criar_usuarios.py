"""
Cria ou atualiza os dois usuários fixos do sistema.

Uso:
    python scripts/criar_usuarios.py

O script é idempotente:
- não duplica usuários;
- atualiza nome, telefone, cargo, perfil e status;
- redefine a senha informada;
- mantém os usuários ativos.
"""

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from app import create_app
from models import db
from models.usuario import Usuario


USUARIOS = [
    {
        "nome": "Lucas José Tavares Carneiro da Cunha",
        "email": "lucastavaresadvocacia@gmail.com",
        "telefone": "83999452488",
        "cargo": "Advogado",
        "perfil": Usuario.PERFIL_ADMIN,
        "senha": "Lucas280914@",
    },
    {
        "nome": "Ronaldy Regis Galberto da Silva",
        "email": "ronaldyjuridico@gmail.com",
        "telefone": "83986349978",
        "cargo": "Estagiário",
        "perfil": Usuario.PERFIL_ADMIN,
        "senha": "Ronaldy*2026",
    },
]


def criar_ou_atualizar_usuario(dados):
    email = dados["email"].strip().lower()

    usuario = Usuario.query.filter_by(
        email=email,
    ).first()

    criado = False

    if not usuario:
        usuario = Usuario(
            email=email,
        )
        db.session.add(usuario)
        criado = True

    usuario.nome = dados["nome"].strip()
    usuario.telefone = dados["telefone"].strip()
    usuario.cargo = dados["cargo"].strip()
    usuario.perfil = dados["perfil"]
    usuario.ativo = True

    usuario.definir_senha(
        dados["senha"],
    )

    return usuario, criado


def executar():
    app = create_app()

    with app.app_context():
        resultados = []

        try:
            for dados in USUARIOS:
                usuario, criado = (
                    criar_ou_atualizar_usuario(
                        dados
                    )
                )

                resultados.append(
                    (
                        usuario.nome,
                        usuario.email,
                        "criado" if criado else "atualizado",
                    )
                )

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        print("")
        print("=" * 65)
        print("USUÁRIOS CRIADOS/ATUALIZADOS COM SUCESSO")
        print("=" * 65)

        for nome, email, acao in resultados:
            print(
                f"- {nome} ({email}): {acao}"
            )

        print("=" * 65)
        print(
            "Os dois usuários estão ativos e com perfil ADMIN."
        )
        print("")


if __name__ == "__main__":
    executar()