from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from models import db
from models.modelo_documento import ModeloDocumento
from services.catalogo_variaveis import (
    listar_variaveis,
    obter_dados_variavel,
)
from services.regras_modelo import (
    ErroRegrasModelo,
    adicionar_regra_modelo,
    carregar_regras_modelo,
)


regras_modelo_bp = Blueprint(
    "regras_modelo",
    __name__,
    url_prefix="/modelos",
)


OPERADORES = [
    ("igual", "Igual a"),
    ("diferente", "Diferente de"),
    ("maior", "Maior que"),
    ("menor", "Menor que"),
    ("maior_igual", "Maior ou igual a"),
    ("menor_igual", "Menor ou igual a"),
    ("contem", "Contém"),
    ("nao_contem", "Não contém"),
    ("vazio", "Está vazio"),
    ("nao_vazio", "Não está vazio"),
    ("comeca_com", "Começa com"),
    ("termina_com", "Termina com"),
    ("entre", "Entre"),
]


ACOES = [
    ("mostrar", "Mostrar campo"),
    ("ocultar", "Ocultar campo"),
    ("obrigatorio", "Tornar obrigatório"),
    ("opcional", "Tornar opcional"),
    ("somente_leitura", "Tornar somente leitura"),
    ("editavel", "Tornar editável"),
    ("valor", "Definir valor"),
    ("placeholder", "Definir placeholder"),
    ("ajuda", "Definir texto de ajuda"),
    ("inserir_clausula", "Inserir cláusula"),
]


ROTULOS_OPERADORES = dict(OPERADORES)
ROTULOS_ACOES = dict(ACOES)


def _texto(valor: Any, padrao: str = "") -> str:
    if valor is None:
        return padrao

    texto = str(valor).strip()

    return texto or padrao


def _humanizar_codigo(codigo: Any) -> str:
    texto = _texto(codigo)

    if not texto:
        return "Campo não informado"

    dados = obter_dados_variavel(texto)

    if dados:
        return dados["descricao"]

    parte_final = texto.split(".")[-1]
    parte_final = parte_final.replace("_", " ").strip()

    if not parte_final:
        return texto

    return parte_final[0].upper() + parte_final[1:]


def _montar_variaveis_condicao(
    modelo: ModeloDocumento,
) -> list[dict[str, str]]:
    variaveis = []
    adicionadas = set()

    for item in listar_variaveis():
        codigo = _texto(item.get("codigo"))

        if not codigo or codigo in adicionadas:
            continue

        adicionadas.add(codigo)

        variaveis.append(
            {
                "codigo": codigo,
                "grupo": _texto(
                    item.get("grupo"),
                    "Outros",
                ),
                "descricao": _texto(
                    item.get("descricao"),
                    _humanizar_codigo(codigo),
                ),
            }
        )

    for codigo_original in modelo.variaveis:
        codigo = _texto(codigo_original)

        if not codigo or codigo in adicionadas:
            continue

        adicionadas.add(codigo)

        variaveis.append(
            {
                "codigo": codigo,
                "grupo": "modelo",
                "descricao": _humanizar_codigo(codigo),
            }
        )

    return sorted(
        variaveis,
        key=lambda item: (
            item["grupo"].lower(),
            item["descricao"].lower(),
            item["codigo"].lower(),
        ),
    )


def _montar_variaveis_acao(
    modelo: ModeloDocumento,
) -> list[dict[str, str]]:
    variaveis = []

    for codigo_original in modelo.variaveis:
        codigo = _texto(codigo_original)

        if not codigo:
            continue

        variaveis.append(
            {
                "codigo": codigo,
                "descricao": _humanizar_codigo(codigo),
            }
        )

    return sorted(
        variaveis,
        key=lambda item: (
            item["descricao"].lower(),
            item["codigo"].lower(),
        ),
    )


def _normalizar_condicao(
    regra: Mapping[str, Any],
) -> dict[str, Any]:
    condicao = regra.get("quando")

    if not isinstance(condicao, Mapping):
        condicao = regra.get("condicao")

    if not isinstance(condicao, Mapping):
        condicao = {}

    campo = _texto(
        condicao.get("campo")
        or condicao.get("variavel")
        or condicao.get("codigo")
    )

    operador = _texto(
        condicao.get("operador"),
        "igual",
    )

    valor = condicao.get("valor")

    return {
        "campo": campo,
        "campo_rotulo": _humanizar_codigo(campo),
        "operador": operador,
        "operador_rotulo": ROTULOS_OPERADORES.get(
            operador,
            operador,
        ),
        "valor": valor,
        "possui_valor": valor not in (None, ""),
    }


