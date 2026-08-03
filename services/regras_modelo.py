from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from services.motor_regras import (
    ACOES_SUPORTADAS,
    OPERADORES_SUPORTADOS,
    normalizar_acao,
    normalizar_operador,
)


NOME_PADRAO_ARQUIVO_REGRAS = "regras.json"
SUFIXO_PADRAO_REGRAS = ".regras.json"
VERSAO_ESTRUTURA_REGRAS = 1


class ErroRegrasModelo(ValueError):
    """Erro de leitura, validação ou gravação das regras de um modelo."""


def criar_estrutura_regras_vazia() -> dict[str, Any]:
    """
    Retorna a estrutura padrão usada para armazenar regras de um modelo.
    """
    return {
        "versao": VERSAO_ESTRUTURA_REGRAS,
        "regras": [],
    }


def criar_modelo_regras_vazio() -> dict[str, Any]:
    """
    Alias semântico para uso em rotas e telas administrativas.
    """
    return criar_estrutura_regras_vazia()


def _normalizar_caminho(valor: Any) -> Path | None:
    if valor is None:
        return None

    if isinstance(valor, Path):
        return valor

    texto = str(valor).strip()

    if not texto:
        return None

    return Path(texto)


def _obter_atributo_ou_chave(
    objeto: Any,
    nomes: Iterable[str],
) -> Any:
    if objeto is None:
        return None

    if isinstance(objeto, Mapping):
        for nome in nomes:
            if nome in objeto:
                valor = objeto.get(nome)

                if valor not in (None, ""):
                    return valor

        return None

    for nome in nomes:
        if hasattr(objeto, nome):
            valor = getattr(objeto, nome)

            if valor not in (None, ""):
                return valor

    return None


def obter_caminho_docx_modelo(modelo: Any) -> Path | None:
    """
    Tenta localizar o caminho do arquivo DOCX associado ao modelo.

    São aceitos objetos, dicionários ou caminhos diretos.
    """
    if isinstance(modelo, (str, Path)):
        caminho = _normalizar_caminho(modelo)

        if caminho and caminho.suffix.lower() == ".docx":
            return caminho

    valor = _obter_atributo_ou_chave(
        modelo,
        (
            "caminho_arquivo",
            "arquivo",
            "arquivo_docx",
            "caminho_docx",
            "template_path",
            "documento_path",
            "path",
        ),
    )

    caminho = _normalizar_caminho(valor)

    if caminho and caminho.suffix.lower() == ".docx":
        return caminho

    return caminho


def obter_caminho_regras_modelo(
    modelo: Any,
    diretorio_base: str | Path | None = None,
) -> Path:
    """
    Resolve o arquivo JSON de regras pertencente ao modelo.

    Prioridade:
    1. caminho explícito de regras no modelo;
    2. arquivo ao lado do DOCX, no formato nome.regras.json;
    3. pasta própria do modelo, usando regras.json;
    4. diretório base informado.
    """
    caminho_explicito = _obter_atributo_ou_chave(
        modelo,
        (
            "caminho_regras",
            "arquivo_regras",
            "regras_path",
            "regras_arquivo",
        ),
    )

    caminho = _normalizar_caminho(caminho_explicito)

    if caminho:
        if not caminho.is_absolute() and diretorio_base:
            return Path(diretorio_base) / caminho

        return caminho

    caminho_docx = obter_caminho_docx_modelo(modelo)

    if caminho_docx:
        if not caminho_docx.is_absolute() and diretorio_base:
            caminho_docx = Path(diretorio_base) / caminho_docx

        if caminho_docx.suffix:
            return caminho_docx.with_suffix(SUFIXO_PADRAO_REGRAS)

        return caminho_docx / NOME_PADRAO_ARQUIVO_REGRAS

    identificador = _obter_atributo_ou_chave(
        modelo,
        (
            "id",
            "uuid",
            "slug",
            "codigo",
            "nome_arquivo",
            "nome",
        ),
    )

    if diretorio_base:
        base = Path(diretorio_base)

        if identificador not in (None, ""):
            return base / str(identificador) / NOME_PADRAO_ARQUIVO_REGRAS

        return base / NOME_PADRAO_ARQUIVO_REGRAS

    raise ErroRegrasModelo(
        "Não foi possível determinar o caminho do arquivo de regras."
    )


