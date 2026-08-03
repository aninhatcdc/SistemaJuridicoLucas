from datetime import datetime

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

from models import db
from models.cliente import Cliente


clientes_bp = Blueprint(
    "clientes",
    __name__,
    url_prefix="/clientes",
)


def converter_data(valor):
    if not valor:
        return None

    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def obter_texto_formulario(campo, padrao=None):
    valor = request.form.get(campo, "").strip()

    if valor:
        return valor

    return padrao


def obter_uf_formulario(campo):
    valor = request.form.get(campo, "").strip().upper()

    return valor or None


@clientes_bp.route("/")
@login_required
def listar():
    termo = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    consulta = Cliente.query

    if termo:
        busca = f"%{termo}%"

        consulta = consulta.filter(
            or_(
                Cliente.nome.ilike(busca),
                Cliente.cpf.ilike(busca),
                Cliente.rg.ilike(busca),
                Cliente.telefone.ilike(busca),
                Cliente.whatsapp.ilike(busca),
                Cliente.email.ilike(busca),
                Cliente.cidade.ilike(busca),
            )
        )

    if status == "ativos":
        consulta = consulta.filter(
            Cliente.ativo.is_(True)
        )

    elif status == "inativos":
        consulta = consulta.filter(
            Cliente.ativo.is_(False)
        )

    clientes = consulta.order_by(
        Cliente.ativo.desc(),
        Cliente.nome.asc(),
    ).all()

    return render_template(
        "clientes/listar.html",
        clientes=clientes,
        termo=termo,
        status=status,
    )


@clientes_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not nome:
            flash(
                "Informe o nome do cliente.",
                "danger",
            )

            return render_template(
                "clientes/novo.html",
                dados=request.form,
            )

        if not cpf:
            flash(
                "Informe o CPF do cliente.",
                "danger",
            )

            return render_template(
                "clientes/novo.html",
                dados=request.form,
            )

        cliente_com_cpf = Cliente.query.filter_by(
            cpf=cpf
        ).first()

        if cliente_com_cpf:
            flash(
                "Já existe um cliente cadastrado com esse CPF.",
                "danger",
            )

            return render_template(
                "clientes/novo.html",
                dados=request.form,
            )

        if email:
            cliente_com_email = Cliente.query.filter_by(
                email=email
            ).first()

            if cliente_com_email:
                flash(
                    "Já existe um cliente cadastrado com esse e-mail.",
                    "danger",
                )

                return render_template(
                    "clientes/novo.html",
                    dados=request.form,
                )

        cliente = Cliente(
            # Dados pessoais
            nome=nome,
            cpf=cpf,
            rg=obter_texto_formulario("rg"),
            orgao_expedidor=obter_texto_formulario(
                "orgao_expedidor"
            ),
            uf_rg=obter_uf_formulario("uf_rg"),
            data_nascimento=converter_data(
                request.form.get("data_nascimento")
            ),
            sexo=obter_texto_formulario("sexo"),
            nacionalidade=obter_texto_formulario(
                "nacionalidade",
                "Brasileira",
            ),
            naturalidade=obter_texto_formulario(
                "naturalidade"
            ),
            uf_naturalidade=obter_uf_formulario(
                "uf_naturalidade"
            ),
            estado_civil=obter_texto_formulario(
                "estado_civil"
            ),
            profissao=obter_texto_formulario(
                "profissao"
            ),

            # Filiação
            nome_mae=obter_texto_formulario(
                "nome_mae"
            ),
            nome_pai=obter_texto_formulario(
                "nome_pai"
            ),

            # Contato
            telefone=obter_texto_formulario(
                "telefone"
            ),
            whatsapp=obter_texto_formulario(
                "whatsapp"
            ),
            email=email or None,

            # Endereço
            cep=obter_texto_formulario("cep"),
            logradouro=obter_texto_formulario(
                "logradouro"
            ),
            numero=obter_texto_formulario(
                "numero"
            ),
            complemento=obter_texto_formulario(
                "complemento"
            ),
            bairro=obter_texto_formulario(
                "bairro"
            ),
            cidade=obter_texto_formulario(
                "cidade"
            ),
            estado=obter_uf_formulario(
                "estado"
            ),

            # Informações do cadastro
            origem=obter_texto_formulario(
                "origem"
            ),
            observacoes=obter_texto_formulario(
                "observacoes"
            ),
            ativo=True,
        )

        try:
            db.session.add(cliente)
            db.session.commit()

            flash(
                "Cliente cadastrado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "clientes.detalhes",
                    cliente_id=cliente.id,
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                "Não foi possível cadastrar o cliente.",
                "danger",
            )

            return render_template(
                "clientes/novo.html",
                dados=request.form,
            )

    return render_template(
        "clientes/novo.html",
        dados={},
    )


