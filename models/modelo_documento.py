import json
import uuid
from datetime import datetime

from models import db
from services.catalogo_variaveis import (
    contar_variaveis_invalidas,
    contar_variaveis_validas,
    validar_variaveis,
)


class ModeloDocumento(db.Model):
    __tablename__ = "modelos_documentos"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    nome = db.Column(
        db.String(150),
        nullable=False,
    )

    tipo_documento = db.Column(
        db.String(100),
        nullable=True,
    )

    categoria = db.Column(
        db.String(100),
        nullable=True,
    )

    area_juridica = db.Column(
        db.String(100),
        nullable=True,
    )

    descricao = db.Column(
        db.Text,
        nullable=True,
    )

    observacoes_uso = db.Column(
        db.Text,
        nullable=True,
    )

    versao = db.Column(
        db.String(30),
        nullable=False,
        default="1.0",
    )

    nome_arquivo = db.Column(
        db.String(255),
        nullable=False,
    )

    caminho_arquivo = db.Column(
        db.String(500),
        nullable=False,
    )

    variaveis_json = db.Column(
        db.Text,
        nullable=True,
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    criado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now,
    )

    atualizado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    criado_por_id = db.Column(
        db.String(36),
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )

    criado_por = db.relationship(
        "Usuario",
        foreign_keys=[criado_por_id],
        backref=db.backref(
            "modelos_documentos_criados",
            lazy=True,
        ),
    )

    @property
    def status_texto(self):
        return "Ativo" if self.ativo else "Inativo"

    @property
    def extensao(self):
        if not self.nome_arquivo:
            return ""

        if "." not in self.nome_arquivo:
            return ""

        return self.nome_arquivo.rsplit(
            ".",
            1,
        )[-1].lower()

    @property
    def eh_docx(self):
        return self.extensao == "docx"

    @property
    def variaveis(self):
        if not self.variaveis_json:
            return []

        try:
            dados = json.loads(
                self.variaveis_json
            )

            if isinstance(dados, list):
                return dados

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

        return []

    @property
    def variaveis_validadas(self):
        return validar_variaveis(
            self.variaveis
        )

    @property
    def quantidade_variaveis_validas(self):
        return contar_variaveis_validas(
            self.variaveis
        )

    @property
    def quantidade_variaveis_invalidas(self):
        return contar_variaveis_invalidas(
            self.variaveis
        )

    @property
    def todas_variaveis_validas(self):
        return (
            self.quantidade_variaveis_invalidas
            == 0
        )

    def definir_variaveis(self, variaveis):
        variaveis_limpas = sorted(
            {
                str(variavel).strip()
                for variavel in variaveis
                if str(variavel).strip()
            },
            key=lambda item: item.lower(),
        )

        self.variaveis_json = json.dumps(
            variaveis_limpas,
            ensure_ascii=False,
        )

    def __repr__(self):
        return (
            "<ModeloDocumento "
            f"id={self.id} "
            f"nome={self.nome!r} "
            f"versao={self.versao!r}>"
        )