def _normalizar_condicao(
    condicao: Mapping[str, Any],
    indice_regra: int,
) -> dict[str, Any]:
    campo = str(condicao.get("campo") or "").strip()
    operador_original = condicao.get("operador", "igual")
    operador = normalizar_operador(operador_original)

    if not campo:
        raise ErroRegrasModelo(
            f"Regra {indice_regra + 1}: a condição precisa informar o campo."
        )

    if operador not in OPERADORES_SUPORTADOS:
        raise ErroRegrasModelo(
            f"Regra {indice_regra + 1}: operador não suportado: "
            f"{operador_original!r}."
        )

    resultado = {
        "campo": campo,
        "operador": operador,
    }

    if operador not in {"vazio", "nao_vazio"}:
        if "valor" not in condicao:
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: o operador {operador!r} "
                "exige um valor de comparação."
            )

        resultado["valor"] = deepcopy(condicao.get("valor"))

    if operador == "entre":
        valor = resultado.get("valor")

        if (
            not isinstance(valor, Sequence)
            or isinstance(valor, (str, bytes, bytearray))
            or len(valor) != 2
        ):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: o operador 'entre' exige "
                "uma lista com exatamente dois valores."
            )

    return resultado


def _normalizar_acao(
    acao: Mapping[str, Any],
    indice_regra: int,
    indice_acao: int,
) -> dict[str, Any]:
    tipo_original = acao.get("tipo")
    tipo = normalizar_acao(tipo_original)
    campo = str(acao.get("campo") or "").strip()

    if tipo not in ACOES_SUPORTADAS:
        raise ErroRegrasModelo(
            f"Regra {indice_regra + 1}, ação {indice_acao + 1}: "
            f"tipo não suportado: {tipo_original!r}."
        )

    if tipo != "inserir_clausula" and not campo:
        raise ErroRegrasModelo(
            f"Regra {indice_regra + 1}, ação {indice_acao + 1}: "
            "o campo de destino é obrigatório."
        )

    resultado: dict[str, Any] = {
        "tipo": tipo,
    }

    if campo:
        resultado["campo"] = campo

    if tipo in {
        "valor",
        "placeholder",
        "ajuda",
    }:
        if "valor" not in acao:
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}, ação {indice_acao + 1}: "
                f"a ação {tipo!r} exige a propriedade 'valor'."
            )

        resultado["valor"] = deepcopy(acao.get("valor"))

    elif tipo == "inserir_clausula":
        conteudo = acao.get("conteudo", acao.get("valor"))

        if conteudo in (None, ""):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}, ação {indice_acao + 1}: "
                "a cláusula precisa possuir conteúdo."
            )

        resultado["conteudo"] = deepcopy(conteudo)

        for chave in (
            "codigo",
            "posicao",
            "ordem",
        ):
            if chave in acao:
                resultado[chave] = deepcopy(acao.get(chave))

    for chave in (
        "descricao",
        "observacao",
    ):
        if chave in acao:
            resultado[chave] = deepcopy(acao.get(chave))

    return resultado


def validar_regras(
    regras: Any,
) -> list[dict[str, Any]]:
    """
    Valida e normaliza uma lista de regras.

    Retorna uma nova lista pronta para o motor de regras.
    """
    if regras is None:
        return []

    if isinstance(regras, Mapping):
        if "regras" in regras:
            regras = regras.get("regras")
        else:
            raise ErroRegrasModelo(
                "A estrutura de regras precisa possuir a chave 'regras'."
            )

    if not isinstance(regras, Sequence) or isinstance(
        regras,
        (str, bytes, bytearray),
    ):
        raise ErroRegrasModelo(
            "As regras precisam ser fornecidas em uma lista."
        )

    regras_normalizadas: list[dict[str, Any]] = []

    for indice_regra, regra in enumerate(regras):
        if not isinstance(regra, Mapping):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: cada regra precisa ser um objeto."
            )

        ativa = bool(regra.get("ativa", True))

        condicao_original = regra.get(
            "quando",
            regra.get("condicao"),
        )

        if not isinstance(condicao_original, Mapping):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: informe a condição em 'quando'."
            )

        acoes_originais = regra.get("acoes")

        if not isinstance(acoes_originais, Sequence) or isinstance(
            acoes_originais,
            (str, bytes, bytearray),
        ):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: 'acoes' precisa ser uma lista."
            )

        if len(acoes_originais) == 0:
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: informe pelo menos uma ação."
            )

        regra_normalizada: dict[str, Any] = {
            "ativa": ativa,
            "quando": _normalizar_condicao(
                condicao_original,
                indice_regra,
            ),
            "acoes": [
                _normalizar_acao(
                    acao,
                    indice_regra,
                    indice_acao,
                )
                for indice_acao, acao in enumerate(acoes_originais)
                if isinstance(acao, Mapping)
            ],
        }

        if len(regra_normalizada["acoes"]) != len(acoes_originais):
            raise ErroRegrasModelo(
                f"Regra {indice_regra + 1}: todas as ações precisam "
                "ser objetos."
            )

        for chave in (
            "id",
            "nome",
            "descricao",
            "prioridade",
        ):
            if chave in regra:
                regra_normalizada[chave] = deepcopy(regra.get(chave))

        regras_normalizadas.append(regra_normalizada)

    return regras_normalizadas


