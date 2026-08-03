import uuid
from datetime import datetime

from models import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # =========================================================
    # DADOS PESSOAIS
    # =========================================================

    nome = db.Column(
        db.String(150),
        nullable=False,
        index=True,
    )

    cpf = db.Column(
        db.String(14),
        unique=True,
        nullable=False,
        index=True,
    )

    rg = db.Column(
        db.String(20),
    )

    orgao_expedidor = db.Column(
        db.String(20),
    )

    uf_rg = db.Column(
        db.String(2),
    )

    data_nascimento = db.Column(
        db.Date,
    )

    sexo = db.Column(
        db.String(20),
    )

    nacionalidade = db.Column(
        db.String(60),
        default="Brasileira",
    )

    naturalidade = db.Column(
        db.String(100),
    )

    uf_naturalidade = db.Column(
        db.String(2),
    )

    estado_civil = db.Column(
        db.String(30),
    )

    profissao = db.Column(
        db.String(100),
    )

    # =========================================================
    # FILIAÇÃO
    # =========================================================

    nome_mae = db.Column(
        db.String(150),
    )

    nome_pai = db.Column(
        db.String(150),
    )

    # =========================================================
    # CONTATO
    # =========================================================

    telefone = db.Column(
        db.String(20),
    )

    whatsapp = db.Column(
        db.String(20),
    )

    email = db.Column(
        db.String(120),
        index=True,
    )

    # =========================================================
    # ENDEREÇO
    # =========================================================

    cep = db.Column(
        db.String(10),
    )

    logradouro = db.Column(
        db.String(150),
    )

    numero = db.Column(
        db.String(20),
    )

    complemento = db.Column(
        db.String(100),
    )

    bairro = db.Column(
        db.String(100),
    )

    cidade = db.Column(
        db.String(100),
    )

    estado = db.Column(
        db.String(2),
    )

    # =========================================================
    # INFORMAÇÕES DO CADASTRO
    # =========================================================

    origem = db.Column(
        db.String(50),
    )

    observacoes = db.Column(
        db.Text,
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
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

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================

    casos = db.relationship(
        "Caso",
        back_populates="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )

    formularios = db.relationship(
        "FormularioCaso",
        back_populates="cliente",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FormularioCaso.criado_em.desc()",
    )

    # =========================================================
    # PROPRIEDADES PARA EXIBIÇÃO E DOCUMENTOS
    # =========================================================

    @property
    def endereco_completo(self):
        partes = []

        if self.logradouro:
            endereco_inicial = self.logradouro

            if self.numero:
                endereco_inicial += f", nº {self.numero}"

            partes.append(endereco_inicial)
        elif self.numero:
            partes.append(f"nº {self.numero}")

        if self.complemento:
            partes.append(self.complemento)

        if self.bairro:
            partes.append(f"Bairro {self.bairro}")

        cidade_estado = ""

        if self.cidade:
            cidade_estado = self.cidade

        if self.estado:
            cidade_estado += (
                f"/{self.estado}"
                if cidade_estado
                else self.estado
            )

        if cidade_estado:
            partes.append(cidade_estado)

        if self.cep:
            partes.append(f"CEP {self.cep}")

        return ", ".join(partes)

    @property
    def naturalidade_completa(self):
        naturalidade = (self.naturalidade or "").strip()
        uf = (self.uf_naturalidade or "").strip().upper()

        if naturalidade and uf:
            return f"{naturalidade}/{uf}"

        return naturalidade or uf

    @property
    def rg_completo(self):
        partes = []

        if self.rg:
            partes.append(self.rg)

        expedidor = (self.orgao_expedidor or "").strip()
        uf = (self.uf_rg or "").strip().upper()

        if expedidor and uf:
            partes.append(f"{expedidor}/{uf}")
        elif expedidor:
            partes.append(expedidor)
        elif uf:
            partes.append(uf)

        return " - ".join(partes)

    @property
    def quantidade_casos(self):
        return len(self.casos)

    def __repr__(self):
        return f"<Cliente {self.nome}>"