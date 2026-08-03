from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from collections.abc import Iterable, Mapping

from services.conversor_pdf import (
    ErroConversaoPDF,
    converter_docx_para_pdf,
)
from services.regras_modelo import (
    ErroRegrasModelo,
    carregar_regras_modelo,
)
from services.renderizador_docx import (
    ErroRenderizacaoDocumento,
    renderizar_documento_docx,
)
from services.resolvedor_variaveis import (
    montar_contexto_final,
    montar_resumo_resolucao,
    validar_preenchimento_final,
)


class ErroOrquestracaoDocumento(Exception):
    """
    Erro controlado durante a preparação ou geração de um documento.
    """


class DocumentoNaoPreenchidoError(ErroOrquestracaoDocumento):
    """
    Indica que existem campos obrigatórios sem preenchimento.
    """

    def __init__(
        self,
        mensagem: str,
        faltantes: Iterable[Mapping[str, Any]] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.faltantes = [
            dict(item)
            for item in (faltantes or [])
        ]


def _obter_atributo_ou_chave(
    objeto: Any,
    nomes: Iterable[str],
    padrao: Any = None,
) -> Any:
    """
    Busca um valor em objeto ou dicionário usando nomes alternativos.
    """
    if objeto is None:
        return padrao

    if isinstance(objeto, Mapping):
        for nome in nomes:
            if nome in objeto:
                valor = objeto.get(nome)

                if valor is not None:
                    return valor

        return padrao

    for nome in nomes:
        if hasattr(objeto, nome):
            valor = getattr(objeto, nome)

            if valor is not None:
                return valor

    return padrao


def obter_variaveis_modelo(modelo: Any) -> list[Any]:
    """
    Retorna as variáveis cadastradas no modelo.

    Aceita um objeto ModeloDocumento ou um dicionário equivalente.
    """
    variaveis = _obter_atributo_ou_chave(
        modelo,
        (
            "variaveis",
            "campos",
            "placeholders",
        ),
        [],
    )

    if variaveis is None:
        return []

    if isinstance(variaveis, str):
        return [
            item.strip()
            for item in variaveis.split(",")
            if item.strip()
        ]

    try:
        return list(variaveis)
    except TypeError as erro:
        raise ErroOrquestracaoDocumento(
            "As variáveis do modelo possuem formato inválido."
        ) from erro


def resolver_caminho_modelo(
    modelo: Any,
    caminho_modelo: str | Path | None = None,
) -> Path:
    """
    Resolve o caminho físico do DOCX.

    A rota pode enviar um caminho já validado. Caso não envie, o serviço
    tenta usar o caminho armazenado no próprio modelo.
    """
    valor = caminho_modelo

    if valor is None:
        valor = _obter_atributo_ou_chave(
            modelo,
            (
                "caminho_arquivo",
                "arquivo_docx",
                "caminho_docx",
                "arquivo",
                "path",
            ),
        )

    if valor in (None, ""):
        raise ErroOrquestracaoDocumento(
            "O modelo não possui um arquivo DOCX associado."
        )

    return Path(valor)


def carregar_regras_para_documento(
    modelo: Any,
    caminho_modelo: str | Path | None = None,
    regras: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Obtém as regras que serão usadas na geração.

    Quando as regras forem fornecidas diretamente, elas prevalecem.
    Caso contrário, o arquivo de regras é procurado ao lado do caminho
    físico do DOCX. Isso evita problemas com caminhos relativos salvos
    no banco de dados.
    """
    if regras is not None:
        return [
            deepcopy(dict(regra))
            for regra in regras
        ]

    referencia_regras: Any = modelo

    if caminho_modelo is not None:
        referencia_regras = Path(caminho_modelo)

    try:
        return carregar_regras_modelo(
            referencia_regras
        )
    except ErroRegrasModelo as erro:
        raise ErroOrquestracaoDocumento(
            f"Não foi possível carregar as regras do modelo: {erro}"
        ) from erro


def montar_contexto_com_clausulas(
    contexto: Mapping[str, Any] | None,
    clausulas: Iterable[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """
    Acrescenta as cláusulas resultantes das regras ao contexto.

    Cada cláusula com código passa a ficar disponível como:

        clausula.CODIGO

    A lista completa também fica disponível em:

        regras.clausulas

    O renderizador atual continuará funcionando normalmente mesmo quando
    o modelo DOCX ainda não utiliza essas chaves.
    """
    contexto_final = dict(contexto or {})
    clausulas_normalizadas: list[dict[str, Any]] = []

    for indice, clausula_original in enumerate(clausulas or []):
        clausula = dict(clausula_original)
        clausulas_normalizadas.append(clausula)

        codigo = str(
            clausula.get("codigo")
            or clausula.get("campo")
            or f"clausula_{indice + 1}"
        ).strip()

        conteudo = clausula.get(
            "conteudo",
            clausula.get("valor", ""),
        )

        if codigo:
            contexto_final[
                f"clausula.{codigo}"
            ] = conteudo

    contexto_final["regras.clausulas"] = clausulas_normalizadas

    return contexto_final


def preparar_documento(
    modelo: Any,
    contexto_automatico: Mapping[str, Any] | None = None,
    valores_manuais: Mapping[str, Any] | None = None,
    caminho_modelo: str | Path | None = None,
    regras: Iterable[Mapping[str, Any]] | None = None,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Prepara todos os dados necessários para a tela do assistente.

    Fluxo:
        contexto automático
        + valores manuais
        + regras do modelo
        + resolução de variáveis
        = resumo pronto para a interface
    """
    variaveis = obter_variaveis_modelo(modelo)

    contexto_final = montar_contexto_final(
        contexto_automatico=contexto_automatico,
        valores_manuais=valores_manuais,
    )

    regras_modelo = carregar_regras_para_documento(
        modelo=modelo,
        caminho_modelo=caminho_modelo,
        regras=regras,
    )

    resumo = montar_resumo_resolucao(
        variaveis=variaveis,
        contexto=contexto_final,
        regras=regras_modelo,
        ignorar_erros_regras=ignorar_erros_regras,
    )

    contexto_renderizacao = montar_contexto_com_clausulas(
        contexto=contexto_final,
        clausulas=resumo.get("clausulas"),
    )

    return {
        "modelo": modelo,
        "variaveis": variaveis,
        "regras": regras_modelo,
        "contexto": contexto_renderizacao,
        "contexto_original": contexto_final,
        "resumo": resumo,
        "campos": resumo.get(
            "variaveis",
            [],
        ),
        "visiveis": resumo.get(
            "visiveis",
            resumo.get("variaveis", []),
        ),
        "ocultas": resumo.get(
            "ocultas",
            [],
        ),
        "preenchidas": resumo.get(
            "preenchidas",
            [],
        ),
        "faltantes": resumo.get(
            "faltantes",
            [],
        ),
        "faltantes_obrigatorias": resumo.get(
            "faltantes_obrigatorias",
            resumo.get("faltantes", []),
        ),
        "opcionais_vazias": resumo.get(
            "opcionais_vazias",
            [],
        ),
        "clausulas": resumo.get(
            "clausulas",
            [],
        ),
        "regras_aplicadas": resumo.get(
            "regras_aplicadas",
            [],
        ),
        "erros_regras": resumo.get(
            "erros_regras",
            [],
        ),
        "pronto_para_gerar": resumo.get(
            "pronto_para_gerar",
            False,
        ),
    }


def validar_documento_preparado(
    preparacao: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Valida uma preparação já executada, sem aplicar regras novamente.
    """
    resumo = preparacao.get("resumo", {})
    faltantes = resumo.get(
        "faltantes_obrigatorias",
        resumo.get("faltantes", []),
    )
    total = len(faltantes)
    valido = total == 0

    return {
        "valido": valido,
        "faltantes": faltantes,
        "total_faltantes": total,
        "mensagem": (
            "Todas as variáveis obrigatórias foram preenchidas."
            if valido
            else (
                f"{total} variável(is) obrigatória(s) ainda "
                "precisa(m) ser preenchida(s)."
            )
        ),
        "resumo": resumo,
    }


def validar_documento(
    modelo: Any,
    contexto_automatico: Mapping[str, Any] | None = None,
    valores_manuais: Mapping[str, Any] | None = None,
    caminho_modelo: str | Path | None = None,
    regras: Iterable[Mapping[str, Any]] | None = None,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Prepara e valida o documento em uma única chamada.
    """
    preparacao = preparar_documento(
        modelo=modelo,
        contexto_automatico=contexto_automatico,
        valores_manuais=valores_manuais,
        caminho_modelo=caminho_modelo,
        regras=regras,
        ignorar_erros_regras=ignorar_erros_regras,
    )

    validacao = validar_documento_preparado(
        preparacao
    )

    return {
        **validacao,
        "preparacao": preparacao,
    }


def gerar_documento(
    modelo: Any,
    caminho_saida_docx: str | Path,
    contexto_automatico: Mapping[str, Any] | None = None,
    valores_manuais: Mapping[str, Any] | None = None,
    caminho_modelo: str | Path | None = None,
    caminho_saida_pdf: str | Path | None = None,
    gerar_pdf: bool = False,
    regras: Iterable[Mapping[str, Any]] | None = None,
    manter_nao_encontradas: bool = True,
    ignorar_erros_regras: bool = False,
) -> dict[str, Any]:
    """
    Executa o fluxo completo de geração de arquivos.

    O serviço:
        1. carrega as regras;
        2. resolve os campos;
        3. valida obrigatórios;
        4. renderiza o DOCX;
        5. tenta gerar o PDF quando solicitado.

    Persistência no banco, auditoria e mensagens Flask continuam sendo
    responsabilidade da rota ou de um serviço de aplicação específico.
    """
    caminho_modelo_resolvido = resolver_caminho_modelo(
        modelo=modelo,
        caminho_modelo=caminho_modelo,
    ).resolve()

    caminho_docx = Path(
        caminho_saida_docx
    ).resolve()

    caminho_pdf = (
        Path(caminho_saida_pdf).resolve()
        if caminho_saida_pdf is not None
        else None
    )

    if not caminho_modelo_resolvido.is_file():
        raise ErroOrquestracaoDocumento(
            "O arquivo físico do modelo DOCX não foi encontrado."
        )

    preparacao = preparar_documento(
        modelo=modelo,
        contexto_automatico=contexto_automatico,
        valores_manuais=valores_manuais,
        caminho_modelo=caminho_modelo_resolvido,
        regras=regras,
        ignorar_erros_regras=ignorar_erros_regras,
    )

    validacao = validar_documento_preparado(
        preparacao
    )

    if not validacao["valido"]:
        raise DocumentoNaoPreenchidoError(
            validacao["mensagem"],
            validacao["faltantes"],
        )

    caminho_docx.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        resultado_renderizacao = renderizar_documento_docx(
            caminho_modelo=caminho_modelo_resolvido,
            caminho_saida=caminho_docx,
            contexto=preparacao["contexto"],
            manter_nao_encontradas=manter_nao_encontradas,
        )
    except ErroRenderizacaoDocumento:
        if caminho_docx.is_file():
            caminho_docx.unlink()

        raise
    except Exception as erro:
        if caminho_docx.is_file():
            caminho_docx.unlink()

        raise ErroOrquestracaoDocumento(
            "Ocorreu um erro inesperado durante a renderização do DOCX."
        ) from erro

    if not caminho_docx.is_file():
        raise ErroOrquestracaoDocumento(
            "A renderização terminou, mas o arquivo DOCX não foi criado."
        )

    pdf_gerado = False
    erro_pdf: str | None = None

    if gerar_pdf:
        if caminho_pdf is None:
            caminho_pdf = caminho_docx.with_suffix(
                ".pdf"
            )

        try:
            converter_docx_para_pdf(
                caminho_docx=caminho_docx,
                caminho_pdf=caminho_pdf,
            )
            pdf_gerado = caminho_pdf.is_file()
        except ErroConversaoPDF as erro:
            erro_pdf = str(erro)

            if caminho_pdf.is_file():
                caminho_pdf.unlink()

    return {
        "modelo": modelo,
        "preparacao": preparacao,
        "validacao": validacao,
        "contexto": preparacao["contexto"],
        "regras": preparacao["regras"],
        "clausulas": preparacao["clausulas"],
        "regras_aplicadas": preparacao[
            "regras_aplicadas"
        ],
        "erros_regras": preparacao[
            "erros_regras"
        ],
        "resultado_renderizacao": resultado_renderizacao,
        "caminho_docx": caminho_docx,
        "docx_gerado": caminho_docx.is_file(),
        "caminho_pdf": caminho_pdf,
        "pdf_solicitado": gerar_pdf,
        "pdf_gerado": pdf_gerado,
        "erro_pdf": erro_pdf,
    }


def limpar_arquivos_gerados(
    *caminhos: str | Path | None,
) -> None:
    """
    Remove arquivos gerados em caso de rollback da operação.
    """
    for caminho_original in caminhos:
        if caminho_original is None:
            continue

        caminho = Path(caminho_original)

        try:
            if caminho.is_file():
                caminho.unlink()
        except OSError:
            pass


# Nomes alternativos para deixar o uso nas rotas mais expressivo.
orquestrar_preparacao = preparar_documento
orquestrar_validacao = validar_documento
orquestrar_geracao = gerar_documento


__all__ = [
    "DocumentoNaoPreenchidoError",
    "ErroConversaoPDF",
    "ErroOrquestracaoDocumento",
    "ErroRenderizacaoDocumento",
    "carregar_regras_para_documento",
    "gerar_documento",
    "limpar_arquivos_gerados",
    "montar_contexto_com_clausulas",
    "obter_variaveis_modelo",
    "orquestrar_geracao",
    "orquestrar_preparacao",
    "orquestrar_validacao",
    "preparar_documento",
    "resolver_caminho_modelo",
    "validar_documento",
    "validar_documento_preparado",
]