def validar_estrutura_regras(
    estrutura: Any,
) -> dict[str, Any]:
    """
    Valida o documento JSON completo de regras.
    """
    if estrutura is None:
        return criar_estrutura_regras_vazia()

    if isinstance(estrutura, Sequence) and not isinstance(
        estrutura,
        (str, bytes, bytearray),
    ):
        estrutura = {
            "versao": VERSAO_ESTRUTURA_REGRAS,
            "regras": estrutura,
        }

    if not isinstance(estrutura, Mapping):
        raise ErroRegrasModelo(
            "O arquivo de regras precisa conter um objeto JSON."
        )

    versao = estrutura.get(
        "versao",
        VERSAO_ESTRUTURA_REGRAS,
    )

    try:
        versao = int(versao)
    except (TypeError, ValueError) as erro:
        raise ErroRegrasModelo(
            "A versão da estrutura de regras precisa ser numérica."
        ) from erro

    if versao > VERSAO_ESTRUTURA_REGRAS:
        raise ErroRegrasModelo(
            f"A versão {versao} ainda não é suportada pelo sistema."
        )

    regras_normalizadas = validar_regras(
        estrutura.get("regras", [])
    )

    resultado = {
        "versao": versao,
        "regras": regras_normalizadas,
    }

    for chave in (
        "modelo_id",
        "modelo_nome",
        "atualizado_em",
    ):
        if chave in estrutura:
            resultado[chave] = deepcopy(estrutura.get(chave))

    return resultado


def carregar_estrutura_regras_modelo(
    modelo: Any,
    diretorio_base: str | Path | None = None,
    criar_se_nao_existir: bool = False,
) -> dict[str, Any]:
    """
    Carrega a estrutura completa do arquivo JSON de regras.
    """
    caminho = obter_caminho_regras_modelo(
        modelo,
        diretorio_base,
    )

    if not caminho.exists():
        estrutura = criar_estrutura_regras_vazia()

        if criar_se_nao_existir:
            salvar_estrutura_regras_modelo(
                modelo=modelo,
                estrutura=estrutura,
                diretorio_base=diretorio_base,
            )

        return estrutura

    try:
        conteudo = caminho.read_text(
            encoding="utf-8"
        )
    except OSError as erro:
        raise ErroRegrasModelo(
            f"Não foi possível ler o arquivo de regras: {caminho}."
        ) from erro

    if not conteudo.strip():
        return criar_estrutura_regras_vazia()

    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError as erro:
        raise ErroRegrasModelo(
            f"O arquivo de regras possui JSON inválido: "
            f"linha {erro.lineno}, coluna {erro.colno}."
        ) from erro

    return validar_estrutura_regras(dados)


def carregar_regras_modelo(
    modelo: Any,
    diretorio_base: str | Path | None = None,
    incluir_inativas: bool = False,
    criar_se_nao_existir: bool = False,
) -> list[dict[str, Any]]:
    """
    Carrega somente a lista de regras pronta para o motor.
    """
    estrutura = carregar_estrutura_regras_modelo(
        modelo=modelo,
        diretorio_base=diretorio_base,
        criar_se_nao_existir=criar_se_nao_existir,
    )

    regras = estrutura["regras"]

    if incluir_inativas:
        return deepcopy(regras)

    return [
        deepcopy(regra)
        for regra in regras
        if regra.get("ativa", True)
    ]


