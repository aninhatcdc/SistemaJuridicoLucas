from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from services.catalogo_variaveis import (
    normalizar_codigo,
    obter_dados_variavel,
)
from services.motor_regras import (
    aplicar_regras,
)


VALORES_CONSIDERADOS_VAZIOS = (
    None,
    "",
)


# Variáveis que podem permanecer vazias sem impedir a geração.
# Esta flexibilização é útil para a entrega inicial do sistema.
VARIAVEIS_OPCIONAIS_GLOBAIS = {
    "escritorio.cnpj",
    "empregador_cnpj",
    "cliente.uf_rg",
    "documentos_apresentados",
}


def valor_esta_preenchido(valor: Any) -> bool:
    """
    Retorna True quando o valor pode ser utilizado na geração.

    Valores como zero, False e listas não vazias são considerados
    preenchidos. Apenas None, texto vazio ou coleções vazias são
    tratados como ausentes.
    """
    if valor in VALORES_CONSIDERADOS_VAZIOS:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    if isinstance(valor, Mapping):
        return bool(valor)

    if isinstance(
        valor,
        (list, tuple, set, frozenset),
    ):
        return bool(valor)

    return True


def extrair_codigo_variavel(
    variavel: Any,
) -> str:
    """
    Extrai o código de uma variável recebida como texto ou dicionário.

    Formatos aceitos:
        "cliente.nome"
        {"codigo": "cliente.nome"}
        {"variavel": "cliente.nome"}
        {"nome": "cliente.nome"}
    """
    if isinstance(variavel, str):
        return normalizar_codigo(variavel)

    if isinstance(variavel, Mapping):
        for chave in (
            "codigo",
            "variavel",
            "nome",
        ):
            codigo = normalizar_codigo(
                variavel.get(chave)
            )

            if codigo:
                return codigo

    return ""


def normalizar_variaveis(
    variaveis: Iterable[Any] | None,
) -> list[str]:
    """
    Normaliza, remove duplicidades e preserva a ordem das variáveis.
    """
    resultado: list[str] = []
    adicionadas: set[str] = set()

    for variavel in variaveis or []:
        codigo = extrair_codigo_variavel(
            variavel
        )

        if (
            not codigo
            or codigo in adicionadas
        ):
            continue

        adicionadas.add(codigo)
        resultado.append(codigo)

    return resultado


def humanizar_codigo(
    codigo: str,
) -> str:
    """
    Converte um código técnico em um rótulo amigável.

    Exemplos:
        honorario.valor_total -> Valor total
        local_assinatura -> Local assinatura
    """
    codigo = normalizar_codigo(codigo)

    if not codigo:
        return "Campo"

    parte_final = codigo.split(".")[-1]
    texto = (
        parte_final
        .replace("_", " ")
        .strip()
    )

    if not texto:
        return codigo

    return (
        texto[0].upper()
        + texto[1:]
    )


def obter_metadados_variavel(
    codigo: str,
) -> dict[str, Any]:
    """
    Obtém os dados do catálogo ou cria metadados para uma variável
    personalizada encontrada no DOCX.
    """
    codigo = normalizar_codigo(codigo)
    dados_catalogo = obter_dados_variavel(
        codigo
    )

    if dados_catalogo:
        return {
            **deepcopy(dados_catalogo),
            "conhecida": True,
        }

    grupo = "personalizada"
    campo = codigo

    if "." in codigo:
        grupo, campo = codigo.split(
            ".",
            1,
        )

    return {
        "codigo": codigo,
        "grupo": (
            grupo
            or "personalizada"
        ),
        "campo": campo,
        "descricao": humanizar_codigo(
            codigo
        ),
        "tipo": "personalizada",
        "conhecida": False,
    }


def obter_valor_contexto(
    contexto: Mapping[str, Any] | None,
    codigo: str,
) -> Any:
    """
    Busca uma variável no contexto.

    Primeiro procura pela chave plana:

        cliente.nome

    Depois tenta percorrer um contexto aninhado:

        {
            "cliente": {
                "nome": "Ana"
            }
        }
    """
    if not contexto:
        return ""

    codigo = normalizar_codigo(codigo)

    if codigo in contexto:
        return contexto[codigo]

    atual: Any = contexto

    for parte in codigo.split("."):
        if (
            isinstance(atual, Mapping)
            and parte in atual
        ):
            atual = atual[parte]
            continue

        return ""

    return atual


