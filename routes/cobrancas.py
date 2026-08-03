from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from flask import (
    Blueprint,
    render_template,
    request,
)
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models.area_juridica import AreaJuridica
from models.caso import Caso
from models.cliente import Cliente
from models.honorario import (
    HonorarioCaso,
    ParcelaHonorario,
)


cobrancas_bp = Blueprint(
    "cobrancas",
    __name__,
    url_prefix="/cobrancas",
)


STATUS_VALIDOS = {
    "PENDENTE",
    "PAGO",
    "ATRASADO",
    "CANCELADO",
}


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


def formatar_moeda(valor):
    valor = Decimal(
        str(valor or 0)
    )

    texto = f"{valor:,.2f}"

    return (
        "R$ "
        + texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def limpar_numero_whatsapp(valor):
    numero = "".join(
        caractere
        for caractere in str(valor or "")
        if caractere.isdigit()
    )

    if not numero:
        return ""

    # Número brasileiro sem código do país.
    if len(numero) in {10, 11}:
        numero = f"55{numero}"

    return numero


def obter_numero_cliente(cliente):
    if not cliente:
        return ""

    return (
        getattr(cliente, "whatsapp", None)
        or getattr(cliente, "telefone", None)
        or ""
    )


def montar_url_whatsapp(parcela):
    cliente = parcela.honorario.caso.cliente
    numero = limpar_numero_whatsapp(
        obter_numero_cliente(cliente)
    )

    if not numero:
        return None

    vencimento = (
        parcela.data_vencimento.strftime(
            "%d/%m/%Y"
        )
        if parcela.data_vencimento
        else "data não informada"
    )

    mensagem = (
        f"Olá, {cliente.nome}. "
        f"Estamos entrando em contato sobre a parcela "
        f"{parcela.numero} de "
        f"{parcela.honorario.quantidade_parcelas}, "
        f"referente a {parcela.honorario.descricao}, "
        f"no valor de {parcela.valor_formatado}, "
        f"com vencimento em {vencimento}. "
        f"Em caso de dúvidas, estamos à disposição. "
        f"Lucas Tavares Advocacia e Consultoria Jurídica."
    )

    return (
        f"https://wa.me/{numero}"
        f"?text={quote(mensagem)}"
    )


def status_real_parcela(parcela):
    if parcela.status in {
        "PAGO",
        "CANCELADO",
    }:
        return parcela.status

    if (
        parcela.data_vencimento
        and parcela.data_vencimento < date.today()
    ):
        return "ATRASADO"

    return "PENDENTE"


@cobrancas_bp.route("/")
@login_required
def listar():
    termo = request.args.get(
        "q",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip().upper()

    cliente_id = request.args.get(
        "cliente_id",
        "",
    ).strip()

    area_id = request.args.get(
        "area_id",
        "",
    ).strip()

    data_inicial_texto = request.args.get(
        "data_inicial",
        "",
    ).strip()

    data_final_texto = request.args.get(
        "data_final",
        "",
    ).strip()

    data_inicial = converter_data(
        data_inicial_texto
    )

    data_final = converter_data(
        data_final_texto
    )

    consulta = (
        ParcelaHonorario.query
        .options(
            joinedload(
                ParcelaHonorario.honorario
            ).joinedload(
                HonorarioCaso.caso
            ).joinedload(
                Caso.cliente
            ),
            joinedload(
                ParcelaHonorario.honorario
            ).joinedload(
                HonorarioCaso.caso
            ).joinedload(
                Caso.area_juridica
            ),
        )
        .join(
            HonorarioCaso,
            ParcelaHonorario.honorario_id
            == HonorarioCaso.id,
        )
        .join(
            Caso,
            HonorarioCaso.caso_id
            == Caso.id,
        )
        .join(
            Cliente,
            Caso.cliente_id
            == Cliente.id,
        )
        .outerjoin(
            AreaJuridica,
            Caso.area_juridica_id
            == AreaJuridica.id,
        )
    )

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                HonorarioCaso.descricao.ilike(
                    busca
                ),
                Caso.numero_interno.ilike(
                    busca
                ),
                Caso.titulo.ilike(
                    busca
                ),
                Cliente.nome.ilike(
                    busca
                ),
                AreaJuridica.nome.ilike(
                    busca
                ),
            )
        )

    if cliente_id:
        consulta = consulta.filter(
            Cliente.id == cliente_id
        )

    if area_id:
        consulta = consulta.filter(
            AreaJuridica.id == area_id
        )

    if data_inicial:
        consulta = consulta.filter(
            ParcelaHonorario.data_vencimento
            >= data_inicial
        )

    if data_final:
        consulta = consulta.filter(
            ParcelaHonorario.data_vencimento
            <= data_final
        )

    parcelas = (
        consulta
        .order_by(
            ParcelaHonorario.data_vencimento.asc(),
            ParcelaHonorario.numero.asc(),
        )
        .all()
    )

    hoje = date.today()
    limite_sete_dias = hoje + timedelta(
        days=7
    )

    for parcela in parcelas:
        parcela.status_exibicao = (
            status_real_parcela(
                parcela
            )
        )

        parcela.whatsapp_url = (
            montar_url_whatsapp(
                parcela
            )
        )

    if status in STATUS_VALIDOS:
        parcelas = [
            parcela
            for parcela in parcelas
            if parcela.status_exibicao
            == status
        ]

    receber_hoje = sum(
        (
            Decimal(
                str(
                    parcela.valor
                    or 0
                )
            )
            for parcela in parcelas
            if (
                parcela.status_exibicao
                in {
                    "PENDENTE",
                    "ATRASADO",
                }
                and parcela.data_vencimento
                == hoje
            )
        ),
        Decimal("0.00"),
    )

    total_atrasado = sum(
        (
            Decimal(
                str(
                    parcela.valor
                    or 0
                )
            )
            for parcela in parcelas
            if parcela.status_exibicao
            == "ATRASADO"
        ),
        Decimal("0.00"),
    )

    proximos_sete_dias = sum(
        (
            Decimal(
                str(
                    parcela.valor
                    or 0
                )
            )
            for parcela in parcelas
            if (
                parcela.status_exibicao
                == "PENDENTE"
                and parcela.data_vencimento
                and hoje
                <= parcela.data_vencimento
                <= limite_sete_dias
            )
        ),
        Decimal("0.00"),
    )

    recebido_mes = sum(
        (
            Decimal(
                str(
                    parcela.valor
                    or 0
                )
            )
            for parcela in parcelas
            if (
                parcela.status_exibicao
                == "PAGO"
                and parcela.data_pagamento
                and parcela.data_pagamento.year
                == hoje.year
                and parcela.data_pagamento.month
                == hoje.month
            )
        ),
        Decimal("0.00"),
    )

    total_em_aberto = sum(
        (
            Decimal(
                str(
                    parcela.valor
                    or 0
                )
            )
            for parcela in parcelas
            if parcela.status_exibicao
            in {
                "PENDENTE",
                "ATRASADO",
            }
        ),
        Decimal("0.00"),
    )

    clientes = (
        Cliente.query
        .order_by(
            Cliente.nome.asc()
        )
        .all()
    )

    areas = (
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

    filtros = {
        "termo": termo,
        "status": status,
        "cliente_id": cliente_id,
        "area_id": area_id,
        "data_inicial": data_inicial_texto,
        "data_final": data_final_texto,
    }

    return render_template(
        "cobrancas/listar.html",
        parcelas=parcelas,
        clientes=clientes,
        areas=areas,
        filtros=filtros,
        receber_hoje=formatar_moeda(
            receber_hoje
        ),
        total_atrasado=formatar_moeda(
            total_atrasado
        ),
        proximos_sete_dias=formatar_moeda(
            proximos_sete_dias
        ),
        recebido_mes=formatar_moeda(
            recebido_mes
        ),
        total_em_aberto=formatar_moeda(
            total_em_aberto
        ),
        hoje=hoje,
    )