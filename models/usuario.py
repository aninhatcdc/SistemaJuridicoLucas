import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from models import db


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    PERFIL_ADMIN = "ADMIN"
    PERFIL_ADVOGADO = "ADV"
    PERFIL_ASSISTENTE = "ASSIST"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    nome = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    telefone = db.Column(
        db.String(20)
    )

    foto = db.Column(
        db.String(255)
    )

    senha_hash = db.Column(
        db.String(255),
        nullable=False
    )

    perfil = db.Column(
        db.String(20),
        nullable=False,
        default=PERFIL_ASSISTENTE
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    criado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    ultimo_login = db.Column(
        db.DateTime
    )

    casos_responsavel = db.relationship(
        "Caso",
        back_populates="responsavel",
        lazy=True
    )

    documentos_enviados = db.relationship(
        "DocumentoCaso",
        back_populates="usuario",
        lazy=True,
    )

    atendimentos = db.relationship(
        "AtendimentoCaso",
        back_populates="usuario",
        lazy=True,
        order_by="AtendimentoCaso.data_atendimento.desc()",
    )

    eventos_agenda = db.relationship(
        "EventoAgenda",
        back_populates="responsavel",
        passive_deletes=True,
        lazy=True,
        order_by=(
            "EventoAgenda.data.desc(), "
            "EventoAgenda.hora_inicio.desc()"
        ),
    )

    eventos_caso = db.relationship(
        "EventoCaso",
        back_populates="usuario",
        passive_deletes=True,
        lazy=True,
        order_by="EventoCaso.criado_em.desc()",
    )

    formularios_responsavel = db.relationship(
        "FormularioCaso",
        back_populates="usuario",
        passive_deletes=True,
        lazy=True,
        order_by="FormularioCaso.criado_em.desc()",
    )

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(
            self.senha_hash,
            senha,
        )

    @property
    def is_active(self):
        return self.ativo

    @property
    def is_admin(self):
        return self.perfil == self.PERFIL_ADMIN

    @property
    def is_advogado(self):
        return self.perfil == self.PERFIL_ADVOGADO

    @property
    def is_assistente(self):
        return self.perfil == self.PERFIL_ASSISTENTE

    def __repr__(self):
        return f"<Usuario {self.nome}>"