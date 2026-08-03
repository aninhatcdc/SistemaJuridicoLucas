import uuid
from datetime import datetime

from models import db


class DocumentoCaso(db.Model):
    __tablename__ = "documentos_caso"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    nome_original = db.Column(
        db.String(255),
        nullable=False,
    )

    nome_arquivo = db.Column(
        db.String(255),
        nullable=False,
    )

    caminho_arquivo = db.Column(
        db.String(500),
        nullable=False,
    )

    tipo_documento = db.Column(
        db.String(100),
        nullable=True,
    )

    extensao = db.Column(
        db.String(20),
        nullable=True,
    )

    tamanho_bytes = db.Column(
        db.Integer,
        nullable=True,
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

    caso = db.relationship(
        "Caso",
        back_populates="documentos",
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="documentos_enviados",
    )

    @property
    def tamanho_formatado(self):
        if not self.tamanho_bytes:
            return "0 KB"

        tamanho = float(self.tamanho_bytes)

        if tamanho < 1024:
            return f"{int(tamanho)} bytes"

        tamanho /= 1024

        if tamanho < 1024:
            return f"{tamanho:.1f} KB"

        tamanho /= 1024

        if tamanho < 1024:
            return f"{tamanho:.1f} MB"

        tamanho /= 1024

        return f"{tamanho:.1f} GB"

    @property
    def icone(self):
        extensao = (self.extensao or "").lower()

        if extensao == "pdf":
            return "📕"

        if extensao in {"doc", "docx"}:
            return "📘"

        if extensao in {"xls", "xlsx", "csv"}:
            return "📗"

        if extensao in {"jpg", "jpeg", "png", "webp"}:
            return "🖼️"

        if extensao in {"zip", "rar", "7z"}:
            return "🗜️"

        return "📄"

    def __repr__(self):
        return (
            f"<DocumentoCaso "
            f"{self.nome_original} - {self.caso_id}>"
        )