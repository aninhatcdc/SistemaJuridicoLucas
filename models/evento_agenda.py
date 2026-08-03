import uuid
from datetime import date, datetime

from models import db


class EventoAgenda(db.Model):
    __tablename__ = "eventos_agenda"

    TIPOS = {
        "AUDIENCIA": "Audiência",
        "PRAZO": "Prazo",
        "REUNIAO": "Reunião",
        "ATENDIMENTO": "Atendimento agendado",
        "TAREFA": "Tarefa",
        "LEMBRETE": "Lembrete",
    }

    STATUS = {
        "PENDENTE": "Pendente",
        "EM_ANDAMENTO": "Em andamento",
        "CONCLUIDO": "Concluído",
        "CANCELADO": "Cancelado",
    }

    PRIORIDADES = {
        "BAIXA": "Baixa",
        "NORMAL": "Normal",
        "ALTA": "Alta",
        "URGENTE": "Urgente",
    }

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    titulo = db.Column(
        db.String(200),
        nullable=False,
        index=True,
    )

    descricao = db.Column(
        db.Text,
        nullable=True,
    )

    tipo = db.Column(
        db.String(30),
        nullable=False,
        default="TAREFA",
        index=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDENTE",
        index=True,
    )

    prioridade = db.Column(
        db.String(20),
        nullable=False,
        default="NORMAL",
        index=True,
    )

    data = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    hora_inicio = db.Column(
        db.Time,
        nullable=True,
    )

    hora_fim = db.Column(
        db.Time,
        nullable=True,
    )

    local = db.Column(
        db.String(200),
        nullable=True,
    )

    concluido_em = db.Column(
        db.DateTime,
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

    # ============================================================
    # CHAVES ESTRANGEIRAS
    # ============================================================

    caso_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "casos.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    processo_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "processos.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    responsavel_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "usuarios.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ============================================================
    # RELACIONAMENTOS
    # ============================================================

    caso = db.relationship(
        "Caso",
        back_populates="eventos_agenda",
    )

    processo = db.relationship(
        "Processo",
        back_populates="eventos_agenda",
    )

    responsavel = db.relationship(
        "Usuario",
        back_populates="eventos_agenda",
    )

    # ============================================================
    # PROPRIEDADES DE EXIBIÇÃO
    # ============================================================

    @property
    def tipo_formatado(self):
        return self.TIPOS.get(
            self.tipo,
            self.tipo or "Não informado",
        )

    @property
    def status_formatado(self):
        return self.STATUS.get(
            self.status,
            self.status or "Não informado",
        )

    @property
    def prioridade_formatada(self):
        return self.PRIORIDADES.get(
            self.prioridade,
            self.prioridade or "Não informada",
        )

    @property
    def data_formatada(self):
        if not self.data:
            return "Não informada"

        return self.data.strftime("%d/%m/%Y")

    @property
    def hora_inicio_formatada(self):
        if not self.hora_inicio:
            return ""

        return self.hora_inicio.strftime("%H:%M")

    @property
    def hora_fim_formatada(self):
        if not self.hora_fim:
            return ""

        return self.hora_fim.strftime("%H:%M")

    @property
    def horario_formatado(self):
        if self.hora_inicio and self.hora_fim:
            return (
                f"{self.hora_inicio.strftime('%H:%M')} até "
                f"{self.hora_fim.strftime('%H:%M')}"
            )

        if self.hora_inicio:
            return self.hora_inicio.strftime("%H:%M")

        return "Horário não informado"

    # ============================================================
    # SITUAÇÃO DO EVENTO
    # ============================================================

    @property
    def concluido(self):
        return self.status == "CONCLUIDO"

    @property
    def cancelado(self):
        return self.status == "CANCELADO"

    @property
    def pendente(self):
        return self.status == "PENDENTE"

    @property
    def em_andamento(self):
        return self.status == "EM_ANDAMENTO"

    @property
    def atrasado(self):
        if not self.data:
            return False

        if self.status in {
            "CONCLUIDO",
            "CANCELADO",
        }:
            return False

        return self.data < date.today()

    @property
    def acontece_hoje(self):
        if not self.data:
            return False

        return self.data == date.today()

    @property
    def futuro(self):
        if not self.data:
            return False

        return self.data > date.today()

    @property
    def dias_restantes(self):
        if not self.data:
            return None

        return (self.data - date.today()).days

    # ============================================================
    # CLASSES BOOTSTRAP
    # ============================================================

    @property
    def tipo_classe(self):
        classes = {
            "AUDIENCIA": "danger",
            "PRAZO": "warning",
            "REUNIAO": "primary",
            "ATENDIMENTO": "info",
            "TAREFA": "secondary",
            "LEMBRETE": "dark",
        }

        return classes.get(
            self.tipo,
            "secondary",
        )

    @property
    def status_classe(self):
        if self.atrasado:
            return "danger"

        classes = {
            "PENDENTE": "warning",
            "EM_ANDAMENTO": "primary",
            "CONCLUIDO": "success",
            "CANCELADO": "secondary",
        }

        return classes.get(
            self.status,
            "secondary",
        )

    @property
    def prioridade_classe(self):
        classes = {
            "BAIXA": "success",
            "NORMAL": "secondary",
            "ALTA": "warning",
            "URGENTE": "danger",
        }

        return classes.get(
            self.prioridade,
            "secondary",
        )

    # ============================================================
    # MÉTODOS
    # ============================================================

    def marcar_como_concluido(self):
        self.status = "CONCLUIDO"
        self.concluido_em = datetime.utcnow()

    def reabrir(self):
        self.status = "PENDENTE"
        self.concluido_em = None

    def cancelar(self):
        self.status = "CANCELADO"
        self.concluido_em = None

    def __repr__(self):
        return (
            f"<EventoAgenda "
            f"{self.titulo} - {self.data}>"
        )