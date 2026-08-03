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
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from models import db
from models.formulario_modelo import FormularioModelo
from models.pergunta_formulario import PerguntaFormulario


perguntas_formulario_bp = Blueprint(
    "perguntas_formulario",
    __name__,
    url_prefix="/formularios/<string:formulario_id>/perguntas",
)


TIPOS_COM_OPCOES = {
    "SELECAO",
    "MULTIPLA_SELECAO",
}


def gerar_codigo(texto):
    texto = texto or ""

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = texto.lower().strip()

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


def normalizar_opcoes(texto):
    if not texto:
        return []

    valores = []

    for linha in texto.splitlines():
        valor = linha.strip()

        if valor and valor not in valores:
            valores.append(
                valor
            )

    return valores


def obter_formulario(formulario_id):
    return (
        FormularioModelo.query
        .get_or_404(
            formulario_id
        )
    )


def obter_pergunta(
    formulario_id,
    pergunta_id,
):
    return (
        PerguntaFormulario.query
        .filter_by(
            id=pergunta_id,
            formulario_modelo_id=formulario_id,
        )
        .first_or_404()
    )


def proxima_ordem(formulario_id):
    ultima = (
        PerguntaFormulario.query
        .filter_by(
            formulario_modelo_id=formulario_id
        )
        .order_by(
            PerguntaFormulario.ordem.desc()
        )
        .first()
    )

    if not ultima:
        return 1

    return ultima.ordem + 1


def preencher_pergunta(
    pergunta,
    formulario_id,
):
    pergunta.texto = request.form.get(
        "texto",
        "",
    ).strip()

    codigo_informado = request.form.get(
        "codigo",
        "",
    ).strip()

    pergunta.codigo = gerar_codigo(
        codigo_informado
        or pergunta.texto
    )

    pergunta.descricao = (
        request.form.get(
            "descricao",
            "",
        ).strip()
        or None
    )

    pergunta.tipo = (
        request.form.get(
            "tipo",
            "TEXTO",
        ).strip()
        or "TEXTO"
    )

    pergunta.placeholder = (
        request.form.get(
            "placeholder",
            "",
        ).strip()
        or None
    )

    pergunta.valor_padrao = (
        request.form.get(
            "valor_padrao",
            "",
        ).strip()
        or None
    )

    pergunta.etapa = (
        request.form.get(
            "etapa",
            "Geral",
        ).strip()
        or "Geral"
    )

    pergunta.grupo = (
        request.form.get(
            "grupo",
            "",
        ).strip()
        or None
    )

    pergunta.icone = (
        request.form.get(
            "icone",
            "📄",
        ).strip()
        or "📄"
    )

    pergunta.descricao_etapa = (
        request.form.get(
            "descricao_etapa",
            "",
        ).strip()
        or None
    )

    try:
        pergunta.ordem = int(
            request.form.get(
                "ordem",
                "0",
            )
            or 0
        )
    except (TypeError, ValueError):
        pergunta.ordem = 0

    if pergunta.ordem < 0:
        pergunta.ordem = 0

    try:
        pergunta.ordem_etapa = int(
            request.form.get(
                "ordem_etapa",
                "1",
            )
            or 1
        )
    except (TypeError, ValueError):
        pergunta.ordem_etapa = 1

    if pergunta.ordem_etapa < 1:
        pergunta.ordem_etapa = 1

    pergunta.obrigatoria = (
        request.form.get(
            "obrigatoria"
        )
        == "on"
    )

    pergunta.ativo = (
        request.form.get(
            "ativo"
        )
        == "on"
    )

    pergunta.formulario_modelo_id = (
        formulario_id
    )

    opcoes_texto = request.form.get(
        "opcoes",
        "",
    )

    if pergunta.tipo in TIPOS_COM_OPCOES:
        pergunta.opcoes = normalizar_opcoes(
            opcoes_texto
        )
    else:
        pergunta.opcoes = []


def codigo_em_uso(
    formulario_id,
    codigo,
    pergunta_id=None,
):
    consulta = (
        PerguntaFormulario.query
        .filter(
            PerguntaFormulario.formulario_modelo_id
            == formulario_id,
            PerguntaFormulario.codigo
            == codigo,
        )
    )

    if pergunta_id:
        consulta = consulta.filter(
            PerguntaFormulario.id
            != pergunta_id
        )

    return consulta.first() is not None


