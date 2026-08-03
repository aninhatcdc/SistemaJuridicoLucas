import re
import unicodedata

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import db
from models.area_juridica import AreaJuridica
from models.formulario_modelo import FormularioModelo


formularios_bp = Blueprint(
    "formularios",
    __name__,
    url_prefix="/formularios",
)


def gerar_codigo(texto):
    """
    Converte o nome informado em um código padronizado.

    Exemplo:
        Entrevista Trabalhista
        entrevista_trabalhista
    """
    texto = texto or ""

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = texto.lower().strip()

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


def normalizar_codigo(codigo, nome):
    """
    Usa o código digitado pelo usuário.

    Caso esteja vazio, gera automaticamente a partir do nome.
    """
    codigo = gerar_codigo(codigo)

    if codigo:
        return codigo

    return gerar_codigo(nome)


def codigo_em_uso(codigo, formulario_id=None):
    consulta = FormularioModelo.query.filter(
        FormularioModelo.codigo == codigo
    )

    if formulario_id:
        consulta = consulta.filter(
            FormularioModelo.id != formulario_id
        )

    return consulta.first() is not None


def carregar_areas_juridicas():
    return (
        AreaJuridica.query
        .filter(
            AreaJuridica.ativa.is_(True)
        )
        .order_by(
            AreaJuridica.ordem.asc(),
            AreaJuridica.nome.asc(),
        )
        .all()
    )


def preencher_formulario_modelo(formulario):
    formulario.nome = request.form.get(
        "nome",
        "",
    ).strip()

    formulario.codigo = normalizar_codigo(
        request.form.get(
            "codigo",
            "",
        ),
        formulario.nome,
    )

    formulario.descricao = (
        request.form.get(
            "descricao",
            "",
        ).strip()
        or None
    )

    formulario.area_juridica_id = (
        request.form.get(
            "area_juridica_id",
            "",
        ).strip()
        or None
    )

    try:
        formulario.versao = int(
            request.form.get(
                "versao",
                "1",
            )
            or 1
        )
    except (TypeError, ValueError):
        formulario.versao = 1

    if formulario.versao < 1:
        formulario.versao = 1

    formulario.ativo = (
        request.form.get("ativo")
        == "on"
    )


def validar_formulario(formulario, formulario_id=None):
    if not formulario.nome:
        return "Informe o nome do formulário."

    if not formulario.codigo:
        return "Informe um código válido para o formulário."

    if len(formulario.codigo) > 100:
        return "O código deve possuir no máximo 100 caracteres."

    if codigo_em_uso(
        formulario.codigo,
        formulario_id,
    ):
        return (
            "Já existe um modelo de formulário "
            "cadastrado com esse código."
        )

    if formulario.area_juridica_id:
        area = db.session.get(
            AreaJuridica,
            formulario.area_juridica_id,
        )

        if not area:
            return "A área jurídica selecionada não foi encontrada."

    return None


@formularios_bp.route("/")
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

    area_juridica_id = request.args.get(
        "area_juridica_id",
        "",
    ).strip()

    consulta = FormularioModelo.query

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                FormularioModelo.nome.ilike(
                    busca
                ),
                FormularioModelo.codigo.ilike(
                    busca
                ),
                FormularioModelo.descricao.ilike(
                    busca
                ),
            )
        )

    if status == "ativos":
        consulta = consulta.filter(
            FormularioModelo.ativo.is_(True)
        )

    elif status == "inativos":
        consulta = consulta.filter(
            FormularioModelo.ativo.is_(False)
        )

    if area_juridica_id:
        consulta = consulta.filter(
            FormularioModelo.area_juridica_id
            == area_juridica_id
        )

    formularios = consulta.order_by(
        FormularioModelo.nome.asc(),
        FormularioModelo.versao.desc(),
    ).all()

    areas_juridicas = carregar_areas_juridicas()

    return render_template(
        "formularios/listar.html",
        formularios=formularios,
        areas_juridicas=areas_juridicas,
        termo=termo,
        status=status,
        area_juridica_id=area_juridica_id,
    )