def analisar_variaveis(
    variaveis: Iterable[Any] | None,
    contexto: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Analisa as variáveis antes da aplicação das regras.

    Por compatibilidade com o comportamento anterior do gerador,
    todas as variáveis começam visíveis e obrigatórias. Uma regra
    pode depois ocultá-las ou torná-las opcionais.
    """
    resultado: list[dict[str, Any]] = []

    for codigo in normalizar_variaveis(
        variaveis
    ):
        metadados = (
            obter_metadados_variavel(
                codigo
            )
        )

        valor = obter_valor_contexto(
            contexto,
            codigo,
        )

        preenchida = (
            valor_esta_preenchido(
                valor
            )
        )

        meta_original = metadados.get(
            "meta"
        )

        meta = (
            deepcopy(dict(meta_original))
            if isinstance(
                meta_original,
                Mapping,
            )
            else {}
        )

        visivel = bool(
            metadados.get(
                "visivel",
                meta.get(
                    "visivel",
                    True,
                ),
            )
        )

        obrigatoria = bool(
            metadados.get(
                "obrigatoria",
                metadados.get(
                    "obrigatorio",
                    meta.get(
                        "obrigatoria",
                        meta.get(
                            "obrigatorio",
                            True,
                        ),
                    ),
                ),
            )
        )

        # Campos abaixo são opcionais em qualquer modelo.
        # O placeholder continua sendo substituído quando houver valor,
        # mas sua ausência não bloqueia a geração do documento.
        if codigo in VARIAVEIS_OPCIONAIS_GLOBAIS:
            obrigatoria = False

        editavel = bool(
            metadados.get(
                "editavel",
                meta.get(
                    "editavel",
                    True,
                ),
            )
        )

        item = {
            **metadados,
            "codigo": codigo,
            "valor": valor,
            "preenchida": preenchida,
            "origem": (
                "automatica"
                if preenchida
                else "manual"
            ),
            "visivel": visivel,
            "obrigatoria": obrigatoria,
            "obrigatorio": obrigatoria,
            "editavel": editavel,
            "somente_leitura": (
                not editavel
            ),
            "meta": {
                **meta,
                "visivel": visivel,
                "obrigatoria": (
                    obrigatoria
                ),
                "obrigatorio": (
                    obrigatoria
                ),
                "editavel": editavel,
                "somente_leitura": (
                    not editavel
                ),
            },
        }

        resultado.append(item)

    return resultado


def aplicar_regras_resolucao(
    campos: Iterable[Mapping[str, Any]],
    regras: Iterable[
        Mapping[str, Any]
    ] | None = None,
    contexto: Mapping[str, Any] | None = None,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Aplica o motor de regras e normaliza o resultado para o resolvedor.
    """
    resultado = aplicar_regras(
        campos=campos,
        regras=regras,
        contexto=contexto,
        ignorar_erros=(
            ignorar_erros_regras
        ),
    )

    campos_processados: list[
        dict[str, Any]
    ] = []

    for campo_original in resultado[
        "campos"
    ]:
        campo = deepcopy(
            dict(campo_original)
        )

        valor = campo.get(
            "valor",
            "",
        )

        preenchida = (
            valor_esta_preenchido(
                valor
            )
        )

        campo["preenchida"] = (
            preenchida
        )

        if preenchida:
            campo["origem"] = (
                campo.get("origem")
                or "automatica"
            )
        else:
            campo["origem"] = "manual"

        campos_processados.append(
            campo
        )

    return {
        "campos": campos_processados,
        "clausulas": deepcopy(
            resultado.get(
                "clausulas",
                [],
            )
        ),
        "regras_aplicadas": deepcopy(
            resultado.get(
                "regras_aplicadas",
                [],
            )
        ),
        "erros": deepcopy(
            resultado.get(
                "erros",
                [],
            )
        ),
    }


def classificar_campos(
    campos: Iterable[
        Mapping[str, Any]
    ],
) -> dict[str, list[dict[str, Any]]]:
    """
    Separa os campos após a aplicação das regras.
    """
    visiveis: list[
        dict[str, Any]
    ] = []

    ocultas: list[
        dict[str, Any]
    ] = []

    preenchidas: list[
        dict[str, Any]
    ] = []

    faltantes_obrigatorias: list[
        dict[str, Any]
    ] = []

    opcionais_vazias: list[
        dict[str, Any]
    ] = []

    for campo_original in campos:
        campo = deepcopy(
            dict(campo_original)
        )

        visivel = bool(
            campo.get(
                "visivel",
                True,
            )
        )

        obrigatoria = bool(
            campo.get(
                "obrigatoria",
                campo.get(
                    "obrigatorio",
                    False,
                ),
            )
        )

        preenchida = (
            valor_esta_preenchido(
                campo.get("valor")
            )
        )

        campo["preenchida"] = (
            preenchida
        )
        campo["obrigatoria"] = (
            obrigatoria
        )
        campo["obrigatorio"] = (
            obrigatoria
        )

        if not visivel:
            ocultas.append(campo)
            continue

        visiveis.append(campo)

        if preenchida:
            preenchidas.append(campo)
            continue

        if obrigatoria:
            faltantes_obrigatorias.append(
                campo
            )
            continue

        opcionais_vazias.append(
            campo
        )

    return {
        "visiveis": visiveis,
        "ocultas": ocultas,
        "preenchidas": preenchidas,
        "faltantes_obrigatorias": (
            faltantes_obrigatorias
        ),
        "opcionais_vazias": (
            opcionais_vazias
        ),
    }


def descobrir_variaveis_preenchidas(
    variaveis: Iterable[Any] | None,
    contexto: Mapping[str, Any] | None = None,
    regras: Iterable[
        Mapping[str, Any]
    ] | None = None,
    ignorar_erros_regras: bool = False,
) -> list[dict[str, Any]]:
    """
    Retorna somente os campos visíveis preenchidos.
    """
    resumo = montar_resumo_resolucao(
        variaveis=variaveis,
        contexto=contexto,
        regras=regras,
        ignorar_erros_regras=(
            ignorar_erros_regras
        ),
    )

    return resumo["preenchidas"]


def descobrir_variaveis_faltantes(
    variaveis: Iterable[Any] | None,
    contexto: Mapping[str, Any] | None = None,
    regras: Iterable[
        Mapping[str, Any]
    ] | None = None,
    ignorar_erros_regras: bool = False,
) -> list[dict[str, Any]]:
    """
    Retorna somente os campos visíveis e obrigatórios que estão vazios.
    """
    resumo = montar_resumo_resolucao(
        variaveis=variaveis,
        contexto=contexto,
        regras=regras,
        ignorar_erros_regras=(
            ignorar_erros_regras
        ),
    )

    return resumo[
        "faltantes_obrigatorias"
    ]


def montar_resumo_resolucao(
    variaveis: Iterable[Any] | None,
    contexto: Mapping[str, Any] | None = None,
    regras: Iterable[
        Mapping[str, Any]
    ] | None = None,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Monta o resumo completo para rotas, templates e orquestrador.

    Regras podem:
        - mostrar ou ocultar campos;
        - tornar campos obrigatórios ou opcionais;
        - definir somente leitura;
        - preencher valores;
        - alterar placeholder e ajuda;
        - solicitar a inserção de cláusulas.
    """
    analisadas = analisar_variaveis(
        variaveis=variaveis,
        contexto=contexto,
    )

    resultado_regras = (
        aplicar_regras_resolucao(
            campos=analisadas,
            regras=regras,
            contexto=contexto,
            ignorar_erros_regras=(
                ignorar_erros_regras
            ),
        )
    )

    campos = resultado_regras[
        "campos"
    ]

    classificacao = classificar_campos(
        campos
    )

    visiveis = classificacao[
        "visiveis"
    ]

    ocultas = classificacao[
        "ocultas"
    ]

    preenchidas = classificacao[
        "preenchidas"
    ]

    faltantes_obrigatorias = (
        classificacao[
            "faltantes_obrigatorias"
        ]
    )

    opcionais_vazias = (
        classificacao[
            "opcionais_vazias"
        ]
    )

    desconhecidas = [
        deepcopy(item)
        for item in campos
        if not item.get(
            "conhecida",
            False,
        )
    ]

    pronto_para_gerar = (
        len(
            faltantes_obrigatorias
        )
        == 0
    )

    return {
        "variaveis": campos,
        "campos": campos,
        "visiveis": visiveis,
        "ocultas": ocultas,
        "preenchidas": preenchidas,

        # Alias de compatibilidade com as rotas antigas.
        "faltantes": (
            faltantes_obrigatorias
        ),

        "faltantes_obrigatorias": (
            faltantes_obrigatorias
        ),
        "opcionais_vazias": (
            opcionais_vazias
        ),
        "desconhecidas": desconhecidas,
        "clausulas": resultado_regras[
            "clausulas"
        ],
        "regras_aplicadas": (
            resultado_regras[
                "regras_aplicadas"
            ]
        ),
        "erros_regras": (
            resultado_regras[
                "erros"
            ]
        ),
        "total": len(campos),
        "total_visiveis": len(
            visiveis
        ),
        "total_ocultas": len(
            ocultas
        ),
        "total_preenchidas": len(
            preenchidas
        ),
        "total_faltantes": len(
            faltantes_obrigatorias
        ),
        "total_faltantes_obrigatorias": (
            len(
                faltantes_obrigatorias
            )
        ),
        "total_opcionais_vazias": len(
            opcionais_vazias
        ),
        "total_desconhecidas": len(
            desconhecidas
        ),
        "total_clausulas": len(
            resultado_regras[
                "clausulas"
            ]
        ),
        "total_regras_aplicadas": len(
            resultado_regras[
                "regras_aplicadas"
            ]
        ),
        "total_erros_regras": len(
            resultado_regras[
                "erros"
            ]
        ),
        "pronto_para_gerar": (
            pronto_para_gerar
        ),
    }


def normalizar_valores_manuais(
    valores_manuais: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    """
    Limpa as chaves recebidas do formulário dinâmico.
    """
    resultado: dict[str, Any] = {}

    for codigo, valor in (
        valores_manuais
        or {}
    ).items():
        codigo_normalizado = (
            normalizar_codigo(
                codigo
            )
        )

        if not codigo_normalizado:
            continue

        if isinstance(valor, str):
            valor = valor.strip()

        resultado[
            codigo_normalizado
        ] = valor

    return resultado


def montar_contexto_final(
    contexto_automatico: Mapping[
        str,
        Any,
    ] | None = None,
    valores_manuais: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    """
    Combina o contexto automático com os valores informados pelo usuário.

    Os valores manuais prevalecem. Isso permite corrigir ou sobrescrever
    um dado apenas naquela geração, sem alterar o cadastro original.
    """
    contexto_final = dict(
        contexto_automatico
        or {}
    )

    contexto_final.update(
        normalizar_valores_manuais(
            valores_manuais
        )
    )

    return contexto_final


def validar_preenchimento_final(
    variaveis: Iterable[Any] | None,
    contexto_final: Mapping[
        str,
        Any,
    ] | None,
    regras: Iterable[
        Mapping[str, Any]
    ] | None = None,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Valida somente campos visíveis e obrigatórios após aplicar as regras.

    Campos ocultos ou definidos como opcionais não bloqueiam a geração.
    """
    resumo = montar_resumo_resolucao(
        variaveis=variaveis,
        contexto=contexto_final,
        regras=regras,
        ignorar_erros_regras=(
            ignorar_erros_regras
        ),
    )

    valido = resumo[
        "pronto_para_gerar"
    ]

    faltantes = resumo[
        "faltantes_obrigatorias"
    ]

    total_faltantes = len(
        faltantes
    )

    return {
        "valido": valido,
        "faltantes": faltantes,
        "faltantes_obrigatorias": (
            faltantes
        ),
        "total_faltantes": (
            total_faltantes
        ),
        "total_faltantes_obrigatorias": (
            total_faltantes
        ),
        "mensagem": (
            "Todas as variáveis obrigatórias foram preenchidas."
            if valido
            else (
                f"{total_faltantes} "
                "variável(is) obrigatória(s) "
                "ainda precisa(m) ser "
                "preenchida(s)."
            )
        ),
        "resumo": resumo,
        "clausulas": resumo[
            "clausulas"
        ],
        "regras_aplicadas": resumo[
            "regras_aplicadas"
        ],
        "erros_regras": resumo[
            "erros_regras"
        ],
    }


# Alias mantido para deixar o uso nas rotas mais direto.
resolver_variaveis = (
    montar_resumo_resolucao
)


__all__ = [
    "VALORES_CONSIDERADOS_VAZIOS",
    "VARIAVEIS_OPCIONAIS_GLOBAIS",
    "analisar_variaveis",
    "aplicar_regras_resolucao",
    "classificar_campos",
    "descobrir_variaveis_faltantes",
    "descobrir_variaveis_preenchidas",
    "extrair_codigo_variavel",
    "humanizar_codigo",
    "montar_contexto_final",
    "montar_resumo_resolucao",
    "normalizar_valores_manuais",
    "normalizar_variaveis",
    "obter_metadados_variavel",
    "obter_valor_contexto",
    "resolver_variaveis",
    "validar_preenchimento_final",
    "valor_esta_preenchido",
]