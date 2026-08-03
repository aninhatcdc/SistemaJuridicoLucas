import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from models import db
from models.modelo_documento import ModeloDocumento
from services.scanner_variaveis import (
    ErroLeituraDocumento,
    escanear_variaveis_docx,
)


modelos_bp = Blueprint(
    "modelos",
    __name__,
    url_prefix="/modelos",
)


EXTENSOES_PERMITIDAS = {
    "docx",
}


def arquivo_permitido(nome_arquivo):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower()
        in EXTENSOES_PERMITIDAS
    )


def obter_pasta_modelos():
    pasta_uploads = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    pasta = (
        pasta_uploads
        / "modelos_documentos"
    )

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta


def obter_caminho_modelo(modelo):
    caminho = Path(
        modelo.caminho_arquivo
    )

    if caminho.is_absolute():
        return caminho

    return (
        Path(current_app.root_path)
        / caminho
    )


def salvar_arquivo_modelo(arquivo):
    nome_original = secure_filename(
        arquivo.filename
    )

    extensao = (
        nome_original.rsplit(".", 1)[1].lower()
    )

    nome_salvo = (
        f"{uuid.uuid4()}.{extensao}"
    )

    pasta = obter_pasta_modelos()

    caminho_absoluto = (
        pasta
        / nome_salvo
    )

    arquivo.save(
        caminho_absoluto
    )

    try:
        caminho_relativo = (
            caminho_absoluto.relative_to(
                current_app.root_path
            )
        )

        caminho_banco = str(
            caminho_relativo
        )

    except ValueError:
        caminho_banco = str(
            caminho_absoluto
        )

    return {
        "nome_original": nome_original,
        "nome_salvo": nome_salvo,
        "caminho_absoluto": caminho_absoluto,
        "caminho_banco": caminho_banco,
    }


def remover_arquivo(caminho):
    if not caminho:
        return

    try:
        caminho = Path(caminho)

        if caminho.exists() and caminho.is_file():
            caminho.unlink()

    except OSError:
        current_app.logger.exception(
            "Não foi possível remover o arquivo: %s",
            caminho,
        )


@modelos_bp.route("/")
@login_required
def listar():
    termo = request.args.get(
        "q",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip().lower()

    consulta = ModeloDocumento.query

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                ModeloDocumento.nome.ilike(
                    busca
                ),
                ModeloDocumento.tipo_documento.ilike(
                    busca
                ),
                ModeloDocumento.categoria.ilike(
                    busca
                ),
                ModeloDocumento.area_juridica.ilike(
                    busca
                ),
                ModeloDocumento.descricao.ilike(
                    busca
                ),
                ModeloDocumento.observacoes_uso.ilike(
                    busca
                ),
            )
        )

    if status == "ativos":
        consulta = consulta.filter(
            ModeloDocumento.ativo.is_(True)
        )

    elif status == "inativos":
        consulta = consulta.filter(
            ModeloDocumento.ativo.is_(False)
        )

    modelos = consulta.order_by(
        ModeloDocumento.nome.asc(),
        ModeloDocumento.versao.desc(),
    ).all()

    return render_template(
        "modelos/listar.html",
        modelos=modelos,
        termo=termo,
        status=status,
    )


