import uuid
from datetime import datetime

from models import db


class FormularioCaso(db.Model):
    __tablename__ = "formularios_caso"

    STATUS = {
        "RASCUNHO": "Rascunho",
        "CONCLUIDO": "Concluído",
        "CANCELADO": "Cancelado",
    }

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    titulo = db.Column(
        db.String(200),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="RASCUNHO",
        index=True,
    )

    versao_modelo = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    observacoes = db.Column(
        db.Text,
    )

    iniciado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    concluido_em = db.Column(
        db.DateTime,
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

    formulario_modelo_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "formularios_modelo.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
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

    cliente_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    usuario_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "usuarios.id",
            ondelete="SET NULL",
        ),
        index=True,
    )

    formulario_modelo = db.relationship(
        "FormularioModelo",
        back_populates="formularios_preenchidos",
    )

    caso = db.relationship(
        "Caso",
        back_populates="formularios",
    )

    cliente = db.relationship(
        "Cliente",
        back_populates="formularios",
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="formularios_responsavel",
    )

    respostas = db.relationship(
        "RespostaFormulario",
        back_populates="formulario_caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="RespostaFormulario.criado_em.asc()",
    )

    @property
    def status_formatado(self):
        return self.STATUS.get(
            self.status,
            self.status or "Não informado",
        )

    @property
    def status_classe(self):
        classes = {
            "RASCUNHO": "bg-warning text-dark",
            "CONCLUIDO": "bg-success",
            "CANCELADO": "bg-secondary",
        }

        return classes.get(
            self.status,
            "bg-secondary",
        )

    @property
    def concluido(self):
        return self.status == "CONCLUIDO"

    @property
    def quantidade_respostas(self):
        return len(self.respostas)

    def concluir(self):
        self.status = "CONCLUIDO"
        self.concluido_em = datetime.utcnow()

    def reabrir(self):
        self.status = "RASCUNHO"
        self.concluido_em = None

    def cancelar(self):
        self.status = "CANCELADO"

    def __repr__(self):
        return f"<FormularioCaso {self.titulo}>"