def _normalizar_acoes(
    regra: Mapping[str, Any],
) -> list[dict[str, Any]]:
    acoes = regra.get("acoes")

    if not isinstance(acoes, list):
        return []

    resultado = []

    for acao in acoes:
        if not isinstance(acao, Mapping):
            continue

        tipo = _texto(
            acao.get("tipo"),
            "acao",
        )

        campo = _texto(
            acao.get("campo")
            or acao.get("variavel")
            or acao.get("codigo")
        )

        valor = acao.get("valor")
        conteudo = acao.get("conteudo")

        resultado.append(
            {
                "tipo": tipo,
                "tipo_rotulo": ROTULOS_ACOES.get(
                    tipo,
                    tipo.replace("_", " ").capitalize(),
                ),
                "campo": campo,
                "campo_rotulo": (
                    _humanizar_codigo(campo)
                    if campo
                    else ""
                ),
                "valor": valor,
                "possui_valor": valor not in (None, ""),
                "conteudo": conteudo,
                "possui_conteudo": conteudo not in (None, ""),
            }
        )

    return resultado


def _normalizar_regra_listagem(
    regra_original: Mapping[str, Any],
    indice: int,
) -> dict[str, Any]:
    regra = dict(regra_original)

    nome = _texto(
        regra.get("nome")
        or regra.get("titulo"),
        f"Regra {indice + 1}",
    )

    ativa = regra.get("ativa", True)
    prioridade = regra.get("prioridade", indice + 1)

    return {
        "indice": indice,
        "id": _texto(regra.get("id")),
        "nome": nome,
        "descricao": _texto(regra.get("descricao")),
        "ativa": bool(ativa),
        "prioridade": prioridade,
        "condicao": _normalizar_condicao(regra),
        "acoes": _normalizar_acoes(regra),
    }


def _valor_condicao_formulario(
    operador: str,
    valor_principal: str,
    valor_final: str,
) -> Any:
    if operador in {"vazio", "nao_vazio"}:
        return None

    if operador == "entre":
        if not valor_principal or not valor_final:
            raise ErroRegrasModelo(
                "O operador “Entre” exige um valor inicial e um valor final."
            )

        return [
            valor_principal,
            valor_final,
        ]

    if not valor_principal:
        raise ErroRegrasModelo(
            "Informe o valor usado para comparar a condição."
        )

    return valor_principal


def _montar_acoes_formulario() -> list[dict[str, Any]]:
    tipos = request.form.getlist("acao_tipo[]")
    campos = request.form.getlist("acao_campo[]")
    valores = request.form.getlist("acao_valor[]")
    conteudos = request.form.getlist("acao_conteudo[]")

    quantidade = max(
        len(tipos),
        len(campos),
        len(valores),
        len(conteudos),
        0,
    )

    acoes = []

    for indice in range(quantidade):
        tipo = _texto(
            tipos[indice]
            if indice < len(tipos)
            else ""
        )

        campo = _texto(
            campos[indice]
            if indice < len(campos)
            else ""
        )

        valor = _texto(
            valores[indice]
            if indice < len(valores)
            else ""
        )

        conteudo = _texto(
            conteudos[indice]
            if indice < len(conteudos)
            else ""
        )

        if not tipo:
            continue

        acao: dict[str, Any] = {
            "tipo": tipo,
        }

        if tipo == "inserir_clausula":
            if not conteudo:
                raise ErroRegrasModelo(
                    f"A ação {indice + 1} precisa informar o conteúdo da cláusula."
                )

            acao["conteudo"] = conteudo

        else:
            if not campo:
                raise ErroRegrasModelo(
                    f"A ação {indice + 1} precisa informar o campo de destino."
                )

            acao["campo"] = campo

            if tipo in {
                "valor",
                "placeholder",
                "ajuda",
            }:
                if not valor:
                    raise ErroRegrasModelo(
                        f"A ação {indice + 1} precisa informar um valor."
                    )

                acao["valor"] = valor

        acoes.append(acao)

    if not acoes:
        raise ErroRegrasModelo(
            "Adicione pelo menos uma ação à regra."
        )

    return acoes