def validar_pergunta(
    pergunta,
    pergunta_id=None,
):
    if not pergunta.texto:
        return "Informe o texto da pergunta."

    if len(pergunta.texto) > 500:
        return (
            "O texto da pergunta deve possuir "
            "no máximo 500 caracteres."
        )

    if not pergunta.codigo:
        return "Informe um código válido para a pergunta."

    if len(pergunta.codigo) > 100:
        return (
            "O código deve possuir no máximo "
            "100 caracteres."
        )

    if pergunta.tipo not in PerguntaFormulario.TIPOS:
        return "O tipo de pergunta selecionado é inválido."

    if not pergunta.etapa:
        return "Informe o nome da etapa."

    if len(pergunta.etapa) > 100:
        return "O nome da etapa deve possuir no máximo 100 caracteres."

    if pergunta.ordem_etapa < 1:
        return "A ordem da etapa deve ser igual ou maior que 1."

    if pergunta.grupo and len(pergunta.grupo) > 100:
        return "O grupo deve possuir no máximo 100 caracteres."

    if pergunta.icone and len(pergunta.icone) > 30:
        return "O ícone deve possuir no máximo 30 caracteres."

    if (
        pergunta.descricao_etapa
        and len(pergunta.descricao_etapa) > 255
    ):
        return (
            "A descrição da etapa deve possuir "
            "no máximo 255 caracteres."
        )

    if codigo_em_uso(
        pergunta.formulario_modelo_id,
        pergunta.codigo,
        pergunta_id,
    ):
        return (
            "Já existe uma pergunta com esse código "
            "neste formulário."
        )

    if (
        pergunta.tipo in TIPOS_COM_OPCOES
        and not pergunta.opcoes
    ):
        return (
            "Informe pelo menos uma opção para "
            "esse tipo de pergunta."
        )

    return None


def obter_opcoes_texto(pergunta):
    return "\n".join(
        str(valor)
        for valor in pergunta.opcoes
    )


@perguntas_formulario_bp.route("/")
@login_required
def listar(formulario_id):
    formulario = obter_formulario(
        formulario_id
    )

    perguntas = (
        PerguntaFormulario.query
        .filter_by(
            formulario_modelo_id=formulario.id
        )
        .order_by(
            PerguntaFormulario.ordem_etapa.asc(),
            PerguntaFormulario.etapa.asc(),
            PerguntaFormulario.ordem.asc(),
            PerguntaFormulario.criado_em.asc(),
        )
        .all()
    )

    return render_template(
        "perguntas_formulario/listar.html",
        formulario=formulario,
        perguntas=perguntas,
    )


@perguntas_formulario_bp.route(
    "/nova",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def nova(formulario_id):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = PerguntaFormulario(
        formulario_modelo_id=formulario.id,
        tipo="TEXTO",
        ordem=proxima_ordem(
            formulario.id
        ),
        etapa="Geral",
        ordem_etapa=1,
        icone="📄",
        obrigatoria=False,
        ativo=True,
    )

    opcoes_texto = ""

    if request.method == "POST":
        preencher_pergunta(
            pergunta,
            formulario.id,
        )

        opcoes_texto = request.form.get(
            "opcoes",
            "",
        )

        erro = validar_pergunta(
            pergunta
        )

        if erro:
            flash(
                erro,
                "danger",
            )

            return render_template(
                "perguntas_formulario/novo.html",
                formulario=formulario,
                pergunta=pergunta,
                tipos=PerguntaFormulario.TIPOS,
                opcoes_texto=opcoes_texto,
            )

        try:
            db.session.add(
                pergunta
            )

            db.session.commit()

            flash(
                "Pergunta cadastrada com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "perguntas_formulario.listar",
                    formulario_id=formulario.id,
                )
            )

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Não foi possível cadastrar a pergunta. "
                    "Verifique se o código já está em uso."
                ),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Erro ao cadastrar pergunta de formulário."
            )

            flash(
                "Não foi possível cadastrar a pergunta.",
                "danger",
            )

    return render_template(
        "perguntas_formulario/novo.html",
        formulario=formulario,
        pergunta=pergunta,
        tipos=PerguntaFormulario.TIPOS,
        opcoes_texto=opcoes_texto,
    )


@perguntas_formulario_bp.route(
    "/<string:pergunta_id>/editar",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def editar(
    formulario_id,
    pergunta_id,
):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = obter_pergunta(
        formulario.id,
        pergunta_id,
    )

    opcoes_texto = obter_opcoes_texto(
        pergunta
    )

    if request.method == "POST":
        preencher_pergunta(
            pergunta,
            formulario.id,
        )

        opcoes_texto = request.form.get(
            "opcoes",
            "",
        )

        erro = validar_pergunta(
            pergunta,
            pergunta_id=pergunta.id,
        )

        if erro:
            flash(
                erro,
                "danger",
            )

            return render_template(
                "perguntas_formulario/editar.html",
                formulario=formulario,
                pergunta=pergunta,
                tipos=PerguntaFormulario.TIPOS,
                opcoes_texto=opcoes_texto,
            )

        try:
            db.session.commit()

            flash(
                "Pergunta atualizada com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "perguntas_formulario.listar",
                    formulario_id=formulario.id,
                )
            )

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Não foi possível atualizar a pergunta. "
                    "Verifique se o código já está em uso."
                ),
                "danger",
            )

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Erro ao atualizar pergunta de formulário."
            )

            flash(
                "Não foi possível atualizar a pergunta.",
                "danger",
            )

    return render_template(
        "perguntas_formulario/editar.html",
        formulario=formulario,
        pergunta=pergunta,
        tipos=PerguntaFormulario.TIPOS,
        opcoes_texto=opcoes_texto,
    )


