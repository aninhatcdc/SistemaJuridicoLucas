from datetime import date

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import or_
from services.timeline_service import TimelineService

from models import db
from models.area_juridica import AreaJuridica
from models.caso import Caso
from models.cliente import Cliente
from models.status_caso import StatusCaso
from models.usuario import Usuario
from models.documento_caso import DocumentoCaso
from models.processo import Processo
from models.honorario import HonorarioCaso
from models.modelo_documento import (
    ModeloDocumento,
)
from models.atendimento_caso import AtendimentoCaso
from models.formulario_caso import FormularioCaso


casos_bp = Blueprint(
    "casos",
    __name__,
    url_prefix="/casos",
)


def gerar_numero_interno():
    ano_atual = date.today().year
    prefixo = f"{ano_atual}-"

    ultimo_caso = (
        Caso.query
        .filter(Caso.numero_interno.like(f"{prefixo}%"))
        .order_by(Caso.numero_interno.desc())
        .first()
    )

    if not ultimo_caso:
        proximo_numero = 1
    else:
        try:
            sequencial_atual = int(
                ultimo_caso.numero_interno.split("-")[-1]
            )
            proximo_numero = sequencial_atual + 1
        except (ValueError, IndexError):
            proximo_numero = 1

    return f"{ano_atual}-{proximo_numero:04d}"


@casos_bp.route("/")
@login_required
def listar():
    termo = request.args.get("q", "").strip()
    area_id = request.args.get("area_id", "").strip()
    status_id = request.args.get("status_id", "").strip()

    consulta = Caso.query

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.join(Cliente).filter(
            or_(
                Caso.numero_interno.ilike(busca),
                Caso.titulo.ilike(busca),
                Caso.descricao.ilike(busca),
                Cliente.nome.ilike(busca),
                Cliente.cpf.ilike(busca),
            )
        )

    if area_id:
        consulta = consulta.filter(
            Caso.area_juridica_id == area_id
        )

    if status_id:
        consulta = consulta.filter(
            Caso.status_id == status_id
        )

    casos = (
        consulta
        .order_by(
            Caso.data_abertura.desc(),
            Caso.numero_interno.desc(),
        )
        .all()
    )

    areas = (
        AreaJuridica.query
        .filter_by(ativa=True)
        .order_by(
            AreaJuridica.ordem.asc(),
            AreaJuridica.nome.asc(),
        )
        .all()
    )

    status_casos = (
        StatusCaso.query
        .filter_by(ativo=True)
        .order_by(
            StatusCaso.ordem.asc(),
            StatusCaso.nome.asc(),
        )
        .all()
    )

    return render_template(
        "casos/listar.html",
        casos=casos,
        areas=areas,
        status_casos=status_casos,
        termo=termo,
        area_id=area_id,
        status_id=status_id,
    )


@casos_bp.route(
    "/novo/<string:cliente_id>",
    methods=["GET", "POST"],
)
@login_required
def novo(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)

    areas = (
        AreaJuridica.query
        .filter_by(ativa=True)
        .order_by(
            AreaJuridica.ordem.asc(),
            AreaJuridica.nome.asc(),
        )
        .all()
    )

    status_casos = (
        StatusCaso.query
        .filter_by(ativo=True)
        .order_by(
            StatusCaso.ordem.asc(),
            StatusCaso.nome.asc(),
        )
        .all()
    )

    responsaveis = (
        Usuario.query
        .filter_by(ativo=True)
        .order_by(Usuario.nome.asc())
        .all()
    )

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()

        area_juridica_id = request.form.get(
            "area_juridica_id",
            "",
        ).strip()

        status_id = request.form.get(
            "status_id",
            "",
        ).strip()

        responsavel_id = request.form.get(
            "responsavel_id",
            "",
        ).strip()

        prioridade = request.form.get(
            "prioridade",
            "NORMAL",
        ).strip().upper()

        prioridades_validas = {
            "BAIXA",
            "NORMAL",
            "ALTA",
            "URGENTE",
        }

        if not titulo:
            flash(
                "Informe o título do caso.",
                "danger",
            )

        elif not area_juridica_id:
            flash(
                "Selecione a área jurídica.",
                "danger",
            )

        elif not status_id:
            flash(
                "Selecione o status do caso.",
                "danger",
            )

        elif prioridade not in prioridades_validas:
            flash(
                "A prioridade selecionada é inválida.",
                "danger",
            )

        else:
            area = db.session.get(
                AreaJuridica,
                area_juridica_id,
            )

            status = db.session.get(
                StatusCaso,
                status_id,
            )

            responsavel = None

            if responsavel_id:
                responsavel = db.session.get(
                    Usuario,
                    responsavel_id,
                )

            if not area or not area.ativa:
                flash(
                    "A área jurídica selecionada é inválida.",
                    "danger",
                )

            elif not status or not status.ativo:
                flash(
                    "O status selecionado é inválido.",
                    "danger",
                )

            elif responsavel_id and not responsavel:
                flash(
                    "O responsável selecionado é inválido.",
                    "danger",
                )

            elif responsavel and not responsavel.ativo:
                flash(
                    "O responsável selecionado está inativo.",
                    "danger",
                )

            else:
                caso = Caso(
                    numero_interno=gerar_numero_interno(),
                    titulo=titulo,
                    descricao=(
                        request.form.get(
                            "descricao",
                            "",
                        ).strip()
                        or None
                    ),
                    observacoes=(
                        request.form.get(
                            "observacoes",
                            "",
                        ).strip()
                        or None
                    ),
                    prioridade=prioridade,
                    origem=(
                        request.form.get(
                            "origem",
                            "",
                        ).strip()
                        or None
                    ),
                    cliente_id=cliente.id,
                    area_juridica_id=area.id,
                    status_id=status.id,
                    responsavel_id=(
                        responsavel.id
                        if responsavel
                        else None
                    ),
                )

                try:
                    db.session.add(caso)
                    db.session.flush()

                    TimelineService.registrar_caso_criado(caso)

                    db.session.commit()

                    flash(
                        f"Caso {caso.numero_interno} criado com sucesso.",
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
                        "Não foi possível cadastrar o caso.",
                        "danger",
                    )

    return render_template(
        "casos/novo.html",
        cliente=cliente,
        areas=areas,
        status_casos=status_casos,
        responsaveis=responsaveis,
        dados=request.form,
    )