@regras_modelo_bp.route(
    "/<string:modelo_id>/regras",
)
@login_required
def listar(modelo_id):
    modelo = db.get_or_404(
        ModeloDocumento,
        modelo_id,
    )

    try:
        regras_originais = carregar_regras_modelo(
            modelo,
            incluir_inativas=True,
        )

    except ErroRegrasModelo as erro:
        current_app.logger.exception(
            "Erro ao carregar regras do modelo %s.",
            modelo.id,
        )

        flash(
            str(erro),
            "danger",
        )

        regras_originais = []

    regras = [
        _normalizar_regra_listagem(
            regra,
            indice,
        )
        for indice, regra in enumerate(
            regras_originais
        )
        if isinstance(regra, Mapping)
    ]

    regras.sort(
        key=lambda item: (
            item["prioridade"],
            item["nome"].lower(),
        )
    )

    total_ativas = sum(
        1
        for regra in regras
        if regra["ativa"]
    )

    return render_template(
        "modelos/regras/listar.html",
        modelo=modelo,
        regras=regras,
        total_regras=len(regras),
        total_ativas=total_ativas,
        total_inativas=(
            len(regras) - total_ativas
        ),
    )


@regras_modelo_bp.route(
    "/<string:modelo_id>/regras/nova",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def nova(modelo_id):
    modelo = db.get_or_404(
        ModeloDocumento,
        modelo_id,
    )

    variaveis_condicao = _montar_variaveis_condicao(
        modelo
    )

    variaveis_acao = _montar_variaveis_acao(
        modelo
    )

    dados_formulario = {
        "nome": "",
        "descricao": "",
        "prioridade": "10",
        "ativa": True,
        "campo_condicao": "",
        "operador": "igual",
        "valor_condicao": "",
        "valor_condicao_final": "",
    }

    if request.method == "POST":
        dados_formulario = {
            "nome": _texto(
                request.form.get("nome")
            ),
            "descricao": _texto(
                request.form.get("descricao")
            ),
            "prioridade": _texto(
                request.form.get("prioridade"),
                "10",
            ),
            "ativa": (
                request.form.get("ativa")
                == "on"
            ),
            "campo_condicao": _texto(
                request.form.get(
                    "campo_condicao"
                )
            ),
            "operador": _texto(
                request.form.get("operador"),
                "igual",
            ),
            "valor_condicao": _texto(
                request.form.get(
                    "valor_condicao"
                )
            ),
            "valor_condicao_final": _texto(
                request.form.get(
                    "valor_condicao_final"
                )
            ),
        }

        try:
            if not dados_formulario["nome"]:
                raise ErroRegrasModelo(
                    "Informe o nome da regra."
                )

            if not dados_formulario[
                "campo_condicao"
            ]:
                raise ErroRegrasModelo(
                    "Selecione o campo da condição."
                )

            try:
                prioridade = int(
                    dados_formulario["prioridade"]
                )
            except (TypeError, ValueError) as erro:
                raise ErroRegrasModelo(
                    "A prioridade precisa ser um número inteiro."
                ) from erro

            if prioridade < 0:
                raise ErroRegrasModelo(
                    "A prioridade não pode ser negativa."
                )

            valor_condicao = (
                _valor_condicao_formulario(
                    dados_formulario["operador"],
                    dados_formulario[
                        "valor_condicao"
                    ],
                    dados_formulario[
                        "valor_condicao_final"
                    ],
                )
            )

            condicao: dict[str, Any] = {
                "campo": dados_formulario[
                    "campo_condicao"
                ],
                "operador": dados_formulario[
                    "operador"
                ],
            }

            if dados_formulario[
                "operador"
            ] not in {
                "vazio",
                "nao_vazio",
            }:
                condicao["valor"] = valor_condicao

            regra = {
                "id": str(uuid.uuid4()),
                "nome": dados_formulario["nome"],
                "descricao": (
                    dados_formulario["descricao"]
                    or None
                ),
                "prioridade": prioridade,
                "ativa": dados_formulario["ativa"],
                "quando": condicao,
                "acoes": _montar_acoes_formulario(),
            }

            adicionar_regra_modelo(
                modelo=modelo,
                regra=regra,
            )

            flash(
                "Regra criada com sucesso.",
                "success",
            )

            return redirect(
                url_for(
                    "regras_modelo.listar",
                    modelo_id=modelo.id,
                )
            )

        except ErroRegrasModelo as erro:
            flash(
                str(erro),
                "danger",
            )

        except OSError:
            current_app.logger.exception(
                "Erro de arquivo ao salvar regra do modelo %s.",
                modelo.id,
            )

            flash(
                "Não foi possível salvar o arquivo de regras.",
                "danger",
            )

        except Exception:
            current_app.logger.exception(
                "Erro inesperado ao criar regra do modelo %s.",
                modelo.id,
            )

            flash(
                "Não foi possível criar a regra.",
                "danger",
            )

    return render_template(
        "modelos/regras/form.html",
        modelo=modelo,
        dados=dados_formulario,
        operadores=OPERADORES,
        tipos_acoes=ACOES,
        variaveis_condicao=variaveis_condicao,
        variaveis_acao=variaveis_acao,
    )