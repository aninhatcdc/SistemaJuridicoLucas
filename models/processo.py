import uuid
from datetime import datetime

from models import db


class Processo(db.Model):
    __tablename__ = "processos"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    numero_cnj = db.Column(
        db.String(30),
        nullable=True,
        index=True,
    )

    tribunal = db.Column(
        db.String(100),
        nullable=True,
    )

    comarca = db.Column(
        db.String(100),
        nullable=True,
    )

    vara = db.Column(
        db.String(150),
        nullable=True,
    )

    classe_processual = db.Column(
        db.String(150),
        nullable=True,
    )

    assunto = db.Column(
        db.String(200),
        nullable=True,
    )

    polo_ativo = db.Column(
        db.String(200),
        nullable=True,
    )

    polo_passivo = db.Column(
        db.String(200),
        nullable=True,
    )

    data_distribuicao = db.Column(
        db.Date,
        nullable=True,
    )

    situacao = db.Column(
        db.String(50),
        nullable=False,
        default="ATIVO",
    )

    valor_causa = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    observacoes = db.Column(
        db.Text,
        nullable=True,
    )

    criado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    atualizado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    caso_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "casos.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    caso = db.relationship(
        "Caso",
        back_populates="processos",
    )

    eventos_agenda = db.relationship(
        "EventoAgenda",
        back_populates="processo",
        passive_deletes=True,
        lazy=True,
        order_by=(
            "EventoAgenda.data.desc(), "
            "EventoAgenda.hora_inicio.desc()"
        ),
    )

    @property
    def valor_causa_formatado(self):
        if self.valor_causa is None:
            return "Não informado"

        valor = float(self.valor_causa)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @property
    def situacao_formatada(self):
        situacoes = {
            "ATIVO": "Ativo",
            "SUSPENSO": "Suspenso",
            "ARQUIVADO": "Arquivado",
            "ENCERRADO": "Encerrado",
        }

        return situacoes.get(
            self.situacao,
            self.situacao,
        )

    def __repr__(self):
        return (
            f"<Processo "
            f"{self.numero_cnj or self.id}>"
        )