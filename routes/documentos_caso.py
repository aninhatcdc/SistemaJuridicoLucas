import uuid
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models import db
from models.caso import Caso
from models.documento_caso import DocumentoCaso
from services.timeline_service import TimelineService


documentos_caso_bp = Blueprint(
    "documentos_caso",
    __name__,
    url_prefix="/documentos-caso",
)


EXTENSOES_PERMITIDAS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "csv",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "zip",
    "rar",
    "7z",
}


EXTENSOES_VISUALIZAVEIS = {
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "webp",
}


TIPOS_MIME = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def extensao_permitida(nome_arquivo):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower()
        in EXTENSOES_PERMITIDAS
    )


def obter_extensao(nome_arquivo):
    if "." not in nome_arquivo:
        return ""

    return nome_arquivo.rsplit(".", 1)[1].lower()


def obter_pasta_upload():
    pasta_upload = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    pasta_upload.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta_upload


def obter_pasta_caso(caso):
    pasta_upload = obter_pasta_upload()

    pasta_caso = (
        pasta_upload
        / f"cliente_{caso.cliente_id}"
        / f"caso_{caso.id}"
    )

    pasta_caso.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta_caso


def obter_caminho_seguro(documento):
    pasta_upload = obter_pasta_upload().resolve()

    caminho_completo = (
        pasta_upload
        / documento.caminho_arquivo
    ).resolve()

    try:
        caminho_completo.relative_to(pasta_upload)

    except ValueError:
        abort(403)

    return caminho_completo


def documento_pertence_ao_kit_trabalhista(documento):
    observacoes = (
        documento.observacoes
        or ""
    ).lower()

    return "kit trabalhista" in observacoes


def criar_nome_unico_zip(nome_original, nomes_utilizados):
    nome_seguro = secure_filename(
        nome_original
        or "documento"
    )

    if not nome_seguro:
        nome_seguro = "documento"

    caminho = Path(nome_seguro)
    nome_base = caminho.stem or "documento"
    extensao = caminho.suffix

    candidato = nome_seguro
    contador = 2

    while candidato.lower() in nomes_utilizados:
        candidato = (
            f"{nome_base}_{contador}"
            f"{extensao}"
        )
        contador += 1

    nomes_utilizados.add(
        candidato.lower()
    )

    return candidato


@documentos_caso_bp.route(
    "/caso/<string:caso_id>/novo",
    methods=["POST"],
)
@login_required
def novo(caso_id):
    caso = db.get_or_404(
        Caso,
        caso_id,
    )

    arquivo = request.files.get("arquivo")

    tipo_documento = (
        request.form.get(
            "tipo_documento",
            "",
        ).strip()
        or None
    )

    observacoes = (
        request.form.get(
            "observacoes",
            "",
        ).strip()
        or None
    )

    if not arquivo:
        flash(
            "Selecione um arquivo para enviar.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        )

    if not arquivo.filename:
        flash(
            "O arquivo selecionado não possui um nome válido.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        )

    nome_original_seguro = secure_filename(
        arquivo.filename
    )

    if not nome_original_seguro:
        flash(
            "O nome do arquivo é inválido.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        )

    if not extensao_permitida(
        nome_original_seguro
    ):
        flash(
            "Tipo de arquivo não permitido.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        )

    extensao = obter_extensao(
        nome_original_seguro
    )

    nome_salvo = (
        f"{uuid.uuid4().hex}.{extensao}"
    )

    pasta_caso = obter_pasta_caso(caso)
    caminho_completo = pasta_caso / nome_salvo

    try:
        arquivo.save(caminho_completo)

        tamanho_bytes = (
            caminho_completo.stat().st_size
        )

        pasta_upload = (
            obter_pasta_upload().resolve()
        )

        caminho_relativo = (
            caminho_completo.resolve()
            .relative_to(pasta_upload)
        )

        documento = DocumentoCaso(
            nome_original=arquivo.filename,
            nome_arquivo=nome_salvo,
            caminho_arquivo=str(
                caminho_relativo
            ),
            tipo_documento=tipo_documento,
            extensao=extensao,
            tamanho_bytes=tamanho_bytes,
            observacoes=observacoes,
            caso_id=caso.id,
            usuario_id=current_user.id,
        )

        db.session.add(documento)
        db.session.flush()

        TimelineService.registrar_documento_enviado(
            caso=caso,
            documento=documento,
        )

        db.session.commit()

        flash(
            "Documento enviado com sucesso.",
            "success",
        )

    except Exception:
        db.session.rollback()

        if caminho_completo.exists():
            caminho_completo.unlink()

        current_app.logger.exception(
            "Erro ao enviar documento para o caso %s.",
            caso.id,
        )

        flash(
            "Não foi possível enviar o documento.",
            "danger",
        )

    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso.id,
        )
    )


@documentos_caso_bp.route(
    "/<string:documento_id>/visualizar",
)
@login_required
def visualizar(documento_id):
    documento = db.get_or_404(
        DocumentoCaso,
        documento_id,
    )

    extensao = (
        documento.extensao or ""
    ).lower()

    if extensao not in EXTENSOES_VISUALIZAVEIS:
        flash(
            "Este tipo de arquivo não pode ser visualizado no navegador.",
            "warning",
        )

        return redirect(
            url_for(
                "documentos_caso.download",
                documento_id=documento.id,
            )
        )

    caminho_completo = obter_caminho_seguro(
        documento
    )

    if not caminho_completo.is_file():
        flash(
            "O arquivo não foi encontrado no servidor.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=documento.caso_id,
            )
        )

    tipo_mime = TIPOS_MIME.get(
        extensao,
        "application/octet-stream",
    )

    return send_file(
        caminho_completo,
        mimetype=tipo_mime,
        as_attachment=False,
        download_name=documento.nome_original,
        conditional=True,
    )


@documentos_caso_bp.route(
    "/<string:documento_id>/download",
)
@login_required
def download(documento_id):
    documento = db.get_or_404(
        DocumentoCaso,
        documento_id,
    )

    caminho_completo = obter_caminho_seguro(
        documento
    )

    if not caminho_completo.is_file():
        flash(
            "O arquivo não foi encontrado no servidor.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=documento.caso_id,
            )
        )

    return send_from_directory(
        directory=str(
            caminho_completo.parent
        ),
        path=caminho_completo.name,
        as_attachment=True,
        download_name=documento.nome_original,
    )


