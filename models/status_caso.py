import uuid

from models import db


class StatusCaso(db.Model):
    __tablename__ = "status_casos"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    nome = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    slug = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    descricao = db.Column(
        db.Text
    )

    cor = db.Column(
        db.String(20)
    )

    ordem = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    encerrado = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # Relacionamentos
    casos = db.relationship(
        "Caso",
        back_populates="status",
        lazy=True
    )

    def __repr__(self):
        return f"<StatusCaso {self.nome}>"