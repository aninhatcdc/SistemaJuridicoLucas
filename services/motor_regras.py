"""
Motor de regras do gerador de documentos.

Responsabilidades:
- avaliar condições;
- executar ações;
- alterar a configuração dos campos;
- devolver os campos processados;
- manter o motor desacoplado de Flask, banco de dados, HTML e DOCX.

O formato esperado das regras é:

[
    {
        "quando": {
            "campo": "cliente.estado_civil",
            "operador": "igual",
            "valor": "Casado"
        },
        "acoes": [
            {
                "tipo": "mostrar",
                "campo": "cliente.nome_conjuge"
            },
            {
                "tipo": "obrigatorio",
                "campo": "cliente.nome_conjuge"
            }
        ]
    }
]
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, MutableMapping, Sequence


OPERADOR_IGUAL = "igual"
OPERADOR_DIFERENTE = "diferente"
OPERADOR_MAIOR = "maior"
OPERADOR_MENOR = "menor"
OPERADOR_MAIOR_IGUAL = "maior_igual"
OPERADOR_MENOR_IGUAL = "menor_igual"
OPERADOR_CONTEM = "contem"
OPERADOR_NAO_CONTEM = "nao_contem"
OPERADOR_VAZIO = "vazio"
OPERADOR_NAO_VAZIO = "nao_vazio"
OPERADOR_COMECA_COM = "comeca_com"
OPERADOR_TERMINA_COM = "termina_com"
OPERADOR_ENTRE = "entre"

OPERADORES_SUPORTADOS = {
    OPERADOR_IGUAL,
    OPERADOR_DIFERENTE,
    OPERADOR_MAIOR,
    OPERADOR_MENOR,
    OPERADOR_MAIOR_IGUAL,
    OPERADOR_MENOR_IGUAL,
    OPERADOR_CONTEM,
    OPERADOR_NAO_CONTEM,
    OPERADOR_VAZIO,
    OPERADOR_NAO_VAZIO,
    OPERADOR_COMECA_COM,
    OPERADOR_TERMINA_COM,
    OPERADOR_ENTRE,
}

ACAO_MOSTRAR = "mostrar"
ACAO_OCULTAR = "ocultar"
ACAO_OBRIGATORIO = "obrigatorio"
ACAO_OPCIONAL = "opcional"
ACAO_SOMENTE_LEITURA = "somente_leitura"
ACAO_EDITAVEL = "editavel"
ACAO_VALOR = "valor"
ACAO_PLACEHOLDER = "placeholder"
ACAO_AJUDA = "ajuda"
ACAO_INSERIR_CLAUSULA = "inserir_clausula"

ACOES_SUPORTADAS = {
    ACAO_MOSTRAR,
    ACAO_OCULTAR,
    ACAO_OBRIGATORIO,
    ACAO_OPCIONAL,
    ACAO_SOMENTE_LEITURA,
    ACAO_EDITAVEL,
    ACAO_VALOR,
    ACAO_PLACEHOLDER,
    ACAO_AJUDA,
    ACAO_INSERIR_CLAUSULA,
}

ALIASES_OPERADORES = {
    "=": OPERADOR_IGUAL,
    "==": OPERADOR_IGUAL,
    "igual": OPERADOR_IGUAL,
    "equals": OPERADOR_IGUAL,
    "!=": OPERADOR_DIFERENTE,
    "<>": OPERADOR_DIFERENTE,
    "diferente": OPERADOR_DIFERENTE,
    ">": OPERADOR_MAIOR,
    "maior": OPERADOR_MAIOR,
    "<": OPERADOR_MENOR,
    "menor": OPERADOR_MENOR,
    ">=": OPERADOR_MAIOR_IGUAL,
    "maior_igual": OPERADOR_MAIOR_IGUAL,
    "maior_ou_igual": OPERADOR_MAIOR_IGUAL,
    "<=": OPERADOR_MENOR_IGUAL,
    "menor_igual": OPERADOR_MENOR_IGUAL,
    "menor_ou_igual": OPERADOR_MENOR_IGUAL,
    "contém": OPERADOR_CONTEM,
    "contem": OPERADOR_CONTEM,
    "contains": OPERADOR_CONTEM,
    "não contém": OPERADOR_NAO_CONTEM,
    "nao contém": OPERADOR_NAO_CONTEM,
    "não contem": OPERADOR_NAO_CONTEM,
    "nao contem": OPERADOR_NAO_CONTEM,
    "nao_contem": OPERADOR_NAO_CONTEM,
    "vazio": OPERADOR_VAZIO,
    "empty": OPERADOR_VAZIO,
    "não vazio": OPERADOR_NAO_VAZIO,
    "nao vazio": OPERADOR_NAO_VAZIO,
    "nao_vazio": OPERADOR_NAO_VAZIO,
    "not_empty": OPERADOR_NAO_VAZIO,
    "começa com": OPERADOR_COMECA_COM,
    "comeca com": OPERADOR_COMECA_COM,
    "começa_com": OPERADOR_COMECA_COM,
    "comeca_com": OPERADOR_COMECA_COM,
    "starts_with": OPERADOR_COMECA_COM,
    "termina com": OPERADOR_TERMINA_COM,
    "termina_com": OPERADOR_TERMINA_COM,
    "ends_with": OPERADOR_TERMINA_COM,
    "entre": OPERADOR_ENTRE,
    "between": OPERADOR_ENTRE,
}

ALIASES_ACOES = {
    "mostrar": ACAO_MOSTRAR,
    "show": ACAO_MOSTRAR,
    "ocultar": ACAO_OCULTAR,
    "hide": ACAO_OCULTAR,
    "obrigatorio": ACAO_OBRIGATORIO,
    "obrigatório": ACAO_OBRIGATORIO,
    "required": ACAO_OBRIGATORIO,
    "opcional": ACAO_OPCIONAL,
    "optional": ACAO_OPCIONAL,
    "somente leitura": ACAO_SOMENTE_LEITURA,
    "somente_leitura": ACAO_SOMENTE_LEITURA,
    "readonly": ACAO_SOMENTE_LEITURA,
    "editavel": ACAO_EDITAVEL,
    "editável": ACAO_EDITAVEL,
    "editable": ACAO_EDITAVEL,
    "valor": ACAO_VALOR,
    "value": ACAO_VALOR,
    "placeholder": ACAO_PLACEHOLDER,
    "ajuda": ACAO_AJUDA,
    "help": ACAO_AJUDA,
    "inserir clausula": ACAO_INSERIR_CLAUSULA,
    "inserir cláusula": ACAO_INSERIR_CLAUSULA,
    "inserir_clausula": ACAO_INSERIR_CLAUSULA,
    "insert_clause": ACAO_INSERIR_CLAUSULA,
}


class ErroRegra(ValueError):
    """Erro de configuração ou execução de uma regra."""


def _normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""

    return str(valor).strip().casefold()


def _normalizar_codigo(codigo: Any) -> str:
    return str(codigo or "").strip()


def normalizar_operador(operador: Any) -> str:
    chave = _normalizar_texto(operador).replace("-", "_")
    return ALIASES_OPERADORES.get(chave, chave)


def normalizar_acao(tipo: Any) -> str:
    chave = _normalizar_texto(tipo).replace("-", "_")
    return ALIASES_ACOES.get(chave, chave)


def esta_vazio(valor: Any) -> bool:
    if valor is None:
        return True

    if isinstance(valor, str):
        return valor.strip() == ""

    if isinstance(valor, Mapping):
        return len(valor) == 0

    if isinstance(valor, Sequence) and not isinstance(
        valor,
        (str, bytes, bytearray),
    ):
        return len(valor) == 0

    return False


def _para_decimal(valor: Any) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, Decimal):
        return valor

    if isinstance(valor, int):
        return Decimal(valor)

    if isinstance(valor, float):
        return Decimal(str(valor))

    texto = str(valor).strip()

    if not texto:
        return None

    texto = (
        texto.replace("R$", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )

    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def _para_data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    texto = str(valor or "").strip()

    if not texto:
        return None

    formatos = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    )

    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    return None


def _comparar_ordenavel(esquerda: Any, direita: Any) -> tuple[Any, Any]:
    esquerda_data = _para_data(esquerda)
    direita_data = _para_data(direita)

    if esquerda_data is not None and direita_data is not None:
        return esquerda_data, direita_data

    esquerda_numero = _para_decimal(esquerda)
    direita_numero = _para_decimal(direita)

    if esquerda_numero is not None and direita_numero is not None:
        return esquerda_numero, direita_numero

    return _normalizar_texto(esquerda), _normalizar_texto(direita)


def comparar(
    valor_atual: Any,
    operador: str,
    valor_esperado: Any = None,
) -> bool:
    operador_normalizado = normalizar_operador(operador)

    if operador_normalizado not in OPERADORES_SUPORTADOS:
        raise ErroRegra(f"Operador não suportado: {operador!r}")

    if operador_normalizado == OPERADOR_VAZIO:
        return esta_vazio(valor_atual)

    if operador_normalizado == OPERADOR_NAO_VAZIO:
        return not esta_vazio(valor_atual)

    if operador_normalizado == OPERADOR_IGUAL:
        if isinstance(valor_atual, bool) or isinstance(valor_esperado, bool):
            return _normalizar_texto(valor_atual) == _normalizar_texto(
                valor_esperado
            )

        esquerda, direita = _comparar_ordenavel(
            valor_atual,
            valor_esperado,
        )
        return esquerda == direita

    if operador_normalizado == OPERADOR_DIFERENTE:
        return not comparar(
            valor_atual,
            OPERADOR_IGUAL,
            valor_esperado,
        )

    if operador_normalizado == OPERADOR_CONTEM:
        if isinstance(valor_atual, Mapping):
            return valor_esperado in valor_atual

        if isinstance(valor_atual, Sequence) and not isinstance(
            valor_atual,
            (str, bytes, bytearray),
        ):
            esperado_normalizado = _normalizar_texto(valor_esperado)
            return any(
                _normalizar_texto(item) == esperado_normalizado
                for item in valor_atual
            )

        return _normalizar_texto(valor_esperado) in _normalizar_texto(
            valor_atual
        )

    if operador_normalizado == OPERADOR_NAO_CONTEM:
        return not comparar(
            valor_atual,
            OPERADOR_CONTEM,
            valor_esperado,
        )

    if operador_normalizado == OPERADOR_COMECA_COM:
        return _normalizar_texto(valor_atual).startswith(
            _normalizar_texto(valor_esperado)
        )

    if operador_normalizado == OPERADOR_TERMINA_COM:
        return _normalizar_texto(valor_atual).endswith(
            _normalizar_texto(valor_esperado)
        )

    if operador_normalizado == OPERADOR_ENTRE:
        if not isinstance(valor_esperado, Sequence) or isinstance(
            valor_esperado,
            (str, bytes, bytearray),
        ):
            raise ErroRegra(
                "O operador 'entre' exige uma lista com dois valores."
            )

        if len(valor_esperado) != 2:
            raise ErroRegra(
                "O operador 'entre' exige exatamente dois valores."
            )

        minimo, maximo = valor_esperado
        atual_comparavel, minimo_comparavel = _comparar_ordenavel(
            valor_atual,
            minimo,
        )
        _, maximo_comparavel = _comparar_ordenavel(
            valor_atual,
            maximo,
        )

        return minimo_comparavel <= atual_comparavel <= maximo_comparavel

    esquerda, direita = _comparar_ordenavel(
        valor_atual,
        valor_esperado,
    )

    if operador_normalizado == OPERADOR_MAIOR:
        return esquerda > direita

    if operador_normalizado == OPERADOR_MENOR:
        return esquerda < direita

    if operador_normalizado == OPERADOR_MAIOR_IGUAL:
        return esquerda >= direita

    if operador_normalizado == OPERADOR_MENOR_IGUAL:
        return esquerda <= direita

    return False


def _campo_para_dict(campo: Any) -> dict[str, Any]:
    if is_dataclass(campo):
        return deepcopy(asdict(campo))

    if isinstance(campo, Mapping):
        return deepcopy(dict(campo))

    if hasattr(campo, "__dict__"):
        return deepcopy(vars(campo))

    raise TypeError(
        "Cada campo deve ser um dicionário, dataclass ou objeto com __dict__."
    )


def _obter_valor_campo(campo: Mapping[str, Any]) -> Any:
    if "valor" in campo:
        return campo.get("valor")

    meta = campo.get("meta")

    if isinstance(meta, Mapping):
        return meta.get("valor")

    return None


def _montar_indice_campos(
    campos: Iterable[Mapping[str, Any]],
) -> dict[str, MutableMapping[str, Any]]:
    indice: dict[str, MutableMapping[str, Any]] = {}

    for campo in campos:
        codigo = _normalizar_codigo(campo.get("codigo"))

        if codigo:
            indice[codigo] = campo  # type: ignore[assignment]

    return indice


def _resolver_valor_contexto(
    codigo: str,
    campos_por_codigo: Mapping[str, Mapping[str, Any]],
    contexto: Mapping[str, Any] | None = None,
) -> Any:
    if codigo in campos_por_codigo:
        return _obter_valor_campo(campos_por_codigo[codigo])

    if not contexto:
        return None

    if codigo in contexto:
        return contexto[codigo]

    atual: Any = contexto

    for parte in codigo.split("."):
        if isinstance(atual, Mapping) and parte in atual:
            atual = atual[parte]
            continue

        return None

    return atual


def condicao_atendida(
    condicao: Mapping[str, Any],
    campos_por_codigo: Mapping[str, Mapping[str, Any]],
    contexto: Mapping[str, Any] | None = None,
) -> bool:
    campo_codigo = _normalizar_codigo(condicao.get("campo"))
    operador = condicao.get("operador", OPERADOR_IGUAL)
    valor_esperado = condicao.get("valor")

    if not campo_codigo:
        raise ErroRegra("A condição precisa informar o campo.")

    valor_atual = _resolver_valor_contexto(
        campo_codigo,
        campos_por_codigo,
        contexto,
    )

    return comparar(
        valor_atual,
        str(operador),
        valor_esperado,
    )


def _garantir_meta(campo: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    meta = campo.get("meta")

    if isinstance(meta, MutableMapping):
        return meta

    if isinstance(meta, Mapping):
        meta_convertido = dict(meta)
        campo["meta"] = meta_convertido
        return meta_convertido

    meta_novo: dict[str, Any] = {}
    campo["meta"] = meta_novo
    return meta_novo


def executar_acao(
    acao: Mapping[str, Any],
    campos_por_codigo: Mapping[str, MutableMapping[str, Any]],
    clausulas: list[dict[str, Any]] | None = None,
) -> None:
    tipo = normalizar_acao(acao.get("tipo"))
    campo_codigo = _normalizar_codigo(acao.get("campo"))

    if tipo not in ACOES_SUPORTADAS:
        raise ErroRegra(f"Ação não suportada: {acao.get('tipo')!r}")

    if tipo == ACAO_INSERIR_CLAUSULA:
        if clausulas is not None:
            clausulas.append(
                {
                    "codigo": acao.get("codigo") or campo_codigo,
                    "conteudo": acao.get("conteudo") or acao.get("valor"),
                    "posicao": acao.get("posicao"),
                    "ordem": acao.get("ordem"),
                }
            )
        return

    if not campo_codigo:
        raise ErroRegra(
            f"A ação {tipo!r} precisa informar o campo de destino."
        )

    campo = campos_por_codigo.get(campo_codigo)

    if campo is None:
        return

    meta = _garantir_meta(campo)

    if tipo == ACAO_MOSTRAR:
        campo["visivel"] = True
        meta["visivel"] = True
        return

    if tipo == ACAO_OCULTAR:
        campo["visivel"] = False
        meta["visivel"] = False
        return

    if tipo == ACAO_OBRIGATORIO:
        campo["obrigatoria"] = True
        campo["obrigatorio"] = True
        meta["obrigatoria"] = True
        meta["obrigatorio"] = True
        return

    if tipo == ACAO_OPCIONAL:
        campo["obrigatoria"] = False
        campo["obrigatorio"] = False
        meta["obrigatoria"] = False
        meta["obrigatorio"] = False
        return

    if tipo == ACAO_SOMENTE_LEITURA:
        campo["editavel"] = False
        campo["somente_leitura"] = True
        meta["editavel"] = False
        meta["somente_leitura"] = True
        return

    if tipo == ACAO_EDITAVEL:
        campo["editavel"] = True
        campo["somente_leitura"] = False
        meta["editavel"] = True
        meta["somente_leitura"] = False
        return

    if tipo == ACAO_VALOR:
        novo_valor = acao.get("valor")
        campo["valor"] = novo_valor
        campo["preenchida"] = not esta_vazio(novo_valor)
        return

    if tipo == ACAO_PLACEHOLDER:
        placeholder = acao.get("valor", "")
        campo["placeholder"] = placeholder
        meta["placeholder"] = placeholder
        return

    if tipo == ACAO_AJUDA:
        ajuda = acao.get("valor", "")
        campo["ajuda"] = ajuda
        meta["ajuda"] = ajuda
        return


def _preparar_campos(
    campos: Iterable[Any],
) -> list[dict[str, Any]]:
    preparados: list[dict[str, Any]] = []

    for campo_original in campos:
        campo = _campo_para_dict(campo_original)
        meta = _garantir_meta(campo)

        visivel_padrao = campo.get(
            "visivel",
            meta.get("visivel", True),
        )
        obrigatoria_padrao = campo.get(
            "obrigatoria",
            campo.get(
                "obrigatorio",
                meta.get(
                    "obrigatoria",
                    meta.get("obrigatorio", False),
                ),
            ),
        )
        editavel_padrao = campo.get(
            "editavel",
            meta.get("editavel", True),
        )

        campo["visivel"] = bool(visivel_padrao)
        campo["obrigatoria"] = bool(obrigatoria_padrao)
        campo["obrigatorio"] = bool(obrigatoria_padrao)
        campo["editavel"] = bool(editavel_padrao)
        campo["somente_leitura"] = not bool(editavel_padrao)

        meta["visivel"] = bool(visivel_padrao)
        meta["obrigatoria"] = bool(obrigatoria_padrao)
        meta["obrigatorio"] = bool(obrigatoria_padrao)
        meta["editavel"] = bool(editavel_padrao)
        meta["somente_leitura"] = not bool(editavel_padrao)

        preparados.append(campo)

    return preparados


def aplicar_regras(
    campos: Iterable[Any],
    regras: Iterable[Mapping[str, Any]] | None,
    contexto: Mapping[str, Any] | None = None,
    ignorar_erros: bool = False,
) -> dict[str, Any]:
    """
    Aplica regras sobre uma lista de campos.

    Retorno:
    {
        "campos": [...],
        "clausulas": [...],
        "regras_aplicadas": [...],
        "erros": [...]
    }
    """
    campos_processados = _preparar_campos(campos)
    campos_por_codigo = _montar_indice_campos(campos_processados)
    clausulas: list[dict[str, Any]] = []
    regras_aplicadas: list[int] = []
    erros: list[dict[str, Any]] = []

    for indice, regra in enumerate(regras or []):
        try:
            condicao = regra.get("quando") or regra.get("condicao")
            acoes = regra.get("acoes") or []

            if not isinstance(condicao, Mapping):
                raise ErroRegra(
                    "A regra precisa possuir uma condição em 'quando'."
                )

            if not isinstance(acoes, Sequence) or isinstance(
                acoes,
                (str, bytes, bytearray),
            ):
                raise ErroRegra(
                    "A propriedade 'acoes' precisa ser uma lista."
                )

            if not condicao_atendida(
                condicao,
                campos_por_codigo,
                contexto,
            ):
                continue

            for acao in acoes:
                if not isinstance(acao, Mapping):
                    raise ErroRegra(
                        "Cada ação precisa ser um objeto."
                    )

                executar_acao(
                    acao,
                    campos_por_codigo,
                    clausulas,
                )

            regras_aplicadas.append(indice)

        except Exception as erro:
            registro = {
                "indice": indice,
                "regra": deepcopy(dict(regra)),
                "erro": str(erro),
                "tipo_erro": erro.__class__.__name__,
            }
            erros.append(registro)

            if not ignorar_erros:
                raise ErroRegra(
                    f"Erro na regra de índice {indice}: {erro}"
                ) from erro

    return {
        "campos": campos_processados,
        "clausulas": clausulas,
        "regras_aplicadas": regras_aplicadas,
        "erros": erros,
    }


def filtrar_campos_visiveis(
    campos: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        deepcopy(dict(campo))
        for campo in campos
        if campo.get("visivel", True)
    ]


def separar_campos_por_preenchimento(
    campos: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    preenchidos: list[dict[str, Any]] = []
    faltantes: list[dict[str, Any]] = []

    for campo_original in campos:
        campo = deepcopy(dict(campo_original))

        if not campo.get("visivel", True):
            continue

        valor = campo.get("valor")
        obrigatoria = campo.get(
            "obrigatoria",
            campo.get("obrigatorio", False),
        )

        if not esta_vazio(valor):
            preenchidos.append(campo)
        elif obrigatoria:
            faltantes.append(campo)
        else:
            preenchidos.append(campo)

    return preenchidos, faltantes


__all__ = [
    "ACOES_SUPORTADAS",
    "OPERADORES_SUPORTADOS",
    "ErroRegra",
    "aplicar_regras",
    "comparar",
    "condicao_atendida",
    "esta_vazio",
    "executar_acao",
    "filtrar_campos_visiveis",
    "normalizar_acao",
    "normalizar_operador",
    "separar_campos_por_preenchimento",
]