@clientes_bp.route("/<string:cliente_id>")
@login_required
def detalhes(cliente_id):
    cliente = db.get_or_404(
        Cliente,
        cliente_id,
    )

    return render_template(
        "clientes/detalhes.html",
        cliente=cliente,
    )


@clientes_bp.route(
    "/<string:cliente_id>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(cliente_id):
    cliente = db.get_or_404(
        Cliente,
        cliente_id,
    )

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not nome:
            flash(
                "Informe o nome do cliente.",
                "danger",
            )

            return render_template(
                "clientes/editar.html",
                cliente=cliente,
                dados=request.form,
            )

        if not cpf:
            flash(
                "Informe o CPF do cliente.",
                "danger",
            )

            return render_template(
                "clientes/editar.html",
                cliente=cliente,
                dados=request.form,
            )

        cliente_com_cpf = Cliente.query.filter(
            Cliente.cpf == cpf,
            Cliente.id != cliente.id,
        ).first()

        if cliente_com_cpf:
            flash(
                "Já existe outro cliente cadastrado com esse CPF.",
                "danger",
            )

            return render_template(
                "clientes/editar.html",
                cliente=cliente,
                dados=request.form,
            )

        if email:
            cliente_com_email = Cliente.query.filter(
                Cliente.email == email,
                Cliente.id != cliente.id,
            ).first()

            if cliente_com_email:
                flash(
                    "Já existe outro cliente cadastrado com esse e-mail.",
                    "danger",
                )

                return render_template(
                    "clientes/editar.html",
                    cliente=cliente,
                    dados=request.form,
                )

        # Dados pessoais
        cliente.nome = nome
        cliente.cpf = cpf
        cliente.rg = obter_texto_formulario(
            "rg"
        )
        cliente.orgao_expedidor = obter_texto_formulario(
            "orgao_expedidor"
        )
        cliente.uf_rg = obter_uf_formulario(
            "uf_rg"
        )
        cliente.data_nascimento = converter_data(
            request.form.get("data_nascimento")
        )
        cliente.sexo = obter_texto_formulario(
            "sexo"
        )
        cliente.nacionalidade = obter_texto_formulario(
            "nacionalidade",
            "Brasileira",
        )
        cliente.naturalidade = obter_texto_formulario(
            "naturalidade"
        )
        cliente.uf_naturalidade = obter_uf_formulario(
            "uf_naturalidade"
        )
        cliente.estado_civil = obter_texto_formulario(
            "estado_civil"
        )
        cliente.profissao = obter_texto_formulario(
            "profissao"
        )

        # Filiação
        cliente.nome_mae = obter_texto_formulario(
            "nome_mae"
        )
        cliente.nome_pai = obter_texto_formulario(
            "nome_pai"
        )

        # Contato
        cliente.telefone = obter_texto_formulario(
            "telefone"
        )
        cliente.whatsapp = obter_texto_formulario(
            "whatsapp"
        )
        cliente.email = email or None

        # Endereço
        cliente.cep = obter_texto_formulario(
            "cep"
        )
        cliente.logradouro = obter_texto_formulario(
            "logradouro"
        )
        cliente.numero = obter_texto_formulario(
            "numero"
        )
        cliente.complemento = obter_texto_formulario(
            "complemento"
        )
        cliente.bairro = obter_texto_formulario(
            "bairro"
        )
        cliente.cidade = obter_texto_formulario(
            "cidade"
        )
        cliente.estado = obter_uf_formulario(
            "estado"
        )

        # Informações do cadastro
        cliente.origem = obter_texto_formulario(
            "origem"
        )
        cliente.observacoes = obter_texto_formulario(
            "observacoes"
        )

        try:
            db.session.commit()

            flash(
                "Cliente atualizado com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "clientes.detalhes",
                    cliente_id=cliente.id,
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                "Não foi possível atualizar o cliente.",
                "danger",
            )

            return render_template(
                "clientes/editar.html",
                cliente=cliente,
                dados=request.form,
            )

    return render_template(
        "clientes/editar.html",
        cliente=cliente,
        dados={},
    )


@clientes_bp.post(
    "/<string:cliente_id>/alternar-status"
)
@login_required
def alternar_status(cliente_id):
    cliente = db.get_or_404(
        Cliente,
        cliente_id,
    )

    cliente.ativo = not cliente.ativo

    try:
        db.session.commit()

        mensagem = (
            "Cliente ativado com sucesso."
            if cliente.ativo
            else "Cliente desativado com sucesso."
        )

        flash(
            mensagem,
            "success",
        )

    except Exception:
        db.session.rollback()

        flash(
            "Não foi possível alterar o status do cliente.",
            "danger",
        )

    return redirect(
        request.referrer
        or url_for("clientes.listar")
    )