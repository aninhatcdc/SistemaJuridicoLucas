import uuid
from datetime import date, datetime

from models import db


class AtendimentoCaso(db.Model):
    __tablename__ = "atendimentos_caso"

    TIPOS = {
        "CONSULTA": "Consulta",
        "REUNIAO": "Reunião",
        "LIGACAO": "Ligação",
        "WHATSAPP": "WhatsApp",
        "EMAIL": "E-mail",
        "AUDIENCIA": "Audiência",
        "DILIGENCIA": "Diligência",
        "OUTRO": "Outro",
    }

    STATUS = {
        "AGENDADO": "Agendado",
        "REALIZADO": "Realizado",
        "CANCELADO": "Cancelado",
    }

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    tipo = db.Column(
        db.String(30),
        nullable=False,
        default="CONSULTA"
    )

    assunto = db.Column(
        db.String(200),
        nullable=False
    )

    data_atendimento = db.Column(
        db.Date,
        nullable=False,
        default=date.today,
        index=True
    )

    horario = db.Column(
        db.Time
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="AGENDADO"
    )

    descricao = db.Column(
        db.Text
    )

    retorno_em = db.Column(
        db.Date
    )

    criado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    atualizado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    caso_id = db.Column(
        db.String(36),
        db.ForeignKey("casos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    usuario_id = db.Column(
        db.String(36),
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True
    )

    caso = db.relationship(
        "Caso",
        back_populates="atendimentos"
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="atendimentos"
    )

    @property
    def tipo_formatado(self):
        return self.TIPOS.get(self.tipo, self.tipo or "Não informado")

    @property
    def status_formatado(self):
        return self.STATUS.get(self.status, self.status or "Não informado")

    @property
    def status_classe(self):
        classes = {
            "AGENDADO": "bg-primary",
            "REALIZADO": "bg-success",
            "CANCELADO": "bg-secondary",
        }
        return classes.get(self.status, "bg-secondary")

    def __repr__(self):
        return f"<AtendimentoCaso {self.assunto}>"