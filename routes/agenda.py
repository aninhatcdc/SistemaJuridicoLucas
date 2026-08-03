from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
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
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from models import db
from models.caso import Caso
from models.evento_agenda import EventoAgenda
from models.processo import Processo
from models.usuario import Usuario
from services.timeline_service import TimelineService


agenda_bp = Blueprint(
    "agenda",
    __name__,
    url_prefix="/agenda",
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def texto_formulario(nome_campo):
    """
    Recupera um texto do formulário e devolve None quando
    o campo estiver vazio.
    """

    valor = request.form.get(
        nome_campo,
        "",
    ).strip()

    return valor or None


def data_formulario(nome_campo):
    """
    Converte um campo HTML do tipo date para um objeto date.
    """

    valor = request.form.get(
        nome_campo,
        "",
    ).strip()

    if not valor:
        return None

    try:
        return datetime.strptime(
            valor,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


def hora_formulario(nome_campo):
    """
    Converte um campo HTML do tipo time para um objeto time.
    """

    valor = request.form.get(
        nome_campo,
        "",
    ).strip()

    if not valor:
        return None

    formatos = [
        "%H:%M",
        "%H:%M:%S",
    ]

    for formato in formatos:
        try:
            return datetime.strptime(
                valor,
                formato,
            ).time()

        except ValueError:
            continue

    return None


def obter_evento_ou_404(evento_id):
    """
    Recupera um evento da Agenda ou retorna erro 404.
    """

    return EventoAgenda.query.get_or_404(evento_id)


def usuarios_ativos():
    """
    Retorna os usuários ativos em ordem alfabética.
    """

    return (
        Usuario.query
        .filter_by(ativo=True)
        .order_by(Usuario.nome.asc())
        .all()
    )


def casos_disponiveis():
    """
    Retorna os casos disponíveis para seleção.
    """

    return (
        Caso.query
        .options(
            joinedload(Caso.cliente),
            joinedload(Caso.status),
        )
        .order_by(
            Caso.data_abertura.desc(),
            Caso.numero_interno.desc(),
        )
        .all()
    )


def processos_disponiveis():
    """
    Retorna os processos disponíveis para seleção.
    """

    return (
        Processo.query
        .options(
            joinedload(Processo.caso),
        )
        .order_by(
            Processo.criado_em.desc(),
        )
        .all()
    )


def validar_tipo(tipo):
    if tipo in EventoAgenda.TIPOS:
        return tipo

    return "TAREFA"


def validar_status(status):
    if status in EventoAgenda.STATUS:
        return status

    return "PENDENTE"


def validar_prioridade(prioridade):
    if prioridade in EventoAgenda.PRIORIDADES:
        return prioridade

    return "NORMAL"


def validar_vinculos(caso_id, processo_id):
    """
    Valida o vínculo do evento com Caso e Processo.

    Quando um processo for informado, o caso do processo será
    utilizado automaticamente caso nenhum caso tenha sido escolhido.
    """

    caso = None
    processo = None

    if caso_id:
        caso = db.session.get(
            Caso,
            caso_id,
        )

        if caso is None:
            return (
                None,
                None,
                "O caso selecionado não foi encontrado.",
            )

    if processo_id:
        processo = db.session.get(
            Processo,
            processo_id,
        )

        if processo is None:
            return (
                caso,
                None,
                "O processo selecionado não foi encontrado.",
            )

        if caso is None:
            caso = processo.caso
            caso_id = processo.caso_id

        elif processo.caso_id != caso.id:
            return (
                caso,
                processo,
                (
                    "O processo selecionado não pertence "
                    "ao caso informado."
                ),
            )

    return (
        caso,
        processo,
        None,
    )


def preencher_evento_com_formulario(evento):
    """
    Preenche um objeto EventoAgenda com os dados recebidos
    pelo formulário.

    Retorna uma mensagem de erro quando algum dado obrigatório
    ou relacionamento for inválido.
    """

    titulo = texto_formulario("titulo")
    descricao = texto_formulario("descricao")
    tipo = texto_formulario("tipo")
    status = texto_formulario("status")
    prioridade = texto_formulario("prioridade")
    data_evento = data_formulario("data")
    hora_inicio = hora_formulario("hora_inicio")
    hora_fim = hora_formulario("hora_fim")
    local = texto_formulario("local")

    caso_id = texto_formulario("caso_id")
    processo_id = texto_formulario("processo_id")
    responsavel_id = texto_formulario("responsavel_id")

    if not titulo:
        return "Informe o título do compromisso."

    if not data_evento:
        return "Informe uma data válida para o compromisso."

    if (
        hora_inicio
        and hora_fim
        and hora_fim <= hora_inicio
    ):
        return (
            "O horário final deve ser posterior "
            "ao horário inicial."
        )

    caso, processo, erro_vinculo = validar_vinculos(
        caso_id=caso_id,
        processo_id=processo_id,
    )

    if erro_vinculo:
        return erro_vinculo

    responsavel = None

    if responsavel_id:
        responsavel = db.session.get(
            Usuario,
            responsavel_id,
        )

        if responsavel is None:
            return "O responsável selecionado não foi encontrado."

        if not responsavel.ativo:
            return "O responsável selecionado está inativo."

    status_anterior = evento.status

    evento.titulo = titulo
    evento.descricao = descricao
    evento.tipo = validar_tipo(tipo)
    evento.status = validar_status(status)
    evento.prioridade = validar_prioridade(prioridade)
    evento.data = data_evento
    evento.hora_inicio = hora_inicio
    evento.hora_fim = hora_fim
    evento.local = local

    evento.caso = caso
    evento.processo = processo
    evento.responsavel = responsavel

    if evento.status == "CONCLUIDO":
        if (
            status_anterior != "CONCLUIDO"
            or evento.concluido_em is None
        ):
            evento.concluido_em = datetime.utcnow()

    else:
        evento.concluido_em = None

    return None


def fotografia_evento(evento):
    """Cria uma fotografia simples do evento para comparar edições."""

    return {
        "titulo": evento.titulo,
        "descricao": evento.descricao,
        "tipo": evento.tipo,
        "status": evento.status,
        "prioridade": evento.prioridade,
        "data": evento.data,
        "hora_inicio": evento.hora_inicio,
        "hora_fim": evento.hora_fim,
        "local": evento.local,
        "caso_id": evento.caso_id,
        "processo_id": evento.processo_id,
        "responsavel_id": evento.responsavel_id,
        "caso_numero": (
            evento.caso.numero_interno
            if evento.caso
            else None
        ),
        "processo_numero": (
            evento.processo.numero_cnj
            if evento.processo
            else None
        ),
        "responsavel_nome": (
            evento.responsavel.nome
            if evento.responsavel
            else None
        ),
    }


def formatar_data_timeline(valor):
    return valor.strftime("%d/%m/%Y") if valor else "Não informado"


def formatar_hora_timeline(valor):
    return valor.strftime("%H:%M") if valor else "Não informado"


def montar_alteracoes_evento(anterior, evento):
    """Retorna apenas os campos efetivamente alterados."""

    alteracoes = {}

    def adicionar(campo, rotulo, valor_anterior, valor_novo):
        if valor_anterior != valor_novo:
            alteracoes[campo] = {
                "rotulo": rotulo,
                "anterior": valor_anterior or "Não informado",
                "novo": valor_novo or "Não informado",
            }

    adicionar("titulo", "Título", anterior["titulo"], evento.titulo)
    adicionar(
        "descricao",
        "Descrição",
        anterior["descricao"],
        evento.descricao,
    )
    adicionar(
        "tipo",
        "Tipo",
        TimelineService.formatar_tipo_agenda(anterior["tipo"]),
        TimelineService.formatar_tipo_agenda(evento.tipo),
    )
    adicionar(
        "prioridade",
        "Prioridade",
        TimelineService.formatar_prioridade(anterior["prioridade"]),
        TimelineService.formatar_prioridade(evento.prioridade),
    )
    adicionar(
        "data",
        "Data",
        formatar_data_timeline(anterior["data"]),
        formatar_data_timeline(evento.data),
    )
    adicionar(
        "hora_inicio",
        "Horário inicial",
        formatar_hora_timeline(anterior["hora_inicio"]),
        formatar_hora_timeline(evento.hora_inicio),
    )
    adicionar(
        "hora_fim",
        "Horário final",
        formatar_hora_timeline(anterior["hora_fim"]),
        formatar_hora_timeline(evento.hora_fim),
    )
    adicionar("local", "Local", anterior["local"], evento.local)
    adicionar(
        "caso",
        "Caso",
        anterior["caso_numero"],
        evento.caso.numero_interno if evento.caso else None,
    )
    adicionar(
        "processo",
        "Processo",
        anterior["processo_numero"],
        evento.processo.numero_cnj if evento.processo else None,
    )
    adicionar(
        "responsavel",
        "Responsável",
        anterior["responsavel_nome"],
        evento.responsavel.nome if evento.responsavel else None,
    )

    return alteracoes


def destino_apos_acao(evento=None):
    """
    Determina para qual tela o usuário deve retornar após
    cadastrar, editar ou excluir um evento.
    """

    retorno = request.form.get(
        "retorno",
        "",
    ).strip()

    if retorno == "caso" and evento and evento.caso_id:
        return (
            url_for(
                "casos.detalhes",
                caso_id=evento.caso_id,
            )
            + "#agenda"
        )

    if retorno == "calendario":
        return url_for(
            "agenda.calendario",
        )

    return url_for(
        "agenda.listar_eventos",
    )


# ============================================================
# LISTAGEM DA AGENDA
# ============================================================

@agenda_bp.route("/")
@login_required
def listar_eventos():
    hoje = date.today()

    termo = request.args.get(
        "q",
        "",
    ).strip()

    periodo = request.args.get(
        "periodo",
        "proximos",
    ).strip()

    tipo = request.args.get(
        "tipo",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip()

    prioridade = request.args.get(
        "prioridade",
        "",
    ).strip()

    responsavel_id = request.args.get(
        "responsavel_id",
        "",
    ).strip()

    caso_id = request.args.get(
        "caso_id",
        "",
    ).strip()

    consulta = (
        EventoAgenda.query
        .options(
            joinedload(EventoAgenda.caso)
            .joinedload(Caso.cliente),
            joinedload(EventoAgenda.processo),
            joinedload(EventoAgenda.responsavel),
        )
    )

    if termo:
        termo_like = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                EventoAgenda.titulo.ilike(termo_like),
                EventoAgenda.descricao.ilike(termo_like),
                EventoAgenda.local.ilike(termo_like),
            )
        )

    if periodo == "hoje":
        consulta = consulta.filter(
            EventoAgenda.data == hoje,
        )

    elif periodo == "amanha":
        consulta = consulta.filter(
            EventoAgenda.data == hoje + timedelta(days=1),
        )

    elif periodo == "semana":
        fim_semana = hoje + timedelta(days=7)

        consulta = consulta.filter(
            EventoAgenda.data >= hoje,
            EventoAgenda.data <= fim_semana,
            EventoAgenda.status.notin_(
                [
                    "CONCLUIDO",
                    "CANCELADO",
                ]
            ),
        )

    elif periodo == "atrasados":
        consulta = consulta.filter(
            EventoAgenda.data < hoje,
            EventoAgenda.status.notin_(
                [
                    "CONCLUIDO",
                    "CANCELADO",
                ]
            ),
        )

    elif periodo == "concluidos":
        consulta = consulta.filter(
            EventoAgenda.status == "CONCLUIDO",
        )

    elif periodo == "cancelados":
        consulta = consulta.filter(
            EventoAgenda.status == "CANCELADO",
        )

    elif periodo == "todos":
        pass

    else:
        periodo = "proximos"

        consulta = consulta.filter(
            EventoAgenda.data >= hoje,
            EventoAgenda.status.notin_(
                [
                    "CONCLUIDO",
                    "CANCELADO",
                ]
            ),
        )

    if tipo in EventoAgenda.TIPOS:
        consulta = consulta.filter(
            EventoAgenda.tipo == tipo,
        )

    if status in EventoAgenda.STATUS:
        consulta = consulta.filter(
            EventoAgenda.status == status,
        )

    if prioridade in EventoAgenda.PRIORIDADES:
        consulta = consulta.filter(
            EventoAgenda.prioridade == prioridade,
        )

    if responsavel_id:
        consulta = consulta.filter(
            EventoAgenda.responsavel_id == responsavel_id,
        )

    if caso_id:
        consulta = consulta.filter(
            EventoAgenda.caso_id == caso_id,
        )

    if periodo in {
        "atrasados",
        "concluidos",
        "cancelados",
        "todos",
    }:
        consulta = consulta.order_by(
            EventoAgenda.data.desc(),
            EventoAgenda.hora_inicio.desc(),
            EventoAgenda.criado_em.desc(),
        )

    else:
        consulta = consulta.order_by(
            EventoAgenda.data.asc(),
            EventoAgenda.hora_inicio.asc(),
            EventoAgenda.criado_em.asc(),
        )

    eventos = consulta.all()

    indicadores = {
        "hoje": (
            EventoAgenda.query
            .filter(
                EventoAgenda.data == hoje,
                EventoAgenda.status.notin_(
                    [
                        "CONCLUIDO",
                        "CANCELADO",
                    ]
                ),
            )
            .count()
        ),
        "proximos": (
            EventoAgenda.query
            .filter(
                EventoAgenda.data > hoje,
                EventoAgenda.status.notin_(
                    [
                        "CONCLUIDO",
                        "CANCELADO",
                    ]
                ),
            )
            .count()
        ),
        "atrasados": (
            EventoAgenda.query
            .filter(
                EventoAgenda.data < hoje,
                EventoAgenda.status.notin_(
                    [
                        "CONCLUIDO",
                        "CANCELADO",
                    ]
                ),
            )
            .count()
        ),
        "concluidos": (
            EventoAgenda.query
            .filter(
                EventoAgenda.status == "CONCLUIDO",
            )
            .count()
        ),
    }

    filtros = {
        "q": termo,
        "periodo": periodo,
        "tipo": tipo,
        "status": status,
        "prioridade": prioridade,
        "responsavel_id": responsavel_id,
        "caso_id": caso_id,
    }

    return render_template(
        "agenda/listar.html",
        eventos=eventos,
        usuarios=usuarios_ativos(),
        casos=casos_disponiveis(),
        indicadores=indicadores,
        filtros=filtros,
        tipos=EventoAgenda.TIPOS,
        status_eventos=EventoAgenda.STATUS,
        prioridades=EventoAgenda.PRIORIDADES,
        hoje=hoje,
    )


# ============================================================
# CALENDÁRIO
# ============================================================

@agenda_bp.route("/calendario")
@login_required
def calendario():
    eventos = (
        EventoAgenda.query
        .options(
            joinedload(EventoAgenda.caso),
            joinedload(EventoAgenda.processo),
            joinedload(EventoAgenda.responsavel),
        )
        .order_by(
            EventoAgenda.data.asc(),
            EventoAgenda.hora_inicio.asc(),
        )
        .all()
    )

    eventos_calendario = []

    cores = {
        "AUDIENCIA": "#dc3545",
        "PRAZO": "#fd7e14",
        "REUNIAO": "#0d6efd",
        "ATENDIMENTO": "#0dcaf0",
        "TAREFA": "#6c757d",
        "LEMBRETE": "#212529",
    }

    for evento in eventos:
        data_inicio = evento.data.isoformat()

        if evento.hora_inicio:
            data_inicio = (
                f"{evento.data.isoformat()}T"
                f"{evento.hora_inicio.strftime('%H:%M:%S')}"
            )

        data_fim = None

        if evento.hora_fim:
            data_fim = (
                f"{evento.data.isoformat()}T"
                f"{evento.hora_fim.strftime('%H:%M:%S')}"
            )

        titulo = evento.titulo

        if evento.status == "CONCLUIDO":
            titulo = f"✓ {titulo}"

        elif evento.status == "CANCELADO":
            titulo = f"Cancelado: {titulo}"

        eventos_calendario.append(
            {
                "id": evento.id,
                "title": titulo,
                "start": data_inicio,
                "end": data_fim,
                "allDay": evento.hora_inicio is None,
                "color": cores.get(
                    evento.tipo,
                    "#6c757d",
                ),
                "url": url_for(
                    "agenda.editar_evento",
                    evento_id=evento.id,
                    retorno="calendario",
                ),
                "extendedProps": {
                    "tipo": evento.tipo_formatado,
                    "status": evento.status_formatado,
                    "prioridade": evento.prioridade_formatada,
                    "local": evento.local or "",
                    "responsavel": (
                        evento.responsavel.nome
                        if evento.responsavel
                        else ""
                    ),
                    "caso": (
                        evento.caso.numero_interno
                        if evento.caso
                        else ""
                    ),
                },
            }
        )

    return render_template(
        "agenda/calendario.html",
        eventos_calendario=eventos_calendario,
        hoje=date.today(),
    )


# ============================================================
# NOVO EVENTO
# ============================================================

@agenda_bp.route(
    "/novo",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def novo_evento():
    caso_id = request.args.get(
        "caso_id",
        "",
    ).strip()

    processo_id = request.args.get(
        "processo_id",
        "",
    ).strip()

    retorno = request.args.get(
        "retorno",
        "",
    ).strip()

    data_inicial = request.args.get(
    "data",
    "",
    ).strip()

    try:
        data_inicial = datetime.strptime(
            data_inicial,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        data_inicial = date.today()


    evento = EventoAgenda(
        data=data_inicial,
        status="PENDENTE",
        prioridade="NORMAL",
        tipo="TAREFA",
        responsavel_id=current_user.id,
    )

    if request.method == "GET":
        if caso_id:
            caso = db.session.get(
                Caso,
                caso_id,
            )

            if caso:
                evento.caso = caso

        if processo_id:
            processo = db.session.get(
                Processo,
                processo_id,
            )

            if processo:
                evento.processo = processo
                evento.caso = processo.caso

        return render_template(
            "agenda/novo.html",
            evento=evento,
            usuarios=usuarios_ativos(),
            casos=casos_disponiveis(),
            processos=processos_disponiveis(),
            tipos=EventoAgenda.TIPOS,
            status_eventos=EventoAgenda.STATUS,
            prioridades=EventoAgenda.PRIORIDADES,
            retorno=retorno,
        )

    erro = preencher_evento_com_formulario(
        evento,
    )

    if erro:
        flash(
            erro,
            "danger",
        )

        return render_template(
            "agenda/novo.html",
            evento=evento,
            usuarios=usuarios_ativos(),
            casos=casos_disponiveis(),
            processos=processos_disponiveis(),
            tipos=EventoAgenda.TIPOS,
            status_eventos=EventoAgenda.STATUS,
            prioridades=EventoAgenda.PRIORIDADES,
            retorno=request.form.get(
                "retorno",
                "",
            ),
        )

    try:
        db.session.add(evento)
        db.session.flush()

        if evento.caso:
            TimelineService.registrar_evento_agenda_criado(
                caso=evento.caso,
                evento_agenda=evento,
                usuario=current_user,
            )

        db.session.commit()

        flash(
            "Compromisso cadastrado com sucesso.",
            "success",
        )

        return redirect(
            destino_apos_acao(evento),
        )

    except SQLAlchemyError:
        db.session.rollback()

        flash(
            (
                "Não foi possível cadastrar o compromisso. "
                "Tente novamente."
            ),
            "danger",
        )

        return render_template(
            "agenda/novo.html",
            evento=evento,
            usuarios=usuarios_ativos(),
            casos=casos_disponiveis(),
            processos=processos_disponiveis(),
            tipos=EventoAgenda.TIPOS,
            status_eventos=EventoAgenda.STATUS,
            prioridades=EventoAgenda.PRIORIDADES,
            retorno=request.form.get(
                "retorno",
                "",
            ),
        )


# ============================================================
# EDITAR EVENTO
# ============================================================

@agenda_bp.route(
    "/<string:evento_id>/editar",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def editar_evento(evento_id):
    evento = obter_evento_ou_404(
        evento_id,
    )

    retorno = (
        request.args.get(
            "retorno",
            "",
        ).strip()
        or request.form.get(
            "retorno",
            "",
        ).strip()
    )

    if request.method == "POST":
        estado_anterior = fotografia_evento(evento)

        erro = preencher_evento_com_formulario(
            evento,
        )

        if erro:
            flash(
                erro,
                "danger",
            )

        else:
            try:
                alteracoes = montar_alteracoes_evento(
                    estado_anterior,
                    evento,
                )

                if evento.caso and alteracoes:
                    TimelineService.registrar_evento_agenda_editado(
                        caso=evento.caso,
                        evento_agenda=evento,
                        alteracoes=alteracoes,
                        usuario=current_user,
                    )

                if (
                    evento.caso
                    and estado_anterior["status"] != evento.status
                ):
                    TimelineService.registrar_status_evento_agenda_alterado(
                        caso=evento.caso,
                        evento_agenda=evento,
                        status_anterior=estado_anterior["status"],
                        novo_status=evento.status,
                        usuario=current_user,
                    )

                db.session.commit()

                flash(
                    "Compromisso atualizado com sucesso.",
                    "success",
                )

                return redirect(
                    destino_apos_acao(evento),
                )

            except SQLAlchemyError:
                db.session.rollback()

                flash(
                    (
                        "Não foi possível atualizar o compromisso. "
                        "Tente novamente."
                    ),
                    "danger",
                )

    return render_template(
        "agenda/editar.html",
        evento=evento,
        usuarios=usuarios_ativos(),
        casos=casos_disponiveis(),
        processos=processos_disponiveis(),
        tipos=EventoAgenda.TIPOS,
        status_eventos=EventoAgenda.STATUS,
        prioridades=EventoAgenda.PRIORIDADES,
        retorno=retorno,
    )


# ============================================================
# MARCAR COMO CONCLUÍDO
# ============================================================

@agenda_bp.route(
    "/<string:evento_id>/concluir",
    methods=["POST"],
)
@login_required
def concluir_evento(evento_id):
    evento = obter_evento_ou_404(
        evento_id,
    )

    if evento.status == "CONCLUIDO":
        flash(
            "Este compromisso já está concluído.",
            "info",
        )

        return redirect(
            destino_apos_acao(evento),
        )

    try:
        status_anterior = evento.status
        evento.marcar_como_concluido()

        if evento.caso:
            TimelineService.registrar_status_evento_agenda_alterado(
                caso=evento.caso,
                evento_agenda=evento,
                status_anterior=status_anterior,
                novo_status=evento.status,
                usuario=current_user,
            )

        db.session.commit()

        flash(
            "Compromisso marcado como concluído.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        flash(
            "Não foi possível concluir o compromisso.",
            "danger",
        )

    return redirect(
        destino_apos_acao(evento),
    )


# ============================================================
# REABRIR EVENTO
# ============================================================

@agenda_bp.route(
    "/<string:evento_id>/reabrir",
    methods=["POST"],
)
@login_required
def reabrir_evento(evento_id):
    evento = obter_evento_ou_404(
        evento_id,
    )

    try:
        status_anterior = evento.status
        evento.reabrir()

        if evento.caso and status_anterior != evento.status:
            TimelineService.registrar_status_evento_agenda_alterado(
                caso=evento.caso,
                evento_agenda=evento,
                status_anterior=status_anterior,
                novo_status=evento.status,
                usuario=current_user,
            )

        db.session.commit()

        flash(
            "Compromisso reaberto com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        flash(
            "Não foi possível reabrir o compromisso.",
            "danger",
        )

    return redirect(
        destino_apos_acao(evento),
    )


# ============================================================
# CANCELAR EVENTO
# ============================================================

@agenda_bp.route(
    "/<string:evento_id>/cancelar",
    methods=["POST"],
)
@login_required
def cancelar_evento(evento_id):
    evento = obter_evento_ou_404(
        evento_id,
    )

    if evento.status == "CANCELADO":
        flash(
            "Este compromisso já está cancelado.",
            "info",
        )

        return redirect(
            destino_apos_acao(evento),
        )

    try:
        status_anterior = evento.status
        evento.cancelar()

        if evento.caso:
            TimelineService.registrar_status_evento_agenda_alterado(
                caso=evento.caso,
                evento_agenda=evento,
                status_anterior=status_anterior,
                novo_status=evento.status,
                usuario=current_user,
            )

        db.session.commit()

        flash(
            "Compromisso cancelado com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        flash(
            "Não foi possível cancelar o compromisso.",
            "danger",
        )

    return redirect(
        destino_apos_acao(evento),
    )


# ============================================================
# EXCLUIR EVENTO
# ============================================================

@agenda_bp.route(
    "/<string:evento_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir_evento(evento_id):
    evento = obter_evento_ou_404(
        evento_id,
    )

    retorno = destino_apos_acao(
        evento,
    )

    try:
        if evento.caso:
            TimelineService.registrar_evento_agenda_excluido(
                caso=evento.caso,
                evento_agenda=evento,
                usuario=current_user,
            )

        db.session.delete(evento)
        db.session.commit()

        flash(
            "Compromisso excluído com sucesso.",
            "success",
        )

    except SQLAlchemyError:
        db.session.rollback()

        flash(
            (
                "Não foi possível excluir o compromisso. "
                "Tente novamente."
            ),
            "danger",
        )

    return redirect(
        retorno,
    )