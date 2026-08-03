from collections import OrderedDict
from datetime import date, time
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from models import db
from models.caso import Caso
from models.formulario_caso import FormularioCaso
from models.formulario_modelo import FormularioModelo
from models.pergunta_formulario import PerguntaFormulario
from models.resposta_formulario import RespostaFormulario


formularios_caso_bp = Blueprint(
    "formularios_caso",
    __name__,
    url_prefix="/casos/<string:caso_id>/formularios",
)


TIPOS_TEXTO = {
    "TEXTO",
    "TEXTO_LONGO",
    "EMAIL",
    "TELEFONE",
    "CPF",
    "CNPJ",
    "SELECAO",
}

TIPOS_NUMERICOS = {
    "NUMERO",
    "MOEDA",
}


def obter_caso(caso_id):
    return db.get_or_404(
        Caso,
        caso_id,
    )


def obter_formulario_caso(
    caso_id,
    formulario_caso_id,
):
    return (
        FormularioCaso.query
        .filter_by(
            id=formulario_caso_id,
            caso_id=caso_id,
        )
        .first_or_404()
    )


def modelo_compativel_com_caso(
    modelo,
    caso,
):
    if not modelo.ativo:
        return False

    if modelo.area_juridica_id is None:
        return True

    return (
        modelo.area_juridica_id
        == caso.area_juridica_id
    )


def obter_modelos_disponiveis(caso):
    return (
        FormularioModelo.query
        .filter(
            FormularioModelo.ativo.is_(True),
            db.or_(
                FormularioModelo.area_juridica_id.is_(None),
                FormularioModelo.area_juridica_id
                == caso.area_juridica_id,
            ),
        )
        .order_by(
            FormularioModelo.nome.asc()
        )
        .all()
    )


def montar_respostas_por_pergunta(
    formulario_caso,
):
    return {
        resposta.pergunta_id: resposta
        for resposta in formulario_caso.respostas
        if resposta.pergunta_id
    }


def valor_esta_preenchido(valor):
    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    if isinstance(valor, list):
        return bool(valor)

    return True


def normalizar_decimal(valor):
    valor = (
        valor
        or ""
    ).strip()

    if not valor:
        return None

    valor = (
        valor
        .replace("R$", "")
        .replace(" ", "")
    )

    if "," in valor:
        valor = (
            valor
            .replace(".", "")
            .replace(",", ".")
        )

    try:
        return Decimal(valor)
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "Informe um número válido."
        )


def obter_valor_enviado(pergunta):
    nome_campo = f"pergunta_{pergunta.id}"

    if pergunta.tipo == "MULTIPLA_SELECAO":
        return [
            valor.strip()
            for valor in request.form.getlist(
                nome_campo
            )
            if valor.strip()
        ]

    valor = request.form.get(
        nome_campo,
        "",
    )

    if isinstance(valor, str):
        return valor.strip()

    return valor


def validar_opcoes(
    pergunta,
    valor,
):
    opcoes_validas = {
        str(opcao)
        for opcao in pergunta.opcoes
    }

    if pergunta.tipo == "SELECAO":
        if (
            valor
            and valor not in opcoes_validas
        ):
            raise ValueError(
                "A opção selecionada é inválida."
            )

    if pergunta.tipo == "MULTIPLA_SELECAO":
        valores_invalidos = [
            item
            for item in valor
            if item not in opcoes_validas
        ]

        if valores_invalidos:
            raise ValueError(
                "Uma ou mais opções selecionadas são inválidas."
            )


def converter_valor(
    pergunta,
    valor_enviado,
):
    tipo = pergunta.tipo

    if tipo in TIPOS_TEXTO:
        if not valor_enviado:
            return None

        validar_opcoes(
            pergunta,
            valor_enviado,
        )

        return valor_enviado

    if tipo in TIPOS_NUMERICOS:
        return normalizar_decimal(
            valor_enviado
        )

    if tipo == "DATA":
        if not valor_enviado:
            return None

        try:
            return date.fromisoformat(
                valor_enviado
            )
        except ValueError:
            raise ValueError(
                "Informe uma data válida."
            )

    if tipo == "HORA":
        if not valor_enviado:
            return None

        try:
            return time.fromisoformat(
                valor_enviado
            )
        except ValueError:
            raise ValueError(
                "Informe um horário válido."
            )

    if tipo == "SIM_NAO":
        if valor_enviado == "":
            return None

        if valor_enviado == "SIM":
            return True

        if valor_enviado == "NAO":
            return False

        raise ValueError(
            "Selecione Sim ou Não."
        )

    if tipo == "MULTIPLA_SELECAO":
        validar_opcoes(
            pergunta,
            valor_enviado,
        )

        return valor_enviado or []

    return (
        valor_enviado
        if valor_enviado
        else None
    )


