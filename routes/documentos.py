from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
)
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models.documento_caso import DocumentoCaso
from models.caso import Caso
from models.cliente import Cliente
from models.area_juridica import AreaJuridica
from models.usuario import Usuario


documentos_bp = Blueprint(
    "documentos",
    __name__,
    url_prefix="/documentos",
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


@documentos_bp.route("/")
@login_required
def listar():
    termo = request.args.get(
        "q",
        "",
    ).strip()

    cliente_id = request.args.get(
        "cliente_id",
        "",
    ).strip()

    caso_id = request.args.get(
        "caso_id",
        "",
    ).strip()

    area_id = request.args.get(
        "area_id",
        "",
    ).strip()

    tipo_documento = request.args.get(
        "tipo_documento",
        "",
    ).strip()

    extensao = request.args.get(
        "extensao",
        "",
    ).strip().lower()

    usuario_id = request.args.get(
        "usuario_id",
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
        DocumentoCaso.query
        .options(
            joinedload(
                DocumentoCaso.caso
            ).joinedload(
                Caso.cliente
            ),
            joinedload(
                DocumentoCaso.caso
            ).joinedload(
                Caso.area_juridica
            ),
            joinedload(
                DocumentoCaso.usuario
            ),
        )
        .join(
            Caso,
            DocumentoCaso.caso_id == Caso.id,
        )
        .join(
            Cliente,
            Caso.cliente_id == Cliente.id,
        )
        .outerjoin(
            AreaJuridica,
            Caso.area_juridica_id == AreaJuridica.id,
        )
        .outerjoin(
            Usuario,
            DocumentoCaso.usuario_id == Usuario.id,
        )
    )

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                DocumentoCaso.nome_original.ilike(
                    busca
                ),
                DocumentoCaso.tipo_documento.ilike(
                    busca
                ),
                DocumentoCaso.observacoes.ilike(
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

    if caso_id:
        consulta = consulta.filter(
            Caso.id == caso_id
        )

    if area_id:
        consulta = consulta.filter(
            AreaJuridica.id == area_id
        )

    if tipo_documento:
        consulta = consulta.filter(
            DocumentoCaso.tipo_documento
            == tipo_documento
        )

    if extensao:
        consulta = consulta.filter(
            func.lower(
                DocumentoCaso.extensao
            )
            == extensao
        )

    if usuario_id:
        consulta = consulta.filter(
            DocumentoCaso.usuario_id
            == usuario_id
        )

    if data_inicial:
        consulta = consulta.filter(
            func.date(
                DocumentoCaso.criado_em
            )
            >= data_inicial
        )

    if data_final:
        consulta = consulta.filter(
            func.date(
                DocumentoCaso.criado_em
            )
            <= data_final
        )

    documentos = (
        consulta
        .order_by(
            DocumentoCaso.criado_em.desc()
        )
        .all()
    )

    clientes = (
        Cliente.query
        .order_by(
            Cliente.nome.asc()
        )
        .all()
    )

    casos = (
        Caso.query
        .order_by(
            Caso.numero_interno.desc()
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

    usuarios = (
        Usuario.query
        .order_by(
            Usuario.nome.asc()
        )
        .all()
    )

    tipos_documento = [
        item[0]
        for item in (
            DocumentoCaso.query
            .with_entities(
                DocumentoCaso.tipo_documento
            )
            .filter(
                DocumentoCaso.tipo_documento
                .isnot(None)
            )
            .distinct()
            .order_by(
                DocumentoCaso.tipo_documento.asc()
            )
            .all()
        )
        if item[0]
    ]

    extensoes = [
        item[0]
        for item in (
            DocumentoCaso.query
            .with_entities(
                DocumentoCaso.extensao
            )
            .filter(
                DocumentoCaso.extensao
                .isnot(None)
            )
            .distinct()
            .order_by(
                DocumentoCaso.extensao.asc()
            )
            .all()
        )
        if item[0]
    ]

    total_documentos = len(documentos)

    total_bytes = sum(
        documento.tamanho_bytes or 0
        for documento in documentos
    )

    enviados_hoje = sum(
        1
        for documento in documentos
        if documento.criado_em
        and documento.criado_em.date()
        == datetime.now().date()
    )

    documentos_pdf = sum(
        1
        for documento in documentos
        if (
            documento.extensao or ""
        ).lower() == "pdf"
    )

    contexto_filtros = {
        "termo": termo,
        "cliente_id": cliente_id,
        "caso_id": caso_id,
        "area_id": area_id,
        "tipo_documento": tipo_documento,
        "extensao": extensao,
        "usuario_id": usuario_id,
        "data_inicial": data_inicial_texto,
        "data_final": data_final_texto,
    }

    return render_template(
        "documentos/listar.html",
        documentos=documentos,
        clientes=clientes,
        casos=casos,
        areas=areas,
        usuarios=usuarios,
        tipos_documento=tipos_documento,
        extensoes=extensoes,
        total_documentos=total_documentos,
        total_bytes=total_bytes,
        enviados_hoje=enviados_hoje,
        documentos_pdf=documentos_pdf,
        filtros=contexto_filtros,
    )