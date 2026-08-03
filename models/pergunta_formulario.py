import json
import uuid
from datetime import datetime

from models import db


class PerguntaFormulario(db.Model):
    __tablename__ = "perguntas_formulario"

    TIPOS = {
        "TEXTO": "Texto curto",
        "TEXTO_LONGO": "Texto longo",
        "NUMERO": "Número",
        "MOEDA": "Moeda",
        "DATA": "Data",
        "HORA": "Hora",
        "SIM_NAO": "Sim ou não",
        "SELECAO": "Seleção única",
        "MULTIPLA_SELECAO": "Múltipla seleção",
        "EMAIL": "E-mail",
        "TELEFONE": "Telefone",
        "CPF": "CPF",
        "CNPJ": "CNPJ",
    }

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    codigo = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    texto = db.Column(
        db.String(500),
        nullable=False,
    )

    descricao = db.Column(
        db.Text,
    )

    tipo = db.Column(
        db.String(30),
        nullable=False,
        default="TEXTO",
    )

    ordem = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        index=True,
    )

    etapa = db.Column(
        db.String(100),
        nullable=False,
        default="Geral",
        index=True,
    )

    ordem_etapa = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        index=True,
    )

    grupo = db.Column(
        db.String(100),
    )

    icone = db.Column(
        db.String(30),
        nullable=False,
        default="📄",
    )

    descricao_etapa = db.Column(
        db.String(255),
    )

    obrigatoria = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    placeholder = db.Column(
        db.String(255),
    )

    opcoes_json = db.Column(
        db.Text,
    )

    valor_padrao = db.Column(
        db.Text,
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
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    formulario_modelo = db.relationship(
        "FormularioModelo",
        back_populates="perguntas",
    )

    respostas = db.relationship(
        "RespostaFormulario",
        back_populates="pergunta",
        passive_deletes=True,
        lazy=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "formulario_modelo_id",
            "codigo",
            name="uq_pergunta_formulario_codigo",
        ),
    )

    @property
    def tipo_formatado(self):
        return self.TIPOS.get(
            self.tipo,
            self.tipo or "Não informado",
        )

    @property
    def etapa_formatada(self):
        return self.etapa or "Geral"

    @property
    def icone_etapa(self):
        return self.icone or "📄"

    @property
    def opcoes(self):
        if not self.opcoes_json:
            return []

        try:
            dados = json.loads(self.opcoes_json)

            if isinstance(dados, list):
                return dados

            return []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    @opcoes.setter
    def opcoes(self, valores):
        if not valores:
            self.opcoes_json = None
            return

        self.opcoes_json = json.dumps(
            valores,
            ensure_ascii=False,
        )

    @property
    def aceita_opcoes(self):
        return self.tipo in {
            "SELECAO",
            "MULTIPLA_SELECAO",
        }

    @property
    def status_formatado(self):
        return "Ativa" if self.ativo else "Inativa"

    def __repr__(self):
        return (
            f"<PerguntaFormulario "
            f"{self.codigo}: {self.texto}>"
        )