@casos_bp.route(
    "/<string:caso_id>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(caso_id):
    caso = db.get_or_404(Caso, caso_id)

    areas = (
        AreaJuridica.query
        .filter_by(ativa=True)
        .order_by(
            AreaJuridica.ordem.asc(),
            AreaJuridica.nome.asc(),
        )
        .all()
    )

    status_casos = (
        StatusCaso.query
        .filter_by(ativo=True)
        .order_by(
            StatusCaso.ordem.asc(),
            StatusCaso.nome.asc(),
        )
        .all()
    )

    responsaveis = (
        Usuario.query
        .filter_by(ativo=True)
        .order_by(Usuario.nome.asc())
        .all()
    )

    if request.method == "POST":
        titulo = request.form.get(
            "titulo",
            "",
        ).strip()

        area_juridica_id = request.form.get(
            "area_juridica_id",
            "",
        ).strip()

        status_id = request.form.get(
            "status_id",
            "",
        ).strip()

        responsavel_id = request.form.get(
            "responsavel_id",
            "",
        ).strip()

        prioridade = request.form.get(
            "prioridade",
            "NORMAL",
        ).strip().upper()

        prioridades_validas = {
            "BAIXA",
            "NORMAL",
            "ALTA",
            "URGENTE",
        }

        if not titulo:
            flash(
                "Informe o título do caso.",
                "danger",
            )

        elif not area_juridica_id:
            flash(
                "Selecione a área jurídica.",
                "danger",
            )

        elif not status_id:
            flash(
                "Selecione o status do caso.",
                "danger",
            )

        elif prioridade not in prioridades_validas:
            flash(
                "A prioridade selecionada é inválida.",
                "danger",
            )

        else:
            area = db.session.get(
                AreaJuridica,
                area_juridica_id,
            )

            status = db.session.get(
                StatusCaso,
                status_id,
            )

            responsavel = None

            if responsavel_id:
                responsavel = db.session.get(
                    Usuario,
                    responsavel_id,
                )

            if not area or not area.ativa:
                flash(
                    "A área jurídica selecionada é inválida.",
                    "danger",
                )

            elif not status or not status.ativo:
                flash(
                    "O status selecionado é inválido.",
                    "danger",
                )

            elif responsavel_id and not responsavel:
                flash(
                    "O responsável selecionado é inválido.",
                    "danger",
                )

            elif responsavel and not responsavel.ativo:
                flash(
                    "O responsável selecionado está inativo.",
                    "danger",
                )

            else:
                nova_origem = (
                    request.form.get(
                        "origem",
                        "",
                    ).strip()
                    or None
                )

                nova_descricao = (
                    request.form.get(
                        "descricao",
                        "",
                    ).strip()
                    or None
                )

                novas_observacoes = (
                    request.form.get(
                        "observacoes",
                        "",
                    ).strip()
                    or None
                )

                titulo_anterior = caso.titulo
                area_anterior = caso.area_juridica
                status_anterior = caso.status
                prioridade_anterior = caso.prioridade
                responsavel_anterior = caso.responsavel
                origem_anterior = caso.origem
                descricao_anterior = caso.descricao
                observacoes_anteriores = caso.observacoes

                alteracoes = {}

                if titulo_anterior != titulo:
                    alteracoes["titulo"] = {
                        "rotulo": "Título",
                        "anterior": titulo_anterior or "Não informado",
                        "novo": titulo or "Não informado",
                    }

                if area_anterior.id != area.id:
                    alteracoes["area_juridica"] = {
                        "rotulo": "Área jurídica",
                        "anterior": area_anterior.nome,
                        "novo": area.nome,
                    }

                if origem_anterior != nova_origem:
                    alteracoes["origem"] = {
                        "rotulo": "Origem",
                        "anterior": origem_anterior or "Não informada",
                        "novo": nova_origem or "Não informada",
                    }

                if descricao_anterior != nova_descricao:
                    alteracoes["descricao"] = {
                        "rotulo": "Descrição",
                        "anterior": descricao_anterior or "Não informada",
                        "novo": nova_descricao or "Não informada",
                    }

                if observacoes_anteriores != novas_observacoes:
                    alteracoes["observacoes"] = {
                        "rotulo": "Observações",
                        "anterior": (
                            observacoes_anteriores
                            or "Não informadas"
                        ),
                        "novo": (
                            novas_observacoes
                            or "Não informadas"
                        ),
                    }

                caso.titulo = titulo
                caso.area_juridica_id = area.id
                caso.status_id = status.id
                caso.prioridade = prioridade
                caso.responsavel_id = (
                    responsavel.id
                    if responsavel
                    else None
                )
                caso.origem = nova_origem
                caso.descricao = nova_descricao
                caso.observacoes = novas_observacoes

                try:
                    if alteracoes:
                        TimelineService.registrar_caso_editado(
                            caso,
                            alteracoes=alteracoes,
                        )

                    if status_anterior.id != status.id:
                        TimelineService.registrar_status_alterado(
                            caso,
                            status_anterior,
                            status,
                        )

                    if prioridade_anterior != prioridade:
                        TimelineService.registrar_prioridade_alterada(
                            caso,
                            prioridade_anterior,
                            prioridade,
                        )

                    responsavel_anterior_id = (
                        responsavel_anterior.id
                        if responsavel_anterior
                        else None
                    )
                    novo_responsavel_id = (
                        responsavel.id
                        if responsavel
                        else None
                    )

                    if responsavel_anterior_id != novo_responsavel_id:
                        TimelineService.registrar_responsavel_alterado(
                            caso,
                            responsavel_anterior,
                            responsavel,
                        )

                    db.session.commit()

                    flash(
                        f"Caso {caso.numero_interno} atualizado com sucesso.",
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
                        "Não foi possível atualizar o caso.",
                        "danger",
                    )

    return render_template(
        "casos/editar.html",
        caso=caso,
        areas=areas,
        status_casos=status_casos,
        responsaveis=responsaveis,
        dados=request.form,
    )


@casos_bp.route("/<string:caso_id>")
@login_required
def detalhes(caso_id):
    caso = db.get_or_404(
        Caso,
        caso_id,
    )

    documentos = (
        DocumentoCaso.query
        .filter_by(caso_id=caso.id)
        .order_by(
            DocumentoCaso.criado_em.desc()
        )
        .all()
    )

    processos = (
        Processo.query
        .filter_by(caso_id=caso.id)
        .order_by(
            Processo.criado_em.desc()
        )
        .all()
    )

    atendimentos = (
        AtendimentoCaso.query
        .filter_by(caso_id=caso.id)
        .order_by(
            AtendimentoCaso.data_atendimento.desc()
        )
        .all()
    )

    formularios_caso = (
        FormularioCaso.query
        .filter_by(caso_id=caso.id)
        .order_by(
            FormularioCaso.criado_em.desc()
        )
        .all()
    )

    modelos_documentos = (
        ModeloDocumento.query
        .filter(
            ModeloDocumento.ativo.is_(True)
        )
        .order_by(
            ModeloDocumento.nome.asc()
        )
        .all()
    )

    honorario = (
        HonorarioCaso.query
        .filter_by(caso_id=caso.id)
        .order_by(
            HonorarioCaso.criado_em.desc()
        )
        .first()
    )

    eventos = TimelineService.listar_eventos_do_caso(
        caso.id
    )

    return render_template(
        "casos/detalhes.html",
        caso=caso,
        documentos=documentos,
        processos=processos,
        atendimentos=atendimentos,
        formularios_caso=formularios_caso,
        modelos_documentos=modelos_documentos,
        honorario=honorario,
        eventos=eventos,
    )


@casos_bp.post(
    "/<string:caso_id>/excluir"
)
@login_required
def excluir(caso_id):
    caso = db.get_or_404(
        Caso,
        caso_id,
    )

    cliente_id = caso.cliente_id
    numero_interno = caso.numero_interno

    try:
        db.session.delete(
            caso
        )

        db.session.commit()

        flash(
            f"Caso {numero_interno} excluído com sucesso.",
            "success",
        )

        return redirect(
            url_for(
                "clientes.detalhes",
                cliente_id=cliente_id,
            )
        )

    except Exception:
        db.session.rollback()

        flash(
            "Não foi possível excluir o caso. "
            "Verifique se ainda existem registros vinculados.",
            "danger",
        )

        return redirect(
            url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        )
