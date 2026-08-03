from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import extract
from sqlalchemy.orm import joinedload, selectinload

from models.cliente import Cliente
from models.evento_agenda import EventoAgenda
from models.evento_caso import EventoCaso
from models.honorario import HonorarioCaso, ParcelaHonorario
from models.processo import Processo


dashboard_bp = Blueprint("dashboard", __name__)


MODULOS_TIMELINE = {
    "TODOS": {
        "rotulo": "Todos",
        "tipos": (),
    },
    "CASOS": {
        "rotulo": "Casos",
        "tipos": (
            EventoCaso.TIPO_CASO_CRIADO,
            EventoCaso.TIPO_CASO_EDITADO,
            EventoCaso.TIPO_STATUS_ALTERADO,
            EventoCaso.TIPO_PRIORIDADE_ALTERADA,
            EventoCaso.TIPO_RESPONSAVEL_ALTERADO,
        ),
    },
    "PROCESSOS": {
        "rotulo": "Processos",
        "tipos": (
            EventoCaso.TIPO_PROCESSO_CRIADO,
            EventoCaso.TIPO_PROCESSO_EDITADO,
            EventoCaso.TIPO_PROCESSO_EXCLUIDO,
        ),
    },
    "DOCUMENTOS": {
        "rotulo": "Documentos",
        "tipos": (
            EventoCaso.TIPO_DOCUMENTO_ENVIADO,
            EventoCaso.TIPO_DOCUMENTO_GERADO,
            EventoCaso.TIPO_DOCUMENTO_EXCLUIDO,
        ),
    },
    "HONORARIOS": {
        "rotulo": "Honorários",
        "tipos": (
            EventoCaso.TIPO_HONORARIO_CRIADO,
            EventoCaso.TIPO_HONORARIO_EDITADO,
            EventoCaso.TIPO_PAGAMENTO_REGISTRADO,
        ),
    },
    "ATENDIMENTOS": {
        "rotulo": "Atendimentos",
        "tipos": (
            EventoCaso.TIPO_ATENDIMENTO_CRIADO,
            EventoCaso.TIPO_ATENDIMENTO_EDITADO,
        ),
    },
    "AGENDA": {
        "rotulo": "Agenda",
        "tipos": (
            EventoCaso.TIPO_AGENDA_CRIADA,
            EventoCaso.TIPO_AGENDA_EDITADA,
            EventoCaso.TIPO_AGENDA_CONCLUIDA,
        ),
    },
}


def calcular_honorarios_pendentes():
    contratos = (
        HonorarioCaso.query
        .options(selectinload(HonorarioCaso.parcelas))
        .filter(
            HonorarioCaso.status.in_(
                [
                    "ATIVO",
                    "SUSPENSO",
                ]
            )
        )
        .all()
    )

    return sum(
        (
            contrato.saldo_pendente
            for contrato in contratos
        ),
        start=0,
    )


def calcular_recebimentos_mes(hoje):
    parcelas = (
        ParcelaHonorario.query
        .filter(
            ParcelaHonorario.status == "PAGO",
            ParcelaHonorario.data_pagamento.isnot(None),
            extract(
                "month",
                ParcelaHonorario.data_pagamento,
            ) == hoje.month,
            extract(
                "year",
                ParcelaHonorario.data_pagamento,
            ) == hoje.year,
        )
        .all()
    )

    return sum(
        (
            parcela.valor or 0
            for parcela in parcelas
        ),
        start=0,
    )


def calcular_cobrancas_atrasadas(hoje):
    return (
        ParcelaHonorario.query
        .filter(
            ParcelaHonorario.status.in_(
                [
                    "PENDENTE",
                    "ATRASADO",
                ]
            ),
            ParcelaHonorario.data_vencimento.isnot(None),
            ParcelaHonorario.data_vencimento < hoje,
        )
        .count()
    )


def carregar_atividades(modulo):
    consulta = (
        EventoCaso.query
        .options(
            joinedload(EventoCaso.caso),
            joinedload(EventoCaso.usuario),
        )
    )

    configuracao = MODULOS_TIMELINE.get(
        modulo,
        MODULOS_TIMELINE["TODOS"],
    )

    if configuracao["tipos"]:
        consulta = consulta.filter(
            EventoCaso.tipo.in_(
                configuracao["tipos"]
            )
        )

    return (
        consulta
        .order_by(EventoCaso.criado_em.desc())
        .limit(20)
        .all()
    )


def carregar_compromissos_hoje(hoje):
    return (
        EventoAgenda.query
        .options(
            joinedload(EventoAgenda.caso),
            joinedload(EventoAgenda.responsavel),
        )
        .filter(
            EventoAgenda.data == hoje,
            EventoAgenda.status.notin_(
                [
                    "CONCLUIDO",
                    "CANCELADO",
                ]
            ),
        )
        .order_by(
            EventoAgenda.hora_inicio.asc(),
            EventoAgenda.prioridade.desc(),
            EventoAgenda.criado_em.asc(),
        )
        .limit(8)
        .all()
    )


@dashboard_bp.route("/")
@login_required
def inicio():
    hoje = date.today()

    modulo = request.args.get(
        "modulo",
        "TODOS",
    ).strip().upper()

    if modulo not in MODULOS_TIMELINE:
        modulo = "TODOS"

    indicadores = {
        "clientes_ativos": (
            Cliente.query
            .filter_by(ativo=True)
            .count()
        ),
        "processos_ativos": (
            Processo.query
            .filter_by(situacao="ATIVO")
            .count()
        ),
        "honorarios_pendentes": (
            calcular_honorarios_pendentes()
        ),
        "recebimentos_mes": (
            calcular_recebimentos_mes(hoje)
        ),
        "cobrancas_atrasadas": (
            calcular_cobrancas_atrasadas(hoje)
        ),
        "compromissos_hoje": (
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
    }

    return render_template(
        "dashboard/inicio.html",
        indicadores=indicadores,
        atividades=carregar_atividades(modulo),
        compromissos_hoje=carregar_compromissos_hoje(hoje),
        modulos_timeline=MODULOS_TIMELINE,
        modulo_ativo=modulo,
        hoje=hoje,
    )