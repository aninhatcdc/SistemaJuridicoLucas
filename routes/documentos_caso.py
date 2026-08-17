import uuid
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models import db
from models.caso import Caso
from models.documento_caso import DocumentoCaso
from services.armazenamento_r2 import (
    ErroArmazenamento,
    baixar_arquivo_para_memoria,
    enviar_arquivo,
    excluir_arquivo,
)
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
    """
    Pasta local usada apenas como área de trabalho temporária por
    partes do sistema que ainda precisam de um arquivo físico em
    disco (ex.: geração de DOCX/conversão para PDF em
    routes/gerador_documentos.py e routes/modelos.py).

    Os documentos definitivos dos casos (upload feito pelo usuário)
    NÃO usam mais esta pasta — eles vão direto para o Cloudflare R2
    através das funções em services/armazenamento_r2.py.
    """
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


def gerar_chave_objeto(caso, nome_salvo):
    """
    Monta a "chave" (caminho) do objeto dentro do bucket do R2.
    Reaproveita a mesma organização que era usada em disco local:
    cliente_<id>/caso_<id>/<nome_salvo>
    """
    return (
        f"cliente_{caso.cliente_id}"
        f"/caso_{caso.id}"
        f"/{nome_salvo}"
    )


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

    chave_objeto = gerar_chave_objeto(
        caso,
        nome_salvo,
    )

    tipo_mime = TIPOS_MIME.get(
        extensao,
        arquivo.mimetype
        or "application/octet-stream",
    )

    try:
        # Descobre o tamanho antes de enviar (o upload consome o stream).
        arquivo.stream.seek(0, 2)
        tamanho_bytes = arquivo.stream.tell()
        arquivo.stream.seek(0)

        enviar_arquivo(
            arquivo,
            chave_objeto,
            content_type=tipo_mime,
        )

        documento = DocumentoCaso(
            nome_original=arquivo.filename,
            nome_arquivo=nome_salvo,
            caminho_arquivo=chave_objeto,
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

    except ErroArmazenamento:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao enviar documento (R2) para o caso %s.",
            caso.id,
        )

        flash(
            "Não foi possível enviar o documento. Verifique a "
            "configuração do armazenamento (R2).",
            "danger",
        )

    except Exception:
        db.session.rollback()

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

    tipo_mime = TIPOS_MIME.get(
        extensao,
        "application/octet-stream",
    )

    try:
        conteudo = baixar_arquivo_para_memoria(
            documento.caminho_arquivo
        )

    except ErroArmazenamento:
        current_app.logger.exception(
            "Erro ao buscar documento %s no R2.",
            documento.id,
        )

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

    return send_file(
        conteudo,
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

    try:
        conteudo = baixar_arquivo_para_memoria(
            documento.caminho_arquivo
        )

    except ErroArmazenamento:
        current_app.logger.exception(
            "Erro ao buscar documento %s no R2.",
            documento.id,
        )

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

    return send_file(
        conteudo,
        mimetype="application/octet-stream",
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
            try:
                conteudo = baixar_arquivo_para_memoria(
                    documento.caminho_arquivo
                )

            except ErroArmazenamento:
                current_app.logger.warning(
                    "Documento do Kit Trabalhista não encontrado no R2: %s",
                    documento.caminho_arquivo,
                )
                continue

            nome_no_zip = criar_nome_unico_zip(
                documento.nome_original,
                nomes_utilizados,
            )

            arquivo_zip.writestr(
                nome_no_zip,
                conteudo.read(),
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

    try:
        TimelineService.registrar_documento_excluido(
            caso=caso,
            documento=documento,
        )

        db.session.delete(documento)
        db.session.commit()

        try:
            excluir_arquivo(documento.caminho_arquivo)

        except ErroArmazenamento:
            current_app.logger.warning(
                "Registro do documento %s excluído, mas houve falha "
                "ao remover o arquivo do R2.",
                documento.id,
            )

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