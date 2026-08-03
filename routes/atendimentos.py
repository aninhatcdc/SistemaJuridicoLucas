from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from models.atendimento_caso import AtendimentoCaso
from models.caso import Caso
from models.usuario import Usuario
from services.timeline_service import TimelineService


atendimentos_bp = Blueprint(
    "atendimentos",
    __name__,
    url_prefix="/atendimentos",
)


def converter_data(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def converter_horario(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%H:%M").time()
    except ValueError:
        return None


def carregar_responsaveis():
    return (
        Usuario.query
        .filter_by(ativo=True)
        .order_by(Usuario.nome.asc())
        .all()
    )


def formatar_data(valor):
    return valor.strftime("%d/%m/%Y") if valor else "Não informada"


def formatar_horario(valor):
    return valor.strftime("%H:%M") if valor else "Não informado"


def formatar_texto(valor):
    return valor.strip() if isinstance(valor, str) and valor.strip() else "Não informado"


def formatar_tipo(valor):
    return AtendimentoCaso.TIPOS.get(valor, valor or "Não informado")


def formatar_responsavel(usuario):
    return usuario.nome if usuario else "Não definido"


def adicionar_alteracao(alteracoes, campo, rotulo, anterior, novo):
    if anterior == novo:
        return

    alteracoes[campo] = {
        "rotulo": rotulo,
        "anterior": anterior,
        "novo": novo,
    }


@atendimentos_bp.route(
    "/novo/<string:caso_id>",
    methods=["GET", "POST"],
)
@login_required
def novo(caso_id):
    caso = db.get_or_404(Caso, caso_id)
    responsaveis = carregar_responsaveis()

    if request.method == "POST":
        tipo = request.form.get("tipo", "").strip().upper()
        assunto = request.form.get("assunto", "").strip()
        status = request.form.get("status", "").strip().upper()
        data_atendimento = converter_data(
            request.form.get("data_atendimento")
        )
        horario = converter_horario(
            request.form.get("horario")
        )
        retorno_em = converter_data(
            request.form.get("retorno_em")
        )
        usuario_id = request.form.get("usuario_id", "").strip() or None
        descricao = request.form.get("descricao", "").strip() or None

        usuario = None
        if usuario_id:
            usuario = db.session.get(Usuario, usuario_id)

        if tipo not in AtendimentoCaso.TIPOS:
            flash("Selecione um tipo de atendimento válido.", "danger")
        elif not assunto:
            flash("Informe o assunto do atendimento.", "danger")
        elif status not in AtendimentoCaso.STATUS:
            flash("Selecione um status válido.", "danger")
        elif not data_atendimento:
            flash("Informe uma data válida para o atendimento.", "danger")
        elif usuario_id and (not usuario or not usuario.ativo):
            flash("O responsável selecionado é inválido.", "danger")
        else:
            responsavel = usuario or current_user

            atendimento = AtendimentoCaso(
                tipo=tipo,
                assunto=assunto,
                data_atendimento=data_atendimento,
                horario=horario,
                status=status,
                descricao=descricao,
                retorno_em=retorno_em,
                caso_id=caso.id,
                usuario_id=responsavel.id,
            )

            try:
                db.session.add(atendimento)
                db.session.flush()

                TimelineService.registrar_atendimento_criado(
                    caso=caso,
                    atendimento=atendimento,
                    usuario=current_user,
                )

                if retorno_em:
                    TimelineService.registrar_retorno_atendimento_alterado(
                        caso=caso,
                        atendimento=atendimento,
                        retorno_anterior=None,
                        novo_retorno=retorno_em,
                        usuario=current_user,
                    )

                db.session.commit()
                flash("Atendimento cadastrado com sucesso.", "success")
                return redirect(
                    url_for(
                        "casos.detalhes",
                        caso_id=caso.id,
                        _anchor="atendimentos",
                    )
                )
            except Exception:
                db.session.rollback()
                flash(
                    "Não foi possível cadastrar o atendimento.",
                    "danger",
                )

    return render_template(
        "atendimentos/novo.html",
        caso=caso,
        responsaveis=responsaveis,
        tipos=AtendimentoCaso.TIPOS,
        status_opcoes=AtendimentoCaso.STATUS,
        dados=request.form,
    )


@atendimentos_bp.route(
    "/<string:atendimento_id>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(atendimento_id):
    atendimento = db.get_or_404(
        AtendimentoCaso,
        atendimento_id,
    )
    responsaveis = carregar_responsaveis()

    if request.method == "POST":
        tipo = request.form.get("tipo", "").strip().upper()
        assunto = request.form.get("assunto", "").strip()
        status = request.form.get("status", "").strip().upper()
        data_atendimento = converter_data(
            request.form.get("data_atendimento")
        )
        horario = converter_horario(
            request.form.get("horario")
        )
        retorno_em = converter_data(
            request.form.get("retorno_em")
        )
        usuario_id = request.form.get("usuario_id", "").strip() or None
        descricao = request.form.get("descricao", "").strip() or None

        usuario = None
        if usuario_id:
            usuario = db.session.get(Usuario, usuario_id)

        if tipo not in AtendimentoCaso.TIPOS:
            flash("Selecione um tipo de atendimento válido.", "danger")
        elif not assunto:
            flash("Informe o assunto do atendimento.", "danger")
        elif status not in AtendimentoCaso.STATUS:
            flash("Selecione um status válido.", "danger")
        elif not data_atendimento:
            flash("Informe uma data válida para o atendimento.", "danger")
        elif usuario_id and (not usuario or not usuario.ativo):
            flash("O responsável selecionado é inválido.", "danger")
        else:
            responsavel_novo = usuario or current_user
            responsavel_anterior = atendimento.usuario
            status_anterior = atendimento.status
            retorno_anterior = atendimento.retorno_em

            alteracoes = {}

            adicionar_alteracao(
                alteracoes,
                "tipo",
                "Tipo",
                formatar_tipo(atendimento.tipo),
                formatar_tipo(tipo),
            )
            adicionar_alteracao(
                alteracoes,
                "assunto",
                "Assunto",
                formatar_texto(atendimento.assunto),
                formatar_texto(assunto),
            )
            adicionar_alteracao(
                alteracoes,
                "data_atendimento",
                "Data do atendimento",
                formatar_data(atendimento.data_atendimento),
                formatar_data(data_atendimento),
            )
            adicionar_alteracao(
                alteracoes,
                "horario",
                "Horário",
                formatar_horario(atendimento.horario),
                formatar_horario(horario),
            )
            adicionar_alteracao(
                alteracoes,
                "responsavel",
                "Responsável",
                formatar_responsavel(responsavel_anterior),
                formatar_responsavel(responsavel_novo),
            )
            adicionar_alteracao(
                alteracoes,
                "descricao",
                "Descrição",
                formatar_texto(atendimento.descricao),
                formatar_texto(descricao),
            )

            atendimento.tipo = tipo
            atendimento.assunto = assunto
            atendimento.status = status
            atendimento.data_atendimento = data_atendimento
            atendimento.horario = horario
            atendimento.retorno_em = retorno_em
            atendimento.descricao = descricao
            atendimento.usuario_id = responsavel_novo.id

            try:
                if alteracoes:
                    TimelineService.registrar_atendimento_editado(
                        caso=atendimento.caso,
                        atendimento=atendimento,
                        alteracoes=alteracoes,
                        usuario=current_user,
                    )

                if status_anterior != status:
                    TimelineService.registrar_status_atendimento_alterado(
                        caso=atendimento.caso,
                        atendimento=atendimento,
                        status_anterior=status_anterior,
                        novo_status=status,
                        usuario=current_user,
                    )

                if retorno_anterior != retorno_em:
                    TimelineService.registrar_retorno_atendimento_alterado(
                        caso=atendimento.caso,
                        atendimento=atendimento,
                        retorno_anterior=retorno_anterior,
                        novo_retorno=retorno_em,
                        usuario=current_user,
                    )

                db.session.commit()
                flash("Atendimento atualizado com sucesso.", "success")
                return redirect(
                    url_for(
                        "casos.detalhes",
                        caso_id=atendimento.caso_id,
                        _anchor="atendimentos",
                    )
                )
            except Exception:
                db.session.rollback()
                flash(
                    "Não foi possível atualizar o atendimento.",
                    "danger",
                )

    return render_template(
        "atendimentos/editar.html",
        atendimento=atendimento,
        caso=atendimento.caso,
        responsaveis=responsaveis,
        tipos=AtendimentoCaso.TIPOS,
        status_opcoes=AtendimentoCaso.STATUS,
        dados=request.form,
    )


@atendimentos_bp.route(
    "/<string:atendimento_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir(atendimento_id):
    atendimento = db.get_or_404(
        AtendimentoCaso,
        atendimento_id,
    )
    caso = atendimento.caso
    caso_id = atendimento.caso_id

    try:
        TimelineService.registrar_atendimento_excluido(
            caso=caso,
            atendimento=atendimento,
            usuario=current_user,
        )

        db.session.delete(atendimento)
        db.session.commit()
        flash("Atendimento excluído com sucesso.", "success")
    except Exception:
        db.session.rollback()
        flash(
            "Não foi possível excluir o atendimento.",
            "danger",
        )

    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso_id,
            _anchor="atendimentos",
        )
    )