import uuid
from datetime import datetime

from models import db


class FormularioModelo(db.Model):
    __tablename__ = "formularios_modelo"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    nome = db.Column(
        db.String(150),
        nullable=False,
        index=True,
    )

    codigo = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    descricao = db.Column(
        db.Text,
    )

    versao = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
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

    area_juridica_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "areas_juridicas.id",
            ondelete="SET NULL",
        ),
        index=True,
    )

    area_juridica = db.relationship(
        "AreaJuridica",
        back_populates="formularios_modelo",
    )

    perguntas = db.relationship(
        "PerguntaFormulario",
        back_populates="formulario_modelo",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="PerguntaFormulario.ordem.asc()",
    )

    formularios_preenchidos = db.relationship(
        "FormularioCaso",
        back_populates="formulario_modelo",
        passive_deletes=True,
        lazy=True,
        order_by="FormularioCaso.criado_em.desc()",
    )

    @property
    def quantidade_perguntas(self):
        return len(self.perguntas)

    @property
    def status_formatado(self):
        return "Ativo" if self.ativo else "Inativo"

    def __repr__(self):
        return f"<FormularioModelo {self.nome}>"