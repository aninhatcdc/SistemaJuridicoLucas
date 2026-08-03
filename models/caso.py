import uuid
from datetime import date, datetime

from models import db


class Caso(db.Model):
    __tablename__ = "casos"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    numero_interno = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True
    )

    titulo = db.Column(
        db.String(200),
        nullable=False
    )

    descricao = db.Column(
        db.Text
    )

    observacoes = db.Column(
        db.Text
    )

    prioridade = db.Column(
        db.String(20),
        nullable=False,
        default="NORMAL"
    )

    origem = db.Column(
        db.String(50)
    )

    data_abertura = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    data_encerramento = db.Column(
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

    # ============================================================
    # RELACIONAMENTOS DOS MÓDULOS DO CASO
    # ============================================================

    documentos = db.relationship(
        "DocumentoCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="DocumentoCaso.criado_em.desc()",
    )

    processos = db.relationship(
        "Processo",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="Processo.criado_em.desc()",
    )

    honorarios = db.relationship(
        "HonorarioCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="HonorarioCaso.criado_em.desc()",
    )

    atendimentos = db.relationship(
        "AtendimentoCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="AtendimentoCaso.data_atendimento.desc()",
    )

    eventos_agenda = db.relationship(
        "EventoAgenda",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by=(
            "EventoAgenda.data.desc(), "
            "EventoAgenda.hora_inicio.desc()"
        ),
    )

    eventos_timeline = db.relationship(
        "EventoCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="EventoCaso.criado_em.desc()",
    )

    atendimentos = db.relationship(
        "AtendimentoCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="AtendimentoCaso.data_atendimento.desc()",
    )

    formularios = db.relationship(
        "FormularioCaso",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="FormularioCaso.criado_em.desc()",
    )

    eventos_agenda = db.relationship(
        "EventoAgenda",
        back_populates="caso",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by=(
            "EventoAgenda.data.desc(), "
            "EventoAgenda.hora_inicio.desc()"
        ),
    )

    # ============================================================
    # CHAVES ESTRANGEIRAS
    # ============================================================

    cliente_id = db.Column(
        db.String(36),
        db.ForeignKey("clientes.id"),
        nullable=False,
        index=True
    )

    area_juridica_id = db.Column(
        db.String(36),
        db.ForeignKey("areas_juridicas.id"),
        nullable=False
    )

    status_id = db.Column(
        db.String(36),
        db.ForeignKey("status_casos.id"),
        nullable=False
    )

    responsavel_id = db.Column(
        db.String(36),
        db.ForeignKey("usuarios.id")
    )

    # ============================================================
    # RELACIONAMENTOS PRINCIPAIS
    # ============================================================

    cliente = db.relationship(
        "Cliente",
        back_populates="casos"
    )

    area_juridica = db.relationship(
        "AreaJuridica",
        back_populates="casos"
    )

    status = db.relationship(
        "StatusCaso",
        back_populates="casos"
    )

    responsavel = db.relationship(
        "Usuario",
        back_populates="casos_responsavel"
    )

    @property
    def encerrado(self):
        if self.status:
            return self.status.encerrado

        return False

    @property
    def dias_aberto(self):
        fim = self.data_encerramento or date.today()
        return (fim - self.data_abertura).days

    def __repr__(self):
        return f"<Caso {self.numero_interno}>"