import uuid

from models import db


class AreaJuridica(db.Model):
    __tablename__ = "areas_juridicas"

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

    icone = db.Column(
        db.String(50)
    )

    cor = db.Column(
        db.String(20)
    )

    ativa = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    ordem = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    # Relacionamentos
    casos = db.relationship(
        "Caso",
        back_populates="area_juridica",
        lazy=True
    )

    formularios_modelo = db.relationship(
        "FormularioModelo",
        back_populates="area_juridica",
        passive_deletes=True,
        lazy=True,
        order_by="FormularioModelo.nome.asc()",
    )


    def __repr__(self):
        return f"<AreaJuridica {self.nome}>"