@formularios_bp.route(
    "/novo",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def novo():
    formulario = FormularioModelo(
        ativo=True,
        versao=1,
    )

    areas_juridicas = carregar_areas_juridicas()

    if request.method == "POST":
        preencher_formulario_modelo(
            formulario
        )

        erro = validar_formulario(
            formulario
        )

        if erro:
            flash(
                erro,
                "danger",
            )

            return render_template(
                "formularios/novo.html",
                formulario=formulario,
                areas_juridicas=areas_juridicas,
            )

        try:
            db.session.add(
                formulario
            )

            db.session.commit()

            flash(
                "Modelo de formulário cadastrado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "formularios.editar",
                    formulario_id=formulario.id,
                )
            )

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Não foi possível cadastrar o formulário. "
                    "Verifique se o código informado já está em uso."
                ),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Erro ao cadastrar modelo de formulário."
            )

            flash(
                "Não foi possível cadastrar o formulário.",
                "danger",
            )

    return render_template(
        "formularios/novo.html",
        formulario=formulario,
        areas_juridicas=areas_juridicas,
    )


@formularios_bp.route(
    "/<string:formulario_id>/editar",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def editar(formulario_id):
    formulario = (
        FormularioModelo.query
        .get_or_404(
            formulario_id
        )
    )

    areas_juridicas = carregar_areas_juridicas()

    if request.method == "POST":
        preencher_formulario_modelo(
            formulario
        )

        erro = validar_formulario(
            formulario,
            formulario_id=formulario.id,
        )

        if erro:
            flash(
                erro,
                "danger",
            )

            return render_template(
                "formularios/editar.html",
                formulario=formulario,
                areas_juridicas=areas_juridicas,
            )

        try:
            db.session.commit()

            flash(
                "Modelo de formulário atualizado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "formularios.editar",
                    formulario_id=formulario.id,
                )
            )

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Não foi possível atualizar o formulário. "
                    "Verifique se o código informado já está em uso."
                ),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Erro ao atualizar modelo de formulário."
            )

            flash(
                "Não foi possível atualizar o formulário.",
                "danger",
            )

    return render_template(
        "formularios/editar.html",
        formulario=formulario,
        areas_juridicas=areas_juridicas,
    )


@formularios_bp.route(
    "/<string:formulario_id>/alternar-status",
    methods=[
        "POST",
    ],
)
@login_required
def alternar_status(formulario_id):
    formulario = (
        FormularioModelo.query
        .get_or_404(
            formulario_id
        )
    )

    try:
        formulario.ativo = not formulario.ativo

        db.session.commit()

        flash(
            (
                "Modelo de formulário ativado com sucesso."
                if formulario.ativo
                else "Modelo de formulário desativado com sucesso."
            ),
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao alterar status do modelo de formulário."
        )

        flash(
            "Não foi possível alterar o status do formulário.",
            "danger",
        )

    return redirect(
        request.referrer
        or url_for(
            "formularios.listar"
        )
    )


@formularios_bp.route(
    "/<string:formulario_id>/excluir",
    methods=[
        "POST",
    ],
)
@login_required
def excluir(formulario_id):
    formulario = (
        FormularioModelo.query
        .get_or_404(
            formulario_id
        )
    )

    if formulario.formularios_preenchidos:
        flash(
            (
                "Este modelo não pode ser excluído porque já possui "
                "formulários preenchidos ou iniciados. "
                "Desative o modelo para impedir novos preenchimentos."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "formularios.listar"
            )
        )

    try:
        db.session.delete(
            formulario
        )

        db.session.commit()

        flash(
            "Modelo de formulário excluído com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao excluir modelo de formulário."
        )

        flash(
            "Não foi possível excluir o formulário.",
            "danger",
        )

    return redirect(
        url_for(
            "formularios.listar"
        )
    )