@modelos_bp.route(
    "/novo",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def novo():
    modelo = ModeloDocumento(
        ativo=True,
        versao="1.0",
    )

    if request.method == "POST":
        modelo.nome = request.form.get(
            "nome",
            "",
        ).strip()

        modelo.tipo_documento = (
            request.form.get(
                "tipo_documento",
                "",
            ).strip()
            or None
        )

        modelo.categoria = (
            request.form.get(
                "categoria",
                "",
            ).strip()
            or None
        )

        modelo.area_juridica = (
            request.form.get(
                "area_juridica",
                "",
            ).strip()
            or None
        )

        modelo.descricao = (
            request.form.get(
                "descricao",
                "",
            ).strip()
            or None
        )

        modelo.observacoes_uso = (
            request.form.get(
                "observacoes_uso",
                "",
            ).strip()
            or None
        )

        modelo.versao = (
            request.form.get(
                "versao",
                "",
            ).strip()
            or "1.0"
        )

        modelo.ativo = (
            request.form.get("ativo")
            == "on"
        )

        arquivo = request.files.get(
            "arquivo"
        )

        if not modelo.nome:
            flash(
                "Informe o nome do modelo.",
                "danger",
            )

            return render_template(
                "modelos/novo.html",
                modelo=modelo,
            )

        if not arquivo or not arquivo.filename:
            flash(
                "Selecione um arquivo DOCX.",
                "danger",
            )

            return render_template(
                "modelos/novo.html",
                modelo=modelo,
            )

        if not arquivo_permitido(
            arquivo.filename
        ):
            flash(
                "O arquivo precisa estar no formato DOCX.",
                "danger",
            )

            return render_template(
                "modelos/novo.html",
                modelo=modelo,
            )

        dados_arquivo = None

        try:
            dados_arquivo = salvar_arquivo_modelo(
                arquivo
            )

            variaveis = escanear_variaveis_docx(
                dados_arquivo[
                    "caminho_absoluto"
                ]
            )

            modelo.nome_arquivo = (
                dados_arquivo[
                    "nome_original"
                ]
            )

            modelo.caminho_arquivo = (
                dados_arquivo[
                    "caminho_banco"
                ]
            )

            modelo.criado_por_id = (
                current_user.id
            )

            modelo.definir_variaveis(
                variaveis
            )

            db.session.add(
                modelo
            )

            db.session.commit()

            quantidade = len(
                variaveis
            )

            if quantidade:
                flash(
                    (
                        "Modelo cadastrado com sucesso. "
                        f"{quantidade} variável(is) "
                        "encontrada(s)."
                    ),
                    "success",
                )
            else:
                flash(
                    (
                        "Modelo cadastrado com sucesso, "
                        "mas nenhuma variável foi encontrada."
                    ),
                    "warning",
                )

            return redirect(
                url_for(
                    "modelos.editar",
                    modelo_id=modelo.id,
                )
            )

        except ErroLeituraDocumento as erro:
            db.session.rollback()

            if dados_arquivo:
                remover_arquivo(
                    dados_arquivo[
                        "caminho_absoluto"
                    ]
                )

            flash(
                str(erro),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            if dados_arquivo:
                remover_arquivo(
                    dados_arquivo[
                        "caminho_absoluto"
                    ]
                )

            current_app.logger.exception(
                "Erro ao cadastrar modelo de documento."
            )

            flash(
                "Não foi possível cadastrar o modelo.",
                "danger",
            )

        except OSError:
            db.session.rollback()

            if dados_arquivo:
                remover_arquivo(
                    dados_arquivo[
                        "caminho_absoluto"
                    ]
                )

            current_app.logger.exception(
                "Erro ao salvar o arquivo do modelo."
            )

            flash(
                "Não foi possível salvar o arquivo.",
                "danger",
            )

    return render_template(
        "modelos/novo.html",
        modelo=modelo,
    )


@modelos_bp.route(
    "/<string:modelo_id>/editar",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def editar(modelo_id):
    modelo = ModeloDocumento.query.get_or_404(
        modelo_id
    )

    if request.method == "POST":
        nome = request.form.get(
            "nome",
            "",
        ).strip()

        if not nome:
            flash(
                "Informe o nome do modelo.",
                "danger",
            )

            return render_template(
                "modelos/editar.html",
                modelo=modelo,
            )

        modelo.nome = nome

        modelo.tipo_documento = (
            request.form.get(
                "tipo_documento",
                "",
            ).strip()
            or None
        )

        modelo.categoria = (
            request.form.get(
                "categoria",
                "",
            ).strip()
            or None
        )

        modelo.area_juridica = (
            request.form.get(
                "area_juridica",
                "",
            ).strip()
            or None
        )

        modelo.descricao = (
            request.form.get(
                "descricao",
                "",
            ).strip()
            or None
        )

        modelo.observacoes_uso = (
            request.form.get(
                "observacoes_uso",
                "",
            ).strip()
            or None
        )

        modelo.versao = (
            request.form.get(
                "versao",
                "",
            ).strip()
            or "1.0"
        )

        modelo.ativo = (
            request.form.get("ativo")
            == "on"
        )

        arquivo = request.files.get(
            "arquivo"
        )

        arquivo_antigo = obter_caminho_modelo(
            modelo
        )

        dados_novo_arquivo = None

        try:
            if arquivo and arquivo.filename:
                if not arquivo_permitido(
                    arquivo.filename
                ):
                    flash(
                        (
                            "O novo arquivo precisa estar "
                            "no formato DOCX."
                        ),
                        "danger",
                    )

                    return render_template(
                        "modelos/editar.html",
                        modelo=modelo,
                    )

                dados_novo_arquivo = (
                    salvar_arquivo_modelo(
                        arquivo
                    )
                )

                variaveis = (
                    escanear_variaveis_docx(
                        dados_novo_arquivo[
                            "caminho_absoluto"
                        ]
                    )
                )

                modelo.nome_arquivo = (
                    dados_novo_arquivo[
                        "nome_original"
                    ]
                )

                modelo.caminho_arquivo = (
                    dados_novo_arquivo[
                        "caminho_banco"
                    ]
                )

                modelo.definir_variaveis(
                    variaveis
                )

            db.session.commit()

            if (
                dados_novo_arquivo
                and arquivo_antigo
                != dados_novo_arquivo[
                    "caminho_absoluto"
                ]
            ):
                remover_arquivo(
                    arquivo_antigo
                )

            flash(
                "Modelo atualizado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "modelos.editar",
                    modelo_id=modelo.id,
                )
            )

        except ErroLeituraDocumento as erro:
            db.session.rollback()

            if dados_novo_arquivo:
                remover_arquivo(
                    dados_novo_arquivo[
                        "caminho_absoluto"
                    ]
                )

            flash(
                str(erro),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            if dados_novo_arquivo:
                remover_arquivo(
                    dados_novo_arquivo[
                        "caminho_absoluto"
                    ]
                )

            current_app.logger.exception(
                "Erro ao atualizar modelo de documento."
            )

            flash(
                "Não foi possível atualizar o modelo.",
                "danger",
            )

        except OSError:
            db.session.rollback()

            if dados_novo_arquivo:
                remover_arquivo(
                    dados_novo_arquivo[
                        "caminho_absoluto"
                    ]
                )

            current_app.logger.exception(
                "Erro ao substituir arquivo do modelo."
            )

            flash(
                "Não foi possível salvar o novo arquivo.",
                "danger",
            )

    return render_template(
        "modelos/editar.html",
        modelo=modelo,
    )


@modelos_bp.route(
    "/<string:modelo_id>/download"
)
@login_required
def download(modelo_id):
    modelo = ModeloDocumento.query.get_or_404(
        modelo_id
    )

    caminho = obter_caminho_modelo(
        modelo
    )

    if not caminho.exists():
        flash(
            "O arquivo deste modelo não foi encontrado.",
            "danger",
        )

        return redirect(
            url_for(
                "modelos.listar"
            )
        )

    return send_file(
        caminho,
        as_attachment=True,
        download_name=modelo.nome_arquivo,
    )


@modelos_bp.route(
    "/<string:modelo_id>/alternar-status",
    methods=[
        "POST",
    ],
)
@login_required
def alternar_status(modelo_id):
    modelo = ModeloDocumento.query.get_or_404(
        modelo_id
    )

    try:
        modelo.ativo = not modelo.ativo

        db.session.commit()

        flash(
            (
                "Modelo ativado com sucesso."
                if modelo.ativo
                else "Modelo desativado com sucesso."
            ),
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao alterar status do modelo."
        )

        flash(
            "Não foi possível alterar o status.",
            "danger",
        )

    return redirect(
        request.referrer
        or url_for(
            "modelos.listar"
        )
    )


@modelos_bp.route(
    "/<string:modelo_id>/excluir",
    methods=[
        "POST",
    ],
)
@login_required
def excluir(modelo_id):
    modelo = ModeloDocumento.query.get_or_404(
        modelo_id
    )

    caminho = obter_caminho_modelo(
        modelo
    )

    try:
        db.session.delete(
            modelo
        )

        db.session.commit()

        remover_arquivo(
            caminho
        )

        flash(
            "Modelo excluído com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao excluir modelo de documento."
        )

        flash(
            "Não foi possível excluir o modelo.",
            "danger",
        )

    return redirect(
        url_for(
            "modelos.listar"
        )
    )