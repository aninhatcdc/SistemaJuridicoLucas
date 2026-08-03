import uuid
from datetime import datetime
from decimal import Decimal

from models import db


class HonorarioCaso(db.Model):
    __tablename__ = "honorarios_caso"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    descricao = db.Column(
        db.String(200),
        nullable=False,
        default="Honorários advocatícios",
    )

    tipo_cobranca = db.Column(
        db.String(30),
        nullable=False,
        default="FIXO",
    )

    valor_total = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    valor_entrada = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    quantidade_parcelas = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    forma_pagamento = db.Column(
        db.String(50),
        nullable=True,
    )

    percentual_exito = db.Column(
        db.Numeric(5, 2),
        nullable=True,
    )

    data_contrato = db.Column(
        db.Date,
        nullable=True,
    )

    primeiro_vencimento = db.Column(
        db.Date,
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="ATIVO",
    )

    observacoes = db.Column(
        db.Text,
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

    caso_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "casos.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    caso = db.relationship(
        "Caso",
        back_populates="honorarios",
    )

    parcelas = db.relationship(
        "ParcelaHonorario",
        back_populates="honorario",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True,
        order_by="ParcelaHonorario.numero.asc()",
    )

    @property
    def valor_total_formatado(self):
        return formatar_moeda(self.valor_total)

    @property
    def valor_entrada_formatado(self):
        return formatar_moeda(self.valor_entrada)

    @property
    def total_pago(self):
        total = Decimal("0.00")

        for parcela in self.parcelas:
            if parcela.status == "PAGO":
                total += Decimal(str(parcela.valor or 0))

        return total

    @property
    def total_pago_formatado(self):
        return formatar_moeda(self.total_pago)

    @property
    def saldo_pendente(self):
        total = Decimal(str(self.valor_total or 0))
        entrada = Decimal(str(self.valor_entrada or 0))
        pago = Decimal(str(self.total_pago or 0))

        saldo = total - entrada - pago

        return max(saldo, Decimal("0.00"))

    @property
    def saldo_pendente_formatado(self):
        return formatar_moeda(self.saldo_pendente)

    @property
    def status_formatado(self):
        opcoes = {
            "ATIVO": "Ativo",
            "QUITADO": "Quitado",
            "CANCELADO": "Cancelado",
            "SUSPENSO": "Suspenso",
        }

        return opcoes.get(
            self.status,
            self.status,
        )

    @property
    def tipo_cobranca_formatado(self):
        opcoes = {
            "FIXO": "Valor fixo",
            "EXITO": "Êxito",
            "FIXO_EXITO": "Fixo + êxito",
            "CONSULTA": "Consulta",
            "MENSAL": "Mensal",
        }

        return opcoes.get(
            self.tipo_cobranca,
            self.tipo_cobranca,
        )

    def __repr__(self):
        return (
            f"<HonorarioCaso "
            f"{self.id} - {self.caso_id}>"
        )


class ParcelaHonorario(db.Model):
    __tablename__ = "parcelas_honorario"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    numero = db.Column(
        db.Integer,
        nullable=False,
    )

    valor = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    data_vencimento = db.Column(
        db.Date,
        nullable=True,
    )

    data_pagamento = db.Column(
        db.Date,
        nullable=True,
    )

    forma_pagamento = db.Column(
        db.String(50),
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDENTE",
    )

    observacoes = db.Column(
        db.Text,
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

    honorario_id = db.Column(
        db.String(36),
        db.ForeignKey(
            "honorarios_caso.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    honorario = db.relationship(
        "HonorarioCaso",
        back_populates="parcelas",
    )

    @property
    def valor_formatado(self):
        return formatar_moeda(self.valor)

    @property
    def status_formatado(self):
        opcoes = {
            "PENDENTE": "Pendente",
            "PAGO": "Pago",
            "ATRASADO": "Atrasado",
            "CANCELADO": "Cancelado",
        }

        return opcoes.get(
            self.status,
            self.status,
        )

    def __repr__(self):
        return (
            f"<ParcelaHonorario "
            f"{self.numero} - {self.status}>"
        )


def formatar_moeda(valor):
    valor = float(valor or 0)

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )