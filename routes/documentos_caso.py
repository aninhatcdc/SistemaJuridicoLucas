import mimetypes
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
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models import db
from models.caso import Caso
from models.documento_caso import DocumentoCaso

from services.storage import ErroStorage
from services.storage_service import (
    baixar_temporariamente,
    existe,
    remover,
    salvar,
    url_temporaria,
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
    Mantido para compatibilidade com documentos antigos
    que ainda possam existir localmente.
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
    pasta_caso = (
        obter_pasta_upload()
        / f"cliente_{caso.cliente_id}"
        / f"caso_{caso.id}"
    )

    pasta_caso.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta_caso    


def obter_caminho_seguro(documento):
    """
    Obtém o caminho de documentos antigos armazenados
    localmente.

    Documentos novos utilizam R2 e não passam por esta
    função.
    """
    pasta_upload = obter_pasta_upload().resolve()

    caminho_arquivo = (
        documento.caminho_arquivo
        or ""
    )

    if caminho_arquivo.startswith(
        "r2://"
    ):
        return None

    if caminho_arquivo.startswith(
        "local://"
    ):
        caminho_arquivo = caminho_arquivo[
            len("local://") :
        ]

    caminho_completo = (
        pasta_upload
        / caminho_arquivo
    ).resolve()

    try:
        caminho_completo.relative_to(
            pasta_upload
        )

    except ValueError:
        abort(403)

    return caminho_completo


def documento_esta_no_r2(documento):
    return (
        documento.caminho_arquivo
        and str(
            documento.caminho_arquivo
        ).startswith(
            "r2://"
        )
    )


def documento_existe(documento):
    """
    Verifica se o documento existe tanto no R2 quanto
    no armazenamento local antigo.
    """
    if not documento.caminho_arquivo:
        return False

    try:
        if documento_esta_no_r2(
            documento
        ):
            return existe(
                documento.caminho_arquivo
            )

        caminho_completo = (
            obter_caminho_seguro(
                documento
            )
        )

        return (
            caminho_completo is not None
            and caminho_completo.is_file()
        )

    except ErroStorage:
        current_app.logger.exception(
            "Erro ao verificar documento %s.",
            documento.id,
        )

        return False


def documento_pertence_ao_kit_trabalhista(
    documento
):
    observacoes = (
        documento.observacoes
        or ""
    ).lower()

    return (
        "kit trabalhista"
        in observacoes
    )


def criar_nome_unico_zip(
    nome_original,
    nomes_utilizados,
):
    nome_seguro = secure_filename(
        nome_original
        or "documento"
    )

    if not nome_seguro:
        nome_seguro = "documento"

    caminho = Path(nome_seguro)

    nome_base = (
        caminho.stem
        or "documento"
    )

    extensao = caminho.suffix

    candidato = nome_seguro
    contador = 2

    while (
        candidato.lower()
        in nomes_utilizados
    ):
        candidato = (
            f"{nome_base}_{contador}"
            f"{extensao}"
        )

        contador += 1

    nomes_utilizados.add(
        candidato.lower()
    )

    return candidato


def obter_content_type(
    arquivo,
    nome_arquivo,
):
    return (
        arquivo.mimetype
        or mimetypes.guess_type(
            nome_arquivo
        )[0]
        or "application/octet-stream"
    )


def obter_tamanho_arquivo(arquivo):
    """
    Obtém o tamanho do arquivo enviado sem precisar
    salvá-lo localmente.
    """
    try:
        stream = arquivo.stream

        posicao_atual = stream.tell()

        stream.seek(
            0,
            2,
        )

        tamanho = stream.tell()

        stream.seek(
            posicao_atual
        )

        return tamanho

    except (
        AttributeError,
        OSError,
    ):
        return None


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

    arquivo = request.files.get(
        "arquivo"
    )

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

    chave = (
        f"documentos_caso/"
        f"cliente_{caso.cliente_id}/"
        f"caso_{caso.id}/"
        f"{nome_salvo}"
    )

    caminho_storage = None

    try:
        tamanho_bytes = (
            obter_tamanho_arquivo(
                arquivo
            )
        )

        content_type = (
            obter_content_type(
                arquivo,
                nome_original_seguro,
            )
        )

        arquivo.stream.seek(0)

        caminho_storage = salvar(
            arquivo.stream,
            chave,
            content_type=content_type,
        )

        documento = DocumentoCaso(
            nome_original=arquivo.filename,
            nome_arquivo=nome_salvo,
            caminho_arquivo=caminho_storage,
            tipo_documento=tipo_documento,
            extensao=extensao,
            tamanho_bytes=tamanho_bytes,
            observacoes=observacoes,
            caso_id=caso.id,
            usuario_id=current_user.id,
        )

        db.session.add(
            documento
        )

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

        if caminho_storage:
            try:
                remover(
                    caminho_storage
                )

            except ErroStorage:
                current_app.logger.exception(
                    "Não foi possível remover o arquivo "
                    "enviado após erro no banco."
                )

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
        documento.extensao
        or ""
    ).lower()

    if (
        extensao
        not in EXTENSOES_VISUALIZAVEIS
    ):
        flash(
            "Este tipo de arquivo não pode ser "
            "visualizado no navegador.",
            "warning",
        )

        return redirect(
            url_for(
                "documentos_caso.download",
                documento_id=documento.id,
            )
        )

    try:
        if documento_esta_no_r2(
            documento
        ):
            if not existe(
                documento.caminho_arquivo
            ):
                flash(
                    "O arquivo não foi encontrado "
                    "no armazenamento.",
                    "danger",
                )

                return redirect(
                    url_for(
                        "casos.detalhes",
                        caso_id=documento.caso_id,
                    )
                )

            link = url_temporaria(
                documento.caminho_arquivo,
                expira_em=300,
            )

            if link:
                return redirect(
                    link
                )

        caminho_completo = (
            obter_caminho_seguro(
                documento
            )
        )

        if (
            caminho_completo is None
            or not caminho_completo.is_file()
        ):
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
            download_name=(
                documento.nome_original
            ),
            conditional=True,
        )

    except ErroStorage:
        current_app.logger.exception(
            "Erro ao visualizar documento %s.",
            documento.id,
        )

        flash(
            "Não foi possível acessar o arquivo "
            "no armazenamento.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=documento.caso_id,
            )
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
        if documento_esta_no_r2(
            documento
        ):
            if not existe(
                documento.caminho_arquivo
            ):
                flash(
                    "O arquivo não foi encontrado "
                    "no armazenamento.",
                    "danger",
                )

                return redirect(
                    url_for(
                        "casos.detalhes",
                        caso_id=documento.caso_id,
                    )
                )

            link = url_temporaria(
                documento.caminho_arquivo,
                nome_download=(
                    documento.nome_original
                ),
                expira_em=300,
            )

            if link:
                return redirect(
                    link
                )

        caminho_completo = (
            obter_caminho_seguro(
                documento
            )
        )

        if (
            caminho_completo is None
            or not caminho_completo.is_file()
        ):
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
            caminho_completo,
            as_attachment=True,
            download_name=(
                documento.nome_original
            ),
            conditional=True,
        )

    except ErroStorage:
        current_app.logger.exception(
            "Erro ao baixar documento %s.",
            documento.id,
        )

        flash(
            "Não foi possível baixar o arquivo "
            "do armazenamento.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=documento.caso_id,
            )
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
        .filter_by(
            caso_id=caso.id
        )
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
            "Este caso ainda não possui documentos "
            "gerados pelo Kit Trabalhista.",
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

    arquivos_temporarios = []

    try:
        with ZipFile(
            memoria_zip,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as arquivo_zip:

            for documento in documentos_kit:

                try:
                    if documento_esta_no_r2(
                        documento
                    ):
                        if not existe(
                            documento.caminho_arquivo
                        ):
                            current_app.logger.warning(
                                "Documento do Kit Trabalhista "
                                "não encontrado no R2: %s",
                                documento.caminho_arquivo,
                            )

                            continue

                        sufixo = (
                            f".{documento.extensao}"
                            if documento.extensao
                            else ""
                        )

                        caminho_completo = (
                            baixar_temporariamente(
                                documento.caminho_arquivo,
                                sufixo=sufixo,
                            )
                        )

                        arquivos_temporarios.append(
                            caminho_completo
                        )

                    else:
                        caminho_completo = (
                            obter_caminho_seguro(
                                documento
                            )
                        )

                    if (
                        caminho_completo is None
                        or not caminho_completo.is_file()
                    ):
                        current_app.logger.warning(
                            "Documento do Kit Trabalhista "
                            "não encontrado: %s",
                            documento.caminho_arquivo,
                        )

                        continue

                    nome_no_zip = (
                        criar_nome_unico_zip(
                            documento.nome_original,
                            nomes_utilizados,
                        )
                    )

                    arquivo_zip.write(
                        caminho_completo,
                        arcname=nome_no_zip,
                    )

                    quantidade_adicionada += 1

                except ErroStorage:
                    current_app.logger.exception(
                        "Erro ao baixar documento do "
                        "Kit Trabalhista: %s",
                        documento.id,
                    )

                    continue

    finally:
        for caminho in arquivos_temporarios:
            try:
                Path(
                    caminho
                ).unlink(
                    missing_ok=True
                )

            except OSError:
                current_app.logger.exception(
                    "Não foi possível remover "
                    "arquivo temporário: %s",
                    caminho,
                )

    if quantidade_adicionada == 0:
        flash(
            "Os registros do kit foram encontrados, "
            "mas os arquivos físicos não estão disponíveis.",
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

    caminho_arquivo = (
        documento.caminho_arquivo
    )

    try:
        TimelineService.registrar_documento_excluido(
            caso=caso,
            documento=documento,
        )

        db.session.delete(
            documento
        )

        db.session.commit()

        try:
            if caminho_arquivo:
                if str(
                    caminho_arquivo
                ).startswith(
                    "r2://"
                ):
                    remover(
                        caminho_arquivo
                    )

                else:
                    caminho_completo = (
                        obter_caminho_seguro(
                            type(
                                "DocumentoTemporario",
                                (),
                                {
                                    "caminho_arquivo":
                                    caminho_arquivo
                                },
                            )()
                        )
                    )

                    if (
                        caminho_completo
                        and caminho_completo.is_file()
                    ):
                        caminho_completo.unlink()

        except (
            ErroStorage,
            OSError,
        ):
            current_app.logger.exception(
                "O registro do documento foi excluído, "
                "mas não foi possível remover o arquivo "
                "físico: %s",
                caminho_arquivo,
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