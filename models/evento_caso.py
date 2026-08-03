import json
import uuid
from datetime import datetime

from models import db


class EventoCaso(db.Model):
    __tablename__ = "eventos_caso"

    # ============================================================
    # TIPOS DE EVENTO
    # ============================================================

    TIPO_CASO_CRIADO = "CASO_CRIADO"
    TIPO_CASO_EDITADO = "CASO_EDITADO"
    TIPO_STATUS_ALTERADO = "STATUS_ALTERADO"
    TIPO_PRIORIDADE_ALTERADA = "PRIORIDADE_ALTERADA"
    TIPO_RESPONSAVEL_ALTERADO = "RESPONSAVEL_ALTERADO"

    TIPO_PROCESSO_CRIADO = "PROCESSO_CRIADO"
    TIPO_PROCESSO_EDITADO = "PROCESSO_EDITADO"
    TIPO_PROCESSO_EXCLUIDO = "PROCESSO_EXCLUIDO"

    TIPO_DOCUMENTO_ENVIADO = "DOCUMENTO_ENVIADO"
    TIPO_DOCUMENTO_GERADO = "DOCUMENTO_GERADO"
    TIPO_DOCUMENTO_EXCLUIDO = "DOCUMENTO_EXCLUIDO"

    TIPO_HONORARIO_CRIADO = "HONORARIO_CRIADO"
    TIPO_HONORARIO_EDITADO = "HONORARIO_EDITADO"
    TIPO_PAGAMENTO_REGISTRADO = "PAGAMENTO_REGISTRADO"

    TIPO_ATENDIMENTO_CRIADO = "ATENDIMENTO_CRIADO"
    TIPO_ATENDIMENTO_EDITADO = "ATENDIMENTO_EDITADO"

    TIPO_AGENDA_CRIADA = "AGENDA_CRIADA"
    TIPO_AGENDA_EDITADA = "AGENDA_EDITADA"
    TIPO_AGENDA_CONCLUIDA = "AGENDA_CONCLUIDA"

    TIPO_OBSERVACAO = "OBSERVACAO"

    # ============================================================
    # IDENTIFICAÇÃO
    # ============================================================

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    tipo = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    titulo = db.Column(
        db.String(200),
        nullable=False,
    )

    descricao = db.Column(
        db.Text,
    )

    icone = db.Column(
        db.String(20),
        nullable=False,
        default="📝",
    )

    cor = db.Column(
        db.String(30),
        nullable=False,
        default="secondary",
    )

    url = db.Column(
        db.String(500),
    )

    dados_json = db.Column(
        db.Text,
    )

    criado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
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
        nullable=False,
        index=True,
    )

    usuario_id = db.Column(
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
        back_populates="eventos_timeline",
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="eventos_caso",
    )

    # ============================================================
    # PROPRIEDADES
    # ============================================================

    @property
    def dados(self):
        if not self.dados_json:
            return {}

        try:
            return json.loads(self.dados_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    @dados.setter
    def dados(self, valor):
        if valor is None:
            self.dados_json = None
            return

        self.dados_json = json.dumps(
            valor,
            ensure_ascii=False,
            default=str,
        )

    @property
    def data_formatada(self):
        return self.criado_em.strftime("%d/%m/%Y")

    @property
    def hora_formatada(self):
        return self.criado_em.strftime("%H:%M")

    @property
    def data_hora_formatada(self):
        return self.criado_em.strftime(
            "%d/%m/%Y às %H:%M"
        )

    def __repr__(self):
        return (
            f"<EventoCaso "
            f"{self.tipo} - {self.titulo}>"
        )