def salvar_estrutura_regras_modelo(
    modelo: Any,
    estrutura: Any,
    diretorio_base: str | Path | None = None,
) -> Path:
    """
    Valida e salva a estrutura completa de regras no arquivo do modelo.
    """
    estrutura_validada = validar_estrutura_regras(
        estrutura
    )

    caminho = obter_caminho_regras_modelo(
        modelo,
        diretorio_base,
    )

    try:
        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        caminho.write_text(
            json.dumps(
                estrutura_validada,
                ensure_ascii=False,
                indent=4,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as erro:
        raise ErroRegrasModelo(
            f"Não foi possível salvar o arquivo de regras: {caminho}."
        ) from erro

    return caminho


def salvar_regras_modelo(
    modelo: Any,
    regras: Any,
    diretorio_base: str | Path | None = None,
    metadados: Mapping[str, Any] | None = None,
) -> Path:
    """
    Salva uma lista de regras no arquivo associado ao modelo.
    """
    estrutura = criar_estrutura_regras_vazia()
    estrutura["regras"] = validar_regras(regras)

    for chave, valor in (metadados or {}).items():
        if chave == "regras":
            continue

        estrutura[chave] = deepcopy(valor)

    return salvar_estrutura_regras_modelo(
        modelo=modelo,
        estrutura=estrutura,
        diretorio_base=diretorio_base,
    )


def adicionar_regra_modelo(
    modelo: Any,
    regra: Mapping[str, Any],
    diretorio_base: str | Path | None = None,
) -> dict[str, Any]:
    """
    Adiciona uma regra ao arquivo do modelo e retorna a estrutura salva.
    """
    estrutura = carregar_estrutura_regras_modelo(
        modelo=modelo,
        diretorio_base=diretorio_base,
    )

    regras = list(estrutura.get("regras", []))
    regras.append(dict(regra))

    estrutura["regras"] = validar_regras(regras)

    salvar_estrutura_regras_modelo(
        modelo=modelo,
        estrutura=estrutura,
        diretorio_base=diretorio_base,
    )

    return estrutura


def atualizar_regra_modelo(
    modelo: Any,
    indice: int,
    regra: Mapping[str, Any],
    diretorio_base: str | Path | None = None,
) -> dict[str, Any]:
    """
    Atualiza uma regra pelo índice.
    """
    estrutura = carregar_estrutura_regras_modelo(
        modelo=modelo,
        diretorio_base=diretorio_base,
    )

    regras = list(estrutura.get("regras", []))

    if indice < 0 or indice >= len(regras):
        raise ErroRegrasModelo(
            "A regra informada não existe."
        )

    regras[indice] = dict(regra)
    estrutura["regras"] = validar_regras(regras)

    salvar_estrutura_regras_modelo(
        modelo=modelo,
        estrutura=estrutura,
        diretorio_base=diretorio_base,
    )

    return estrutura


def remover_regra_modelo(
    modelo: Any,
    indice: int,
    diretorio_base: str | Path | None = None,
) -> dict[str, Any]:
    """
    Remove uma regra pelo índice.
    """
    estrutura = carregar_estrutura_regras_modelo(
        modelo=modelo,
        diretorio_base=diretorio_base,
    )

    regras = list(estrutura.get("regras", []))

    if indice < 0 or indice >= len(regras):
        raise ErroRegrasModelo(
            "A regra informada não existe."
        )

    regras.pop(indice)
    estrutura["regras"] = validar_regras(regras)

    salvar_estrutura_regras_modelo(
        modelo=modelo,
        estrutura=estrutura,
        diretorio_base=diretorio_base,
    )

    return estrutura


def ativar_ou_desativar_regra_modelo(
    modelo: Any,
    indice: int,
    ativa: bool,
    diretorio_base: str | Path | None = None,
) -> dict[str, Any]:
    """
    Ativa ou desativa uma regra pelo índice.
    """
    estrutura = carregar_estrutura_regras_modelo(
        modelo=modelo,
        diretorio_base=diretorio_base,
    )

    regras = list(estrutura.get("regras", []))

    if indice < 0 or indice >= len(regras):
        raise ErroRegrasModelo(
            "A regra informada não existe."
        )

    regra = dict(regras[indice])
    regra["ativa"] = bool(ativa)
    regras[indice] = regra

    estrutura["regras"] = validar_regras(regras)

    salvar_estrutura_regras_modelo(
        modelo=modelo,
        estrutura=estrutura,
        diretorio_base=diretorio_base,
    )

    return estrutura


__all__ = [
    "ErroRegrasModelo",
    "NOME_PADRAO_ARQUIVO_REGRAS",
    "SUFIXO_PADRAO_REGRAS",
    "VERSAO_ESTRUTURA_REGRAS",
    "adicionar_regra_modelo",
    "ativar_ou_desativar_regra_modelo",
    "atualizar_regra_modelo",
    "carregar_estrutura_regras_modelo",
    "carregar_regras_modelo",
    "criar_estrutura_regras_vazia",
    "criar_modelo_regras_vazio",
    "obter_caminho_docx_modelo",
    "obter_caminho_regras_modelo",
    "remover_regra_modelo",
    "salvar_estrutura_regras_modelo",
    "salvar_regras_modelo",
    "validar_estrutura_regras",
    "validar_regras",
]