@documentos_caso_bp.route(
    "/caso/<string:caso_id>/baixar-kit-trabalhista",
)
@login_required
def baixar_kit_trabalhista(caso_id):
    caso = db.get_or_404(
        Caso,
        caso_id,
    )

    documentos = (
        DocumentoCaso.query
        .filter_by(caso_id=caso.id)
        .order_by(
            DocumentoCaso.criado_em.asc()
        )
        .all()
    )

    documentos_kit = [
        documento
        for documento in documentos
        if documento_pertence_ao_kit_trabalhista(
            documento
        )
    ]

    if not documentos_kit:
        flash(
            "Este caso ainda não possui documentos gerados pelo Kit Trabalhista.",
            "warning",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
                _anchor="documentos",
            )
        )

    memoria_zip = BytesIO()
    nomes_utilizados = set()
    quantidade_adicionada = 0

    with ZipFile(
        memoria_zip,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as arquivo_zip:

        for documento in documentos_kit:
            caminho_completo = obter_caminho_seguro(
                documento
            )

            if not caminho_completo.is_file():
                current_app.logger.warning(
                    "Documento do Kit Trabalhista não encontrado: %s",
                    caminho_completo,
                )
                continue

            nome_no_zip = criar_nome_unico_zip(
                documento.nome_original,
                nomes_utilizados,
            )

            arquivo_zip.write(
                caminho_completo,
                arcname=nome_no_zip,
            )

            quantidade_adicionada += 1

    if quantidade_adicionada == 0:
        flash(
            "Os registros do kit foram encontrados, mas os arquivos físicos não estão disponíveis.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
                _anchor="documentos",
            )
        )

    memoria_zip.seek(0)

    nome_cliente = secure_filename(
        caso.cliente.nome
        if caso.cliente
        else "cliente"
    )

    numero_caso = secure_filename(
        caso.numero_interno
        or "caso"
    )

    nome_download = (
        f"Kit_Trabalhista_"
        f"{nome_cliente or 'cliente'}_"
        f"{numero_caso or 'caso'}.zip"
    )

    return send_file(
        memoria_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=nome_download,
        max_age=0,
    )


@documentos_caso_bp.route(
    "/<string:documento_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir(documento_id):
    documento = db.get_or_404(
        DocumentoCaso,
        documento_id,
    )

    caso = db.get_or_404(
        Caso,
        documento.caso_id,
    )

    caminho_completo = obter_caminho_seguro(
        documento
    )

    try:
        TimelineService.registrar_documento_excluido(
            caso=caso,
            documento=documento,
        )

        db.session.delete(documento)
        db.session.commit()

        if caminho_completo.is_file():
            caminho_completo.unlink()

        flash(
            "Documento excluído com sucesso.",
            "success",
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao excluir documento %s.",
            documento.id,
        )

        flash(
            "Não foi possível excluir o documento.",
            "danger",
        )

    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso.id,
        )
    )