@perguntas_formulario_bp.route(
    "/<string:pergunta_id>/alternar-status",
    methods=[
        "POST",
    ],
)
@login_required
def alternar_status(
    formulario_id,
    pergunta_id,
):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = obter_pergunta(
        formulario.id,
        pergunta_id,
    )

    try:
        pergunta.ativo = not pergunta.ativo

        db.session.commit()

        flash(
            (
                "Pergunta ativada com sucesso."
                if pergunta.ativo
                else "Pergunta desativada com sucesso."
            ),
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao alterar status da pergunta."
        )

        flash(
            "Não foi possível alterar o status da pergunta.",
            "danger",
        )

    return redirect(
        url_for(
            "perguntas_formulario.listar",
            formulario_id=formulario.id,
        )
    )


@perguntas_formulario_bp.route(
    "/<string:pergunta_id>/mover-cima",
    methods=[
        "POST",
    ],
)
@login_required
def mover_cima(
    formulario_id,
    pergunta_id,
):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = obter_pergunta(
        formulario.id,
        pergunta_id,
    )

    anterior = (
        PerguntaFormulario.query
        .filter(
            PerguntaFormulario.formulario_modelo_id
            == formulario.id,
            PerguntaFormulario.etapa
            == pergunta.etapa,
            PerguntaFormulario.ordem_etapa
            == pergunta.ordem_etapa,
            PerguntaFormulario.ordem
            < pergunta.ordem,
        )
        .order_by(
            PerguntaFormulario.ordem.desc()
        )
        .first()
    )

    if not anterior:
        return redirect(
            url_for(
                "perguntas_formulario.listar",
                formulario_id=formulario.id,
            )
        )

    try:
        ordem_atual = pergunta.ordem

        pergunta.ordem = anterior.ordem
        anterior.ordem = ordem_atual

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao mover pergunta para cima."
        )

        flash(
            "Não foi possível alterar a ordem da pergunta.",
            "danger",
        )

    return redirect(
        url_for(
            "perguntas_formulario.listar",
            formulario_id=formulario.id,
        )
    )


@perguntas_formulario_bp.route(
    "/<string:pergunta_id>/mover-baixo",
    methods=[
        "POST",
    ],
)
@login_required
def mover_baixo(
    formulario_id,
    pergunta_id,
):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = obter_pergunta(
        formulario.id,
        pergunta_id,
    )

    proxima = (
        PerguntaFormulario.query
        .filter(
            PerguntaFormulario.formulario_modelo_id
            == formulario.id,
            PerguntaFormulario.etapa
            == pergunta.etapa,
            PerguntaFormulario.ordem_etapa
            == pergunta.ordem_etapa,
            PerguntaFormulario.ordem
            > pergunta.ordem,
        )
        .order_by(
            PerguntaFormulario.ordem.asc()
        )
        .first()
    )

    if not proxima:
        return redirect(
            url_for(
                "perguntas_formulario.listar",
                formulario_id=formulario.id,
            )
        )

    try:
        ordem_atual = pergunta.ordem

        pergunta.ordem = proxima.ordem
        proxima.ordem = ordem_atual

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao mover pergunta para baixo."
        )

        flash(
            "Não foi possível alterar a ordem da pergunta.",
            "danger",
        )

    return redirect(
        url_for(
            "perguntas_formulario.listar",
            formulario_id=formulario.id,
        )
    )


@perguntas_formulario_bp.route(
    "/<string:pergunta_id>/excluir",
    methods=[
        "POST",
    ],
)
@login_required
def excluir(
    formulario_id,
    pergunta_id,
):
    formulario = obter_formulario(
        formulario_id
    )

    pergunta = obter_pergunta(
        formulario.id,
        pergunta_id,
    )

    if pergunta.respostas:
        flash(
            (
                "Esta pergunta não pode ser excluída porque "
                "já possui respostas registradas. "
                "Desative a pergunta para impedir novos preenchimentos."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "perguntas_formulario.listar",
                formulario_id=formulario.id,
            )
        )

    try:
        db.session.delete(
            pergunta
        )

        db.session.commit()

        flash(
            "Pergunta excluída com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao excluir pergunta de formulário."
        )

        flash(
            "Não foi possível excluir a pergunta.",
            "danger",
        )

    return redirect(
        url_for(
            "perguntas_formulario.listar",
            formulario_id=formulario.id,
        )
    )