def aplicar_valor_na_resposta(
    resposta,
    pergunta,
    valor,
):
    resposta.limpar_valores()

    if pergunta.tipo in TIPOS_TEXTO:
        resposta.valor_texto = valor
        return

    if pergunta.tipo in TIPOS_NUMERICOS:
        resposta.valor_numero = valor
        return

    if pergunta.tipo == "DATA":
        resposta.valor_data = valor
        return

    if pergunta.tipo == "HORA":
        resposta.valor_hora = valor
        return

    if pergunta.tipo == "SIM_NAO":
        resposta.valor_booleano = valor
        return

    if pergunta.tipo == "MULTIPLA_SELECAO":
        resposta.valor_lista = valor
        return

    resposta.valor_texto = (
        str(valor)
        if valor is not None
        else None
    )


def salvar_respostas(
    formulario_caso,
    concluir=False,
):
    perguntas = (
        PerguntaFormulario.query
        .filter_by(
            formulario_modelo_id=(
                formulario_caso.formulario_modelo_id
            ),
            ativo=True,
        )
        .order_by(
            PerguntaFormulario.ordem.asc(),
            PerguntaFormulario.criado_em.asc(),
        )
        .all()
    )

    respostas_existentes = (
        montar_respostas_por_pergunta(
            formulario_caso
        )
    )

    erros = []
    valores_convertidos = {}

    for pergunta in perguntas:
        valor_enviado = obter_valor_enviado(
            pergunta
        )

        try:
            valor_convertido = converter_valor(
                pergunta,
                valor_enviado,
            )

        except ValueError as erro:
            erros.append(
                f"{pergunta.texto}: {erro}"
            )
            continue

        valores_convertidos[
            pergunta.id
        ] = valor_convertido

        if (
            concluir
            and pergunta.obrigatoria
            and not valor_esta_preenchido(
                valor_convertido
            )
        ):
            erros.append(
                (
                    f'A pergunta "{pergunta.texto}" '
                    "é obrigatória."
                )
            )

    if erros:
        return erros

    for pergunta in perguntas:
        valor = valores_convertidos.get(
            pergunta.id
        )

        resposta = respostas_existentes.get(
            pergunta.id
        )

        preenchido = valor_esta_preenchido(
            valor
        )

        if not preenchido:
            if resposta:
                db.session.delete(
                    resposta
                )

            continue

        if not resposta:
            resposta = RespostaFormulario(
                formulario_caso_id=(
                    formulario_caso.id
                ),
                pergunta_id=pergunta.id,
            )

            db.session.add(
                resposta
            )

        aplicar_valor_na_resposta(
            resposta,
            pergunta,
            valor,
        )

    formulario_caso.observacoes = (
        request.form.get(
            "observacoes",
            "",
        ).strip()
        or None
    )

    if concluir:
        formulario_caso.concluir()
    else:
        formulario_caso.reabrir()

    return []


@formularios_caso_bp.route("/")
@login_required
def listar(caso_id):
    caso = obter_caso(
        caso_id
    )

    formularios = (
        FormularioCaso.query
        .filter_by(
            caso_id=caso.id
        )
        .order_by(
            FormularioCaso.criado_em.desc()
        )
        .all()
    )

    return render_template(
        "formularios_caso/listar.html",
        caso=caso,
        formularios=formularios,
    )


@formularios_caso_bp.route(
    "/selecionar",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def selecionar(caso_id):
    caso = obter_caso(
        caso_id
    )

    modelos = obter_modelos_disponiveis(
        caso
    )

    if request.method == "POST":
        modelo_id = request.form.get(
            "modelo_id",
            "",
        ).strip()

        modelo = db.session.get(
            FormularioModelo,
            modelo_id,
        )

        if not modelo:
            flash(
                "O formulário selecionado não foi encontrado.",
                "danger",
            )

        elif not modelo_compativel_com_caso(
            modelo,
            caso,
        ):
            flash(
                (
                    "O formulário selecionado não está ativo "
                    "ou não pertence à área jurídica deste caso."
                ),
                "danger",
            )

        elif not any(
            pergunta.ativo
            for pergunta in modelo.perguntas
        ):
            flash(
                (
                    "O modelo selecionado não possui "
                    "perguntas ativas."
                ),
                "warning",
            )

        else:
            formulario_caso = FormularioCaso(
                titulo=modelo.nome,
                status="RASCUNHO",
                versao_modelo=modelo.versao,
                formulario_modelo_id=modelo.id,
                caso_id=caso.id,
                cliente_id=caso.cliente_id,
                usuario_id=current_user.id,
            )

            try:
                db.session.add(
                    formulario_caso
                )

                db.session.commit()

                flash(
                    (
                        f'Formulário "{modelo.nome}" '
                        "iniciado com sucesso."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "formularios_caso.preencher",
                        caso_id=caso.id,
                        formulario_caso_id=(
                            formulario_caso.id
                        ),
                    )
                )

            except SQLAlchemyError:
                db.session.rollback()

                current_app.logger.exception(
                    "Erro ao iniciar formulário do caso."
                )

                flash(
                    "Não foi possível iniciar o formulário.",
                    "danger",
                )

    return render_template(
        "formularios_caso/selecionar.html",
        caso=caso,
        modelos=modelos,
    )


@formularios_caso_bp.route(
    "/<string:formulario_caso_id>/preencher",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def preencher(
    caso_id,
    formulario_caso_id,
):
    caso = obter_caso(
        caso_id
    )

    formulario_caso = obter_formulario_caso(
        caso.id,
        formulario_caso_id,
    )

    if formulario_caso.status == "CANCELADO":
        flash(
            (
                "Este formulário está cancelado e "
                "não pode ser alterado."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "formularios_caso.visualizar",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )

    perguntas = (
        PerguntaFormulario.query
        .filter_by(
            formulario_modelo_id=(
                formulario_caso.formulario_modelo_id
            ),
            ativo=True,
        )
        .order_by(
            PerguntaFormulario.ordem.asc(),
            PerguntaFormulario.criado_em.asc(),
        )
        .all()
    )

    if request.method == "POST":
        acao = request.form.get(
            "acao",
            "salvar",
        )

        concluir = (
            acao == "concluir"
        )

        erros = salvar_respostas(
            formulario_caso,
            concluir=concluir,
        )

        if erros:
            for erro in erros:
                flash(
                    erro,
                    "danger",
                )

        else:
            try:
                db.session.commit()

                if concluir:
                    flash(
                        "Formulário concluído com sucesso.",
                        "success",
                    )

                    return redirect(
                        url_for(
                            "formularios_caso.visualizar",
                            caso_id=caso.id,
                            formulario_caso_id=(
                                formulario_caso.id
                            ),
                        )
                    )

                flash(
                    "Rascunho salvo com sucesso.",
                    "success",
                )

                return redirect(
                    url_for(
                        "formularios_caso.preencher",
                        caso_id=caso.id,
                        formulario_caso_id=(
                            formulario_caso.id
                        ),
                    )
                )

            except IntegrityError:
                db.session.rollback()

                current_app.logger.exception(
                    (
                        "Erro de integridade ao salvar "
                        "respostas do formulário."
                    )
                )

                flash(
                    (
                        "Não foi possível salvar as respostas. "
                        "Atualize a página e tente novamente."
                    ),
                    "danger",
                )

            except SQLAlchemyError:
                db.session.rollback()

                current_app.logger.exception(
                    "Erro ao salvar formulário do caso."
                )

                flash(
                    "Não foi possível salvar o formulário.",
                    "danger",
                )

    respostas_por_pergunta = (
        montar_respostas_por_pergunta(
            formulario_caso
        )
    )

    perguntas_por_etapa = OrderedDict()

    for pergunta in perguntas:
        etapa = (
            getattr(pergunta, "etapa", None)
            or "Geral"
        )

        if etapa not in perguntas_por_etapa:
            perguntas_por_etapa[etapa] = {
                "icone": (
                    getattr(
                        pergunta,
                        "icone",
                        None,
                    )
                    or "📋"
                ),
                "descricao": (
                    getattr(
                        pergunta,
                        "descricao_etapa",
                        None,
                    )
                    or ""
                ),
                "ordem_etapa": (
                    getattr(
                        pergunta,
                        "ordem_etapa",
                        1,
                    )
                    or 1
                ),
                "perguntas": [],
            }

        perguntas_por_etapa[
            etapa
        ]["perguntas"].append(pergunta)

    perguntas_por_etapa = OrderedDict(
        sorted(
            perguntas_por_etapa.items(),
            key=lambda item: (
                item[1]["ordem_etapa"],
                item[0].lower(),
            ),
        )
    )

    quantidade_obrigatorias = sum(
        1
        for pergunta in perguntas
        if pergunta.obrigatoria
    )

    quantidade_respondidas = sum(
        1
        for pergunta in perguntas
        if (
            pergunta.id in respostas_por_pergunta
            and valor_esta_preenchido(
                respostas_por_pergunta[
                    pergunta.id
                ].valor
            )
        )
    )

    total_perguntas = len(
        perguntas
    )

    percentual = (
        int(
            (
                quantidade_respondidas
                / total_perguntas
            )
            * 100
        )
        if total_perguntas
        else 0
    )

    return render_template(
        "formularios_caso/preencher.html",
        caso=caso,
        formulario_caso=formulario_caso,
        perguntas=perguntas,
        perguntas_por_etapa=(
            perguntas_por_etapa
        ),
        respostas_por_pergunta=(
            respostas_por_pergunta
        ),
        total_perguntas=total_perguntas,
        quantidade_respondidas=(
            quantidade_respondidas
        ),
        quantidade_obrigatorias=(
            quantidade_obrigatorias
        ),
        percentual=percentual,
    )


@formularios_caso_bp.route(
    "/<string:formulario_caso_id>/visualizar"
)
@login_required
def visualizar(
    caso_id,
    formulario_caso_id,
):
    caso = obter_caso(
        caso_id
    )

    formulario_caso = obter_formulario_caso(
        caso.id,
        formulario_caso_id,
    )

    respostas_por_pergunta = (
        montar_respostas_por_pergunta(
            formulario_caso
        )
    )

    perguntas = (
        PerguntaFormulario.query
        .filter_by(
            formulario_modelo_id=(
                formulario_caso.formulario_modelo_id
            )
        )
        .order_by(
            PerguntaFormulario.ordem.asc(),
            PerguntaFormulario.criado_em.asc(),
        )
        .all()
    )

    perguntas_exibidas = [
        pergunta
        for pergunta in perguntas
        if (
            pergunta.ativo
            or pergunta.id
            in respostas_por_pergunta
        )
    ]

    return render_template(
        "formularios_caso/visualizar.html",
        caso=caso,
        formulario_caso=formulario_caso,
        perguntas=perguntas_exibidas,
        respostas_por_pergunta=(
            respostas_por_pergunta
        ),
    )


@formularios_caso_bp.route(
    "/<string:formulario_caso_id>/reabrir",
    methods=[
        "POST",
    ],
)
@login_required
def reabrir(
    caso_id,
    formulario_caso_id,
):
    caso = obter_caso(
        caso_id
    )

    formulario_caso = obter_formulario_caso(
        caso.id,
        formulario_caso_id,
    )

    if formulario_caso.status == "CANCELADO":
        flash(
            "Um formulário cancelado não pode ser reaberto.",
            "warning",
        )

        return redirect(
            url_for(
                "formularios_caso.visualizar",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )

    try:
        formulario_caso.reabrir()

        db.session.commit()

        flash(
            "Formulário reaberto para edição.",
            "success",
        )

        return redirect(
            url_for(
                "formularios_caso.preencher",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao reabrir formulário."
        )

        flash(
            "Não foi possível reabrir o formulário.",
            "danger",
        )

        return redirect(
            url_for(
                "formularios_caso.visualizar",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )


@formularios_caso_bp.route(
    "/<string:formulario_caso_id>/cancelar",
    methods=[
        "POST",
    ],
)
@login_required
def cancelar(
    caso_id,
    formulario_caso_id,
):
    caso = obter_caso(
        caso_id
    )

    formulario_caso = obter_formulario_caso(
        caso.id,
        formulario_caso_id,
    )

    if formulario_caso.status == "CANCELADO":
        flash(
            "Este formulário já está cancelado.",
            "warning",
        )

        return redirect(
            url_for(
                "formularios_caso.visualizar",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )

    try:
        formulario_caso.cancelar()

        db.session.commit()

        flash(
            "Formulário cancelado com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao cancelar formulário."
        )

        flash(
            "Não foi possível cancelar o formulário.",
            "danger",
        )

    return redirect(
        url_for(
            "formularios_caso.visualizar",
            caso_id=caso.id,
            formulario_caso_id=(
                formulario_caso.id
            ),
        )
    )


@formularios_caso_bp.route(
    "/<string:formulario_caso_id>/excluir",
    methods=[
        "POST",
    ],
)
@login_required
def excluir(
    caso_id,
    formulario_caso_id,
):
    caso = obter_caso(
        caso_id
    )

    formulario_caso = obter_formulario_caso(
        caso.id,
        formulario_caso_id,
    )

    if formulario_caso.status == "CONCLUIDO":
        flash(
            (
                "Um formulário concluído não pode ser excluído. "
                "Reabra ou cancele o formulário primeiro."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "formularios_caso.visualizar",
                caso_id=caso.id,
                formulario_caso_id=(
                    formulario_caso.id
                ),
            )
        )

    try:
        db.session.delete(
            formulario_caso
        )

        db.session.commit()

        flash(
            "Formulário excluído com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Erro ao excluir formulário do caso."
        )

        flash(
            "Não foi possível excluir o formulário.",
            "danger",
        )

    return redirect(
        url_for(
            "formularios_caso.listar",
            caso_id=caso.id,
        )
    )