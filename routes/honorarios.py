import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import db
from models.caso import Caso
from models.cliente import Cliente
from models.area_juridica import AreaJuridica
from models.honorario import (
    HonorarioCaso,
    ParcelaHonorario,
)
from services.timeline_service import TimelineService


honorarios_bp = Blueprint(
    "honorarios",
    __name__,
    url_prefix="/honorarios",
)


TIPOS_COBRANCA = {
    "FIXO",
    "EXITO",
    "FIXO_EXITO",
    "CONSULTA",
    "MENSAL",
}

STATUS_HONORARIO = {
    "ATIVO",
    "QUITADO",
    "CANCELADO",
    "SUSPENSO",
}

STATUS_PARCELA = {
    "PENDENTE",
    "PAGO",
    "ATRASADO",
    "CANCELADO",
}


def moeda_para_decimal(valor):
    if valor is None:
        return Decimal("0.00")

    valor = str(valor).strip()

    if not valor:
        return Decimal("0.00")

    valor_limpo = (
        valor
        .replace("R$", "")
        .replace(" ", "")
    )

    if "," in valor_limpo:
        valor_limpo = (
            valor_limpo
            .replace(".", "")
            .replace(",", ".")
        )

    try:
        return Decimal(valor_limpo).quantize(
            Decimal("0.01")
        )

    except InvalidOperation:
        return Decimal("0.00")


def decimal_opcional(valor):
    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    return moeda_para_decimal(valor)


def data_formulario(valor):
    if not valor:
        return None

    try:
        return datetime.strptime(
            valor,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


def inteiro_positivo(valor, padrao=1):
    try:
        numero = int(valor)

        if numero < 1:
            return padrao

        return numero

    except (TypeError, ValueError):
        return padrao


def adicionar_meses(data_base, quantidade):
    mes_calculado = (
        data_base.month - 1 + quantidade
    )

    ano = (
        data_base.year
        + mes_calculado // 12
    )

    mes = (
        mes_calculado % 12
        + 1
    )

    ultimo_dia_mes = calendar.monthrange(
        ano,
        mes,
    )[1]

    dia = min(
        data_base.day,
        ultimo_dia_mes,
    )

    return date(
        ano,
        mes,
        dia,
    )


def dividir_valor_em_parcelas(
    valor,
    quantidade,
):
    if quantidade <= 0:
        return []

    valor = Decimal(
        str(valor or 0)
    ).quantize(
        Decimal("0.01")
    )

    valor_base = (
        valor / quantidade
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_DOWN,
    )

    valores = [
        valor_base
        for _ in range(quantidade)
    ]

    total_parcial = sum(
        valores,
        Decimal("0.00"),
    )

    diferenca = valor - total_parcial

    centavos_restantes = int(
        (
            diferenca
            * Decimal("100")
        ).to_integral_value()
    )

    for indice in range(
        centavos_restantes
    ):
        valores[indice] += Decimal("0.01")

    return valores



def formatar_data(valor):
    if not valor:
        return "Não informada"

    return valor.strftime("%d/%m/%Y")


def formatar_moeda(valor):
    if valor is None:
        return "R$ 0,00"

    valor_formatado = f"{valor:,.2f}"

    return (
        "R$ "
        + valor_formatado
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_percentual(valor):
    if valor is None:
        return "Não informado"

    return f"{valor}%"


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


def gerar_parcelas(honorario):
    quantidade = honorario.quantidade_parcelas or 1

    valor_total = Decimal(
        str(honorario.valor_total or 0)
    )

    valor_entrada = Decimal(
        str(honorario.valor_entrada or 0)
    )

    valor_parcelado = (
        valor_total - valor_entrada
    )

    if valor_parcelado < 0:
        valor_parcelado = Decimal("0.00")

    valores = dividir_valor_em_parcelas(
        valor_parcelado,
        quantidade,
    )

    for indice, valor_parcela in enumerate(
        valores,
        start=1,
    ):
        vencimento = None

        if honorario.primeiro_vencimento:
            vencimento = adicionar_meses(
                honorario.primeiro_vencimento,
                indice - 1,
            )

        parcela = ParcelaHonorario(
            numero=indice,
            valor=valor_parcela,
            data_vencimento=vencimento,
            forma_pagamento=(
                honorario.forma_pagamento
            ),
            status="PENDENTE",
            honorario=honorario,
        )

        db.session.add(parcela)


def atualizar_parcelas_atrasadas(
    honorario,
):
    hoje = date.today()
    alterado = False

    for parcela in honorario.parcelas:

        if (
            parcela.status == "PENDENTE"
            and parcela.data_vencimento
            and parcela.data_vencimento < hoje
        ):
            parcela.status = "ATRASADO"
            alterado = True

        elif (
            parcela.status == "ATRASADO"
            and parcela.data_vencimento
            and parcela.data_vencimento >= hoje
        ):
            parcela.status = "PENDENTE"
            alterado = True

    if alterado:
        db.session.commit()


def atualizar_status_honorario(
    honorario,
):
    parcelas_validas = [
        parcela
        for parcela in honorario.parcelas
        if parcela.status != "CANCELADO"
    ]

    if (
        parcelas_validas
        and all(
            parcela.status == "PAGO"
            for parcela in parcelas_validas
        )
    ):
        honorario.status = "QUITADO"

    elif (
        honorario.status == "QUITADO"
        and any(
            parcela.status != "PAGO"
            for parcela in parcelas_validas
        )
    ):
        honorario.status = "ATIVO"



@honorarios_bp.route("/")
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

    tipo_cobranca = request.args.get(
        "tipo_cobranca",
        "",
    ).strip().upper()

    area_id = request.args.get(
        "area_id",
        "",
    ).strip()

    cliente_id = request.args.get(
        "cliente_id",
        "",
    ).strip()

    consulta = (
        HonorarioCaso.query
        .options(
            joinedload(
                HonorarioCaso.caso
            ).joinedload(
                Caso.cliente
            ),
            joinedload(
                HonorarioCaso.caso
            ).joinedload(
                Caso.area_juridica
            ),
            joinedload(
                HonorarioCaso.parcelas
            ),
        )
        .join(
            Caso,
            HonorarioCaso.caso_id == Caso.id,
        )
        .join(
            Cliente,
            Caso.cliente_id == Cliente.id,
        )
        .outerjoin(
            AreaJuridica,
            Caso.area_juridica_id == AreaJuridica.id,
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

    if status in STATUS_HONORARIO:
        consulta = consulta.filter(
            HonorarioCaso.status == status
        )

    if tipo_cobranca in TIPOS_COBRANCA:
        consulta = consulta.filter(
            HonorarioCaso.tipo_cobranca
            == tipo_cobranca
        )

    if area_id:
        consulta = consulta.filter(
            AreaJuridica.id == area_id
        )

    if cliente_id:
        consulta = consulta.filter(
            Cliente.id == cliente_id
        )

    honorarios = (
        consulta
        .order_by(
            HonorarioCaso.criado_em.desc()
        )
        .all()
    )

    hoje = date.today()

    total_contratado = sum(
        (
            Decimal(
                str(
                    honorario.valor_total
                    or 0
                )
            )
            for honorario in honorarios
        ),
        Decimal("0.00"),
    )

    total_recebido = sum(
        (
            Decimal(
                str(
                    honorario.valor_entrada
                    or 0
                )
            )
            + Decimal(
                str(
                    honorario.total_pago
                    or 0
                )
            )
            for honorario in honorarios
        ),
        Decimal("0.00"),
    )

    total_pendente = sum(
        (
            Decimal(
                str(
                    honorario.saldo_pendente
                    or 0
                )
            )
            for honorario in honorarios
        ),
        Decimal("0.00"),
    )

    total_atrasado = Decimal("0.00")

    for honorario in honorarios:
        for parcela in honorario.parcelas:
            if (
                parcela.status
                not in {
                    "PAGO",
                    "CANCELADO",
                }
                and parcela.data_vencimento
                and parcela.data_vencimento
                < hoje
            ):
                total_atrasado += Decimal(
                    str(
                        parcela.valor
                        or 0
                    )
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
        "tipo_cobranca": tipo_cobranca,
        "area_id": area_id,
        "cliente_id": cliente_id,
    }

    return render_template(
        "honorarios/listar.html",
        honorarios=honorarios,
        clientes=clientes,
        areas=areas,
        filtros=filtros,
        total_contratado=formatar_moeda(
            total_contratado
        ),
        total_recebido=formatar_moeda(
            total_recebido
        ),
        total_pendente=formatar_moeda(
            total_pendente
        ),
        total_atrasado=formatar_moeda(
            total_atrasado
        ),
    )


@honorarios_bp.route(
    "/novo",
    methods=["GET", "POST"],
)
@login_required
def selecionar_caso_novo():
    casos = (
        Caso.query
        .options(
            joinedload(
                Caso.cliente
            ),
            joinedload(
                Caso.area_juridica
            ),
        )
        .order_by(
            Caso.criado_em.desc()
        )
        .all()
    )

    if request.method == "POST":
        caso_id = (
            request.form.get(
                "caso_id",
                "",
            ).strip()
        )

        if not caso_id:
            flash(
                "Selecione um caso para cadastrar os honorários.",
                "warning",
            )

            return render_template(
                "honorarios/selecionar_caso.html",
                casos=casos,
                caso_id_selecionado="",
            )

        caso = db.session.get(
            Caso,
            caso_id,
        )

        if not caso:
            flash(
                "O caso selecionado não foi encontrado.",
                "danger",
            )

            return render_template(
                "honorarios/selecionar_caso.html",
                casos=casos,
                caso_id_selecionado=caso_id,
            )

        return redirect(
            url_for(
                "honorarios.novo",
                caso_id=caso.id,
            )
        )

    return render_template(
        "honorarios/selecionar_caso.html",
        casos=casos,
        caso_id_selecionado="",
    )


@honorarios_bp.route(
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

        descricao = (
            request.form.get(
                "descricao",
                "",
            ).strip()
            or "Honorários advocatícios"
        )

        tipo_cobranca = (
            request.form.get(
                "tipo_cobranca",
                "FIXO",
            ).strip()
            or "FIXO"
        )

        status = (
            request.form.get(
                "status",
                "ATIVO",
            ).strip()
            or "ATIVO"
        )

        valor_total = moeda_para_decimal(
            request.form.get(
                "valor_total",
            )
        )

        valor_entrada = moeda_para_decimal(
            request.form.get(
                "valor_entrada",
            )
        )

        quantidade_parcelas = inteiro_positivo(
            request.form.get(
                "quantidade_parcelas",
            ),
            1,
        )

        percentual_exito = decimal_opcional(
            request.form.get(
                "percentual_exito",
            )
        )

        forma_pagamento = (
            request.form.get(
                "forma_pagamento",
                "",
            ).strip()
            or None
        )

        data_contrato = data_formulario(
            request.form.get(
                "data_contrato",
            )
        )

        primeiro_vencimento = data_formulario(
            request.form.get(
                "primeiro_vencimento",
            )
        )

        observacoes = (
            request.form.get(
                "observacoes",
                "",
            ).strip()
            or None
        )

        erros = []

        if tipo_cobranca not in TIPOS_COBRANCA:
            erros.append(
                "O tipo de cobrança informado é inválido."
            )

        if status not in STATUS_HONORARIO:
            erros.append(
                "O status informado é inválido."
            )

        if valor_total < 0:
            erros.append(
                "O valor total não pode ser negativo."
            )

        if valor_entrada < 0:
            erros.append(
                "O valor da entrada não pode ser negativo."
            )

        if valor_entrada > valor_total:
            erros.append(
                "O valor da entrada não pode ser maior que o valor total."
            )

        if (
            percentual_exito is not None
            and (
                percentual_exito < 0
                or percentual_exito > 100
            )
        ):
            erros.append(
                "O percentual de êxito deve estar entre 0 e 100."
            )

        if erros:
            for erro in erros:
                flash(
                    erro,
                    "danger",
                )

            return render_template(
                "honorarios/novo.html",
                caso=caso,
                dados=request.form,
            )

        honorario = HonorarioCaso(
            descricao=descricao,
            tipo_cobranca=tipo_cobranca,
            valor_total=valor_total,
            valor_entrada=valor_entrada,
            quantidade_parcelas=(
                quantidade_parcelas
            ),
            forma_pagamento=forma_pagamento,
            percentual_exito=percentual_exito,
            data_contrato=data_contrato,
            primeiro_vencimento=(
                primeiro_vencimento
            ),
            status=status,
            observacoes=observacoes,
            caso_id=caso.id,
        )

        try:
            db.session.add(honorario)
            db.session.flush()

            gerar_parcelas(honorario)
            db.session.flush()

            TimelineService.registrar_honorario_criado(
                caso=caso,
                honorario=honorario,
            )

            TimelineService.registrar_parcelamento_gerado(
                caso=caso,
                honorario=honorario,
            )

            db.session.commit()

            flash(
                "Contrato de honorários cadastrado e parcelas geradas com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "honorarios.detalhes",
                    honorario_id=honorario.id,
                )
            )

        except Exception as erro:
            db.session.rollback()

            print(
                "Erro ao cadastrar honorários:",
                erro,
            )

            flash(
                "Não foi possível cadastrar o contrato de honorários.",
                "danger",
            )

    return render_template(
        "honorarios/novo.html",
        caso=caso,
        dados={},
    )


@honorarios_bp.route(
    "/<string:honorario_id>",
)
@login_required
def detalhes(honorario_id):
    honorario = db.get_or_404(
        HonorarioCaso,
        honorario_id,
    )

    atualizar_parcelas_atrasadas(
        honorario
    )

    return render_template(
        "honorarios/detalhes.html",
        honorario=honorario,
        caso=honorario.caso,
    )


@honorarios_bp.route(
    "/<string:honorario_id>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(honorario_id):
    honorario = db.get_or_404(
        HonorarioCaso,
        honorario_id,
    )

    caso = honorario.caso

    if request.method == "POST":
        descricao_anterior = honorario.descricao
        tipo_cobranca_anterior = honorario.tipo_cobranca
        forma_pagamento_anterior = honorario.forma_pagamento
        percentual_exito_anterior = honorario.percentual_exito
        data_contrato_anterior = honorario.data_contrato
        status_anterior = honorario.status
        observacoes_anteriores = honorario.observacoes

        descricao = (
            request.form.get(
                "descricao",
                "",
            ).strip()
            or "Honorários advocatícios"
        )

        tipo_cobranca = (
            request.form.get(
                "tipo_cobranca",
                "FIXO",
            ).strip()
            or "FIXO"
        )

        status = (
            request.form.get(
                "status",
                "ATIVO",
            ).strip()
            or "ATIVO"
        )

        forma_pagamento = (
            request.form.get(
                "forma_pagamento",
                "",
            ).strip()
            or None
        )

        percentual_exito = decimal_opcional(
            request.form.get(
                "percentual_exito",
            )
        )

        data_contrato = data_formulario(
            request.form.get(
                "data_contrato",
            )
        )

        observacoes = (
            request.form.get(
                "observacoes",
                "",
            ).strip()
            or None
        )

        if tipo_cobranca not in TIPOS_COBRANCA:
            flash(
                "O tipo de cobrança informado é inválido.",
                "danger",
            )

            return render_template(
                "honorarios/editar.html",
                honorario=honorario,
                caso=caso,
            )

        if status not in STATUS_HONORARIO:
            flash(
                "O status informado é inválido.",
                "danger",
            )

            return render_template(
                "honorarios/editar.html",
                honorario=honorario,
                caso=caso,
            )

        if (
            percentual_exito is not None
            and (
                percentual_exito < 0
                or percentual_exito > 100
            )
        ):
            flash(
                "O percentual de êxito deve estar entre 0 e 100.",
                "danger",
            )

            return render_template(
                "honorarios/editar.html",
                honorario=honorario,
                caso=caso,
            )

        alteracoes = {}

        adicionar_alteracao(
            alteracoes,
            "descricao",
            "Descrição",
            descricao_anterior or "Não informada",
            descricao or "Não informada",
        )
        adicionar_alteracao(
            alteracoes,
            "tipo_cobranca",
            "Tipo de cobrança",
            tipo_cobranca_anterior or "Não informado",
            tipo_cobranca or "Não informado",
        )
        adicionar_alteracao(
            alteracoes,
            "forma_pagamento",
            "Forma de pagamento",
            forma_pagamento_anterior or "Não informada",
            forma_pagamento or "Não informada",
        )
        adicionar_alteracao(
            alteracoes,
            "percentual_exito",
            "Percentual de êxito",
            formatar_percentual(percentual_exito_anterior),
            formatar_percentual(percentual_exito),
        )
        adicionar_alteracao(
            alteracoes,
            "data_contrato",
            "Data do contrato",
            formatar_data(data_contrato_anterior),
            formatar_data(data_contrato),
        )
        adicionar_alteracao(
            alteracoes,
            "observacoes",
            "Observações",
            observacoes_anteriores or "Não informadas",
            observacoes or "Não informadas",
        )

        honorario.descricao = descricao
        honorario.tipo_cobranca = tipo_cobranca
        honorario.forma_pagamento = forma_pagamento
        honorario.percentual_exito = percentual_exito
        honorario.data_contrato = data_contrato
        honorario.status = status
        honorario.observacoes = observacoes

        try:
            if alteracoes:
                TimelineService.registrar_honorario_editado(
                    caso=caso,
                    honorario=honorario,
                    alteracoes=alteracoes,
                )

            if status_anterior != status:
                TimelineService.registrar_status_honorario_alterado(
                    caso=caso,
                    honorario=honorario,
                    status_anterior=status_anterior,
                    novo_status=status,
                )

            db.session.commit()

            flash(
                "Contrato de honorários atualizado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "honorarios.detalhes",
                    honorario_id=honorario.id,
                )
            )

        except Exception as erro:
            db.session.rollback()

            print(
                "Erro ao editar honorários:",
                erro,
            )

            flash(
                "Não foi possível atualizar o contrato.",
                "danger",
            )

    return render_template(
        "honorarios/editar.html",
        honorario=honorario,
        caso=caso,
    )


@honorarios_bp.route(
    "/<string:honorario_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir(honorario_id):
    honorario = db.get_or_404(
        HonorarioCaso,
        honorario_id,
    )

    caso = honorario.caso
    caso_id = honorario.caso_id

    try:
        TimelineService.registrar_honorario_excluido(
            caso=caso,
            honorario=honorario,
        )

        db.session.delete(honorario)
        db.session.commit()

        flash(
            "Contrato de honorários excluído com sucesso.",
            "success",
        )

    except Exception as erro:
        db.session.rollback()

        print(
            "Erro ao excluir honorários:",
            erro,
        )

        flash(
            "Não foi possível excluir o contrato de honorários.",
            "danger",
        )

    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso_id,
        )
    )


@honorarios_bp.route(
    "/parcela/<string:parcela_id>/pagar",
    methods=["POST"],
)
@login_required
def pagar_parcela(parcela_id):
    parcela = db.get_or_404(
        ParcelaHonorario,
        parcela_id,
    )

    parcela.data_pagamento = (
        data_formulario(
            request.form.get(
                "data_pagamento",
            )
        )
        or date.today()
    )

    parcela.forma_pagamento = (
        request.form.get(
            "forma_pagamento",
            "",
        ).strip()
        or parcela.honorario.forma_pagamento
    )

    parcela.observacoes = (
        request.form.get(
            "observacoes",
            "",
        ).strip()
        or parcela.observacoes
    )

    parcela.status = "PAGO"

    try:
        honorario = parcela.honorario
        status_honorario_anterior = honorario.status

        atualizar_status_honorario(honorario)

        TimelineService.registrar_pagamento_recebido(
            caso=honorario.caso,
            honorario=honorario,
            parcela=parcela,
        )

        if status_honorario_anterior != honorario.status:
            TimelineService.registrar_status_honorario_alterado(
                caso=honorario.caso,
                honorario=honorario,
                status_anterior=status_honorario_anterior,
                novo_status=honorario.status,
            )

        db.session.commit()

        flash(
            f"Parcela {parcela.numero} registrada como paga.",
            "success",
        )

    except Exception as erro:
        db.session.rollback()

        print(
            "Erro ao registrar pagamento:",
            erro,
        )

        flash(
            "Não foi possível registrar o pagamento.",
            "danger",
        )

    return redirect(
        url_for(
            "honorarios.detalhes",
            honorario_id=(
                parcela.honorario_id
            ),
        )
    )


@honorarios_bp.route(
    "/parcela/<string:parcela_id>/reabrir",
    methods=["POST"],
)
@login_required
def reabrir_parcela(parcela_id):
    parcela = db.get_or_404(
        ParcelaHonorario,
        parcela_id,
    )

    status_parcela_anterior = parcela.status
    parcela.data_pagamento = None

    if (
        parcela.data_vencimento
        and parcela.data_vencimento
        < date.today()
    ):
        parcela.status = "ATRASADO"

    else:
        parcela.status = "PENDENTE"

    try:
        honorario = parcela.honorario
        status_honorario_anterior = honorario.status

        atualizar_status_honorario(honorario)

        TimelineService.registrar_pagamento_reaberto(
            caso=honorario.caso,
            honorario=honorario,
            parcela=parcela,
            status_anterior=status_parcela_anterior,
        )

        if status_honorario_anterior != honorario.status:
            TimelineService.registrar_status_honorario_alterado(
                caso=honorario.caso,
                honorario=honorario,
                status_anterior=status_honorario_anterior,
                novo_status=honorario.status,
            )

        db.session.commit()

        flash(
            f"Pagamento da parcela {parcela.numero} foi desfeito.",
            "success",
        )

    except Exception as erro:
        db.session.rollback()

        print(
            "Erro ao reabrir parcela:",
            erro,
        )

        flash(
            "Não foi possível desfazer o pagamento.",
            "danger",
        )

    return redirect(
        url_for(
            "honorarios.detalhes",
            honorario_id=(
                parcela.honorario_id
            ),
        )
    )