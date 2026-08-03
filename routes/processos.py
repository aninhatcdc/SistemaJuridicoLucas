from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from models import db
from models.caso import Caso
from models.processo import Processo
from services.timeline_service import TimelineService


processos_bp = Blueprint(
    "processos",
    __name__,
    url_prefix="/processos",
)


def converter_data(valor):
    if not valor:
        return None

    try:
        return datetime.strptime(
            valor,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


def converter_valor(valor):
    if not valor:
        return None

    valor_limpo = (
        valor
        .replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return Decimal(valor_limpo)

    except InvalidOperation:
        return None


def formatar_data(valor):
    if not valor:
        return "Não informada"

    return valor.strftime("%d/%m/%Y")


def formatar_valor(valor):
    if valor is None:
        return "Não informado"

    valor_formatado = f"{valor:,.2f}"

    return (
        "R$ "
        + valor_formatado
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def valor_texto(valor):
    if valor is None:
        return "Não informado"

    return str(valor)


def adicionar_alteracao(
    alteracoes,
    campo,
    rotulo,
    anterior,
    novo,
):
    if anterior == novo:
        return

    alteracoes[campo] = {
        "rotulo": rotulo,
        "anterior": anterior,
        "novo": novo,
    }


@processos_bp.route(
    "/caso/<string:caso_id>/novo",
    methods=["GET", "POST"],
)
@login_required
def novo(caso_id):
    caso = db.get_or_404(
        Caso,
        caso_id,
    )

    if request.method == "POST":

        numero_cnj = (
            request.form.get(
                "numero_cnj",
                "",
            ).strip()
            or None
        )

        tribunal = (
            request.form.get(
                "tribunal",
                "",
            ).strip()
            or None
        )

        comarca = (
            request.form.get(
                "comarca",
                "",
            ).strip()
            or None
        )

        vara = (
            request.form.get(
                "vara",
                "",
            ).strip()
            or None
        )

        classe_processual = (
            request.form.get(
                "classe_processual",
                "",
            ).strip()
            or None
        )

        assunto = (
            request.form.get(
                "assunto",
                "",
            ).strip()
            or None
        )

        polo_ativo = (
            request.form.get(
                "polo_ativo",
                "",
            ).strip()
            or None
        )

        polo_passivo = (
            request.form.get(
                "polo_passivo",
                "",
            ).strip()
            or None
        )

        situacao = (
            request.form.get(
                "situacao",
                "ATIVO",
            ).strip()
            or "ATIVO"
        )

        observacoes = (
            request.form.get(
                "observacoes",
                "",
            ).strip()
            or None
        )

        data_distribuicao = converter_data(
            request.form.get(
                "data_distribuicao",
                "",
            )
        )

        valor_causa = converter_valor(
            request.form.get(
                "valor_causa",
                "",
            )
        )

        processo = Processo(
            numero_cnj=numero_cnj,
            tribunal=tribunal,
            comarca=comarca,
            vara=vara,
            classe_processual=classe_processual,
            assunto=assunto,
            polo_ativo=polo_ativo,
            polo_passivo=polo_passivo,
            data_distribuicao=data_distribuicao,
            situacao=situacao,
            valor_causa=valor_causa,
            observacoes=observacoes,
            caso_id=caso.id,
        )

        try:
            db.session.add(processo)
            db.session.flush()

            TimelineService.registrar_processo_criado(
                caso=caso,
                processo=processo,
            )

            db.session.commit()

            flash(
                "Processo cadastrado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "casos.detalhes",
                    caso_id=caso.id,
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                "Não foi possível cadastrar o processo.",
                "danger",
            )

    return render_template(
        "processos/novo.html",
        caso=caso,
    )


@processos_bp.route(
    "/<string:processo_id>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(processo_id):
    processo = db.get_or_404(
        Processo,
        processo_id,
    )

    caso = processo.caso

    if request.method == "POST":
        numero_cnj_anterior = processo.numero_cnj
        tribunal_anterior = processo.tribunal
        comarca_anterior = processo.comarca
        vara_anterior = processo.vara
        classe_anterior = processo.classe_processual
        assunto_anterior = processo.assunto
        polo_ativo_anterior = processo.polo_ativo
        polo_passivo_anterior = processo.polo_passivo
        situacao_anterior = processo.situacao
        observacoes_anteriores = processo.observacoes
        data_distribuicao_anterior = processo.data_distribuicao
        valor_causa_anterior = processo.valor_causa

        novo_numero_cnj = (
            request.form.get(
                "numero_cnj",
                "",
            ).strip()
            or None
        )

        novo_tribunal = (
            request.form.get(
                "tribunal",
                "",
            ).strip()
            or None
        )

        nova_comarca = (
            request.form.get(
                "comarca",
                "",
            ).strip()
            or None
        )

        nova_vara = (
            request.form.get(
                "vara",
                "",
            ).strip()
            or None
        )

        nova_classe_processual = (
            request.form.get(
                "classe_processual",
                "",
            ).strip()
            or None
        )

        novo_assunto = (
            request.form.get(
                "assunto",
                "",
            ).strip()
            or None
        )

        novo_polo_ativo = (
            request.form.get(
                "polo_ativo",
                "",
            ).strip()
            or None
        )

        novo_polo_passivo = (
            request.form.get(
                "polo_passivo",
                "",
            ).strip()
            or None
        )

        nova_situacao = (
            request.form.get(
                "situacao",
                "ATIVO",
            ).strip()
            or "ATIVO"
        )

        novas_observacoes = (
            request.form.get(
                "observacoes",
                "",
            ).strip()
            or None
        )

        nova_data_distribuicao = converter_data(
            request.form.get(
                "data_distribuicao",
                "",
            )
        )

        novo_valor_causa = converter_valor(
            request.form.get(
                "valor_causa",
                "",
            )
        )

        alteracoes = {}

        adicionar_alteracao(
            alteracoes,
            "numero_cnj",
            "Número CNJ",
            numero_cnj_anterior or "Não informado",
            novo_numero_cnj or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "tribunal",
            "Tribunal",
            tribunal_anterior or "Não informado",
            novo_tribunal or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "comarca",
            "Comarca",
            comarca_anterior or "Não informada",
            nova_comarca or "Não informada",
        )
        adicionar_alteracao(
            alteracoes,
            "vara",
            "Vara",
            vara_anterior or "Não informada",
            nova_vara or "Não informada",
        )
        adicionar_alteracao(
            alteracoes,
            "classe_processual",
            "Classe processual",
            classe_anterior or "Não informada",
            nova_classe_processual or "Não informada",
        )
        adicionar_alteracao(
            alteracoes,
            "assunto",
            "Assunto",
            assunto_anterior or "Não informado",
            novo_assunto or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "polo_ativo",
            "Polo ativo",
            polo_ativo_anterior or "Não informado",
            novo_polo_ativo or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "polo_passivo",
            "Polo passivo",
            polo_passivo_anterior or "Não informado",
            novo_polo_passivo or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "data_distribuicao",
            "Data de distribuição",
            formatar_data(data_distribuicao_anterior),
            formatar_data(nova_data_distribuicao),
        )
        adicionar_alteracao(
            alteracoes,
            "valor_causa",
            "Valor da causa",
            formatar_valor(valor_causa_anterior),
            formatar_valor(novo_valor_causa),
        )
        adicionar_alteracao(
            alteracoes,
            "observacoes",
            "Observações",
            observacoes_anteriores or "Não informadas",
            novas_observacoes or "Não informadas",
        )

        processo.numero_cnj = novo_numero_cnj
        processo.tribunal = novo_tribunal
        processo.comarca = nova_comarca
        processo.vara = nova_vara
        processo.classe_processual = nova_classe_processual
        processo.assunto = novo_assunto
        processo.polo_ativo = novo_polo_ativo
        processo.polo_passivo = novo_polo_passivo
        processo.situacao = nova_situacao
        processo.observacoes = novas_observacoes
        processo.data_distribuicao = nova_data_distribuicao
        processo.valor_causa = novo_valor_causa

        try:
            if alteracoes:
                TimelineService.registrar_processo_editado(
                    caso=caso,
                    processo=processo,
                    alteracoes=alteracoes,
                )

            if situacao_anterior != nova_situacao:
                TimelineService.registrar_situacao_processo_alterada(
                    caso=caso,
                    processo=processo,
                    situacao_anterior=situacao_anterior,
                    nova_situacao=nova_situacao,
                )

            db.session.commit()

            flash(
                "Processo atualizado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "casos.detalhes",
                    caso_id=processo.caso_id,
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                "Não foi possível atualizar o processo.",
                "danger",
            )

    return render_template(
        "processos/editar.html",
        processo=processo,
        caso=caso,
    )


@processos_bp.route(
    "/<string:processo_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir(processo_id):
    processo = db.get_or_404(
        Processo,
        processo_id,
    )

    caso = processo.caso

    try:
        TimelineService.registrar_processo_excluido(
            caso=caso,
            processo=processo,
        )

        db.session.delete(processo)
        db.session.commit()

        flash(
            "Processo excluído com sucesso.",
            "success",
        )

    except Exception:
        db.session.rollback()

        flash(
            "Não foi possível excluir o processo.",
            "danger",
        )

    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso.id,
        )
    )