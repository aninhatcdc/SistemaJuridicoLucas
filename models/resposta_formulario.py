import json
import uuid
from datetime import datetime
from decimal import Decimal

from models import db


class RespostaFormulario(db.Model):
    __tablename__ = "respostas_formulario"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    valor_texto = db.Column(
        db.Text,
    )

    valor_numero = db.Column(
        db.Numeric(
            precision=15,
            scale=2,
        ),
    )

    valor_data = db.Column(
        db.Date,
    )

    valor_hora = db.Column(
        db.Time,
    )

    valor_booleano = db.Column(
        db.Boolean,
    )

    valor_json = db.Column(
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

    formulario_caso_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "formularios_caso.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    pergunta_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "perguntas_formulario.id",
            ondelete="SET NULL",
        ),
        index=True,
    )

    formulario_caso = db.relationship(
        "FormularioCaso",
        back_populates="respostas",
    )

    pergunta = db.relationship(
        "PerguntaFormulario",
        back_populates="respostas",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "formulario_caso_id",
            "pergunta_id",
            name="uq_resposta_formulario_pergunta",
        ),
    )

    def limpar_valores(self):
        self.valor_texto = None
        self.valor_numero = None
        self.valor_data = None
        self.valor_hora = None
        self.valor_booleano = None
        self.valor_json = None

    @property
    def valor_lista(self):
        if not self.valor_json:
            return []

        try:
            dados = json.loads(self.valor_json)

            if isinstance(dados, list):
                return dados

            return []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    @valor_lista.setter
    def valor_lista(self, valores):
        if not valores:
            self.valor_json = None
            return

        self.valor_json = json.dumps(
            valores,
            ensure_ascii=False,
        )

    @property
    def valor(self):
        if not self.pergunta:
            return self.valor_texto

        tipo = self.pergunta.tipo

        if tipo in {
            "TEXTO",
            "TEXTO_LONGO",
            "EMAIL",
            "TELEFONE",
            "CPF",
            "CNPJ",
            "SELECAO",
        }:
            return self.valor_texto

        if tipo in {
            "NUMERO",
            "MOEDA",
        }:
            return self.valor_numero

        if tipo == "DATA":
            return self.valor_data

        if tipo == "HORA":
            return self.valor_hora

        if tipo == "SIM_NAO":
            return self.valor_booleano

        if tipo == "MULTIPLA_SELECAO":
            return self.valor_lista

        return self.valor_texto

    @property
    def valor_formatado(self):
        valor = self.valor

        if valor is None:
            return ""

        if isinstance(valor, bool):
            return "Sim" if valor else "Não"

        if isinstance(valor, Decimal):
            if self.pergunta and self.pergunta.tipo == "MOEDA":
                numero = f"{valor:,.2f}"

                numero = (
                    numero
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

                return f"R$ {numero}"

            return str(valor)

        if isinstance(valor, list):
            return ", ".join(str(item) for item in valor)

        if hasattr(valor, "strftime"):
            if self.pergunta and self.pergunta.tipo == "DATA":
                return valor.strftime("%d/%m/%Y")

            if self.pergunta and self.pergunta.tipo == "HORA":
                return valor.strftime("%H:%M")

        return str(valor)

    def __repr__(self):
        codigo = (
            self.pergunta.codigo
            if self.pergunta
            else "SEM_PERGUNTA"
        )

        return f"<RespostaFormulario {codigo}>"