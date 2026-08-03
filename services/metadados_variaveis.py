"""
Metadados oficiais das variáveis utilizadas pelo gerador de documentos.

Este módulo funciona como a fonte central de informações de apresentação,
validação e comportamento dos campos do assistente de preenchimento.

Ele foi projetado para:

- reconhecer variáveis cadastradas explicitamente;
- inferir metadados de variáveis ainda não cadastradas;
- nunca interromper o gerador por causa de uma variável desconhecida;
- fornecer dados consistentes para o resolvedor, formulário e motor de regras.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable


TIPO_TEXTO = "texto"
TIPO_TEXTO_LONGO = "texto_longo"
TIPO_DATA = "data"
TIPO_HORA = "hora"
TIPO_EMAIL = "email"
TIPO_CPF = "cpf"
TIPO_CNPJ = "cnpj"
TIPO_TELEFONE = "telefone"
TIPO_MOEDA = "moeda"
TIPO_NUMERO = "numero"
TIPO_INTEIRO = "inteiro"
TIPO_BOOLEANO = "booleano"
TIPO_SELECT = "select"

ORIGEM_AUTOMATICA = "automatica"
ORIGEM_MANUAL = "manual"
ORIGEM_SISTEMA = "sistema"
ORIGEM_CALCULADA = "calculada"

GRUPO_CLIENTE = "Cliente"
GRUPO_CASO = "Caso"
GRUPO_PROCESSO = "Processo"
GRUPO_ESCRITORIO = "Escritório"
GRUPO_ADVOGADO = "Advogado"
GRUPO_HONORARIOS = "Honorários"
GRUPO_FINANCEIRO = "Financeiro"
GRUPO_ASSINATURA = "Assinatura"
GRUPO_DOCUMENTO = "Documento"
GRUPO_SISTEMA = "Sistema"
GRUPO_OUTROS = "Outros"


@dataclass(frozen=True, slots=True)
class MetaVariavel:
    codigo: str
    descricao: str
    grupo: str = GRUPO_OUTROS
    tipo: str = TIPO_TEXTO
    obrigatoria: bool = False
    editavel: bool = True
    placeholder: str = ""
    ajuda: str = ""
    mascara: str | None = None
    ordem: int = 999
    origem: str = ORIGEM_MANUAL
    icone: str = "bi-input-cursor-text"
    largura: int = 6
    opcoes: tuple[str, ...] = ()
    valor_padrao: Any = None
    sensivel: bool = False

    def para_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["opcoes"] = list(self.opcoes)
        return dados


def _meta(
    codigo: str,
    descricao: str,
    grupo: str,
    *,
    tipo: str = TIPO_TEXTO,
    obrigatoria: bool = False,
    editavel: bool = True,
    placeholder: str = "",
    ajuda: str = "",
    mascara: str | None = None,
    ordem: int = 999,
    origem: str = ORIGEM_AUTOMATICA,
    icone: str = "bi-input-cursor-text",
    largura: int = 6,
    opcoes: Iterable[str] = (),
    valor_padrao: Any = None,
    sensivel: bool = False,
) -> MetaVariavel:
    return MetaVariavel(
        codigo=codigo,
        descricao=descricao,
        grupo=grupo,
        tipo=tipo,
        obrigatoria=obrigatoria,
        editavel=editavel,
        placeholder=placeholder,
        ajuda=ajuda,
        mascara=mascara,
        ordem=ordem,
        origem=origem,
        icone=icone,
        largura=largura,
        opcoes=tuple(opcoes),
        valor_padrao=valor_padrao,
        sensivel=sensivel,
    )


METADADOS_VARIAVEIS: dict[str, MetaVariavel] = {
    # ------------------------------------------------------------------
    # Cliente
    # ------------------------------------------------------------------
    "cliente.nome": _meta(
        "cliente.nome",
        "Nome completo do cliente",
        GRUPO_CLIENTE,
        obrigatoria=True,
        editavel=False,
        ordem=1,
        icone="bi-person",
    ),
    "cliente.cpf": _meta(
        "cliente.cpf",
        "CPF do cliente",
        GRUPO_CLIENTE,
        tipo=TIPO_CPF,
        obrigatoria=True,
        editavel=False,
        mascara="cpf",
        ordem=2,
        icone="bi-person-vcard",
        sensivel=True,
    ),
    "cliente.rg": _meta(
        "cliente.rg",
        "RG do cliente",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=3,
        icone="bi-card-text",
        sensivel=True,
    ),
    "cliente.data_nascimento": _meta(
        "cliente.data_nascimento",
        "Data de nascimento",
        GRUPO_CLIENTE,
        tipo=TIPO_DATA,
        editavel=False,
        ordem=4,
        icone="bi-calendar-event",
    ),
    "cliente.nacionalidade": _meta(
        "cliente.nacionalidade",
        "Nacionalidade",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=5,
        icone="bi-globe-americas",
    ),
    "cliente.estado_civil": _meta(
        "cliente.estado_civil",
        "Estado civil",
        GRUPO_CLIENTE,
        tipo=TIPO_SELECT,
        editavel=False,
        ordem=6,
        icone="bi-people",
        opcoes=(
            "Solteiro(a)",
            "Casado(a)",
            "Divorciado(a)",
            "Viúvo(a)",
            "União estável",
        ),
    ),
    "cliente.profissao": _meta(
        "cliente.profissao",
        "Profissão",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=7,
        icone="bi-briefcase",
    ),
    "cliente.email": _meta(
        "cliente.email",
        "E-mail",
        GRUPO_CLIENTE,
        tipo=TIPO_EMAIL,
        editavel=False,
        mascara="email",
        placeholder="exemplo@email.com",
        ordem=8,
        icone="bi-envelope",
        sensivel=True,
    ),
    "cliente.telefone": _meta(
        "cliente.telefone",
        "Telefone",
        GRUPO_CLIENTE,
        tipo=TIPO_TELEFONE,
        editavel=False,
        mascara="telefone",
        placeholder="(00) 00000-0000",
        ordem=9,
        icone="bi-telephone",
        sensivel=True,
    ),
    "cliente.whatsapp": _meta(
        "cliente.whatsapp",
        "WhatsApp",
        GRUPO_CLIENTE,
        tipo=TIPO_TELEFONE,
        editavel=False,
        mascara="telefone",
        placeholder="(00) 00000-0000",
        ordem=10,
        icone="bi-whatsapp",
        sensivel=True,
    ),
    "cliente.cep": _meta(
        "cliente.cep",
        "CEP",
        GRUPO_CLIENTE,
        editavel=False,
        mascara="cep",
        ordem=20,
        icone="bi-geo-alt",
    ),
    "cliente.endereco": _meta(
        "cliente.endereco",
        "Endereço completo",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=21,
        icone="bi-house-door",
        largura=12,
    ),
    "cliente.rua": _meta(
        "cliente.rua",
        "Rua",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=22,
        icone="bi-signpost",
    ),
    "cliente.numero": _meta(
        "cliente.numero",
        "Número do endereço",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=23,
        icone="bi-123",
    ),
    "cliente.complemento": _meta(
        "cliente.complemento",
        "Complemento",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=24,
        icone="bi-building",
    ),
    "cliente.bairro": _meta(
        "cliente.bairro",
        "Bairro",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=25,
        icone="bi-map",
    ),
    "cliente.cidade": _meta(
        "cliente.cidade",
        "Cidade",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=26,
        icone="bi-buildings",
    ),
    "cliente.estado": _meta(
        "cliente.estado",
        "Estado",
        GRUPO_CLIENTE,
        editavel=False,
        ordem=27,
        icone="bi-map-fill",
    ),
    "cliente.observacoes": _meta(
        "cliente.observacoes",
        "Observações do cliente",
        GRUPO_CLIENTE,
        tipo=TIPO_TEXTO_LONGO,
        editavel=False,
        ordem=90,
        icone="bi-card-text",
        largura=12,
    ),

    # ------------------------------------------------------------------
    # Caso
    # ------------------------------------------------------------------
    "caso.numero_interno": _meta(
        "caso.numero_interno",
        "Número interno do caso",
        GRUPO_CASO,
        editavel=False,
        ordem=1,
        icone="bi-hash",
    ),
    "caso.titulo": _meta(
        "caso.titulo",
        "Título do caso",
        GRUPO_CASO,
        editavel=False,
        ordem=2,
        icone="bi-folder2-open",
    ),
    "caso.area": _meta(
        "caso.area",
        "Área jurídica",
        GRUPO_CASO,
        editavel=False,
        ordem=3,
        icone="bi-diagram-3",
    ),
    "caso.status": _meta(
        "caso.status",
        "Status do caso",
        GRUPO_CASO,
        editavel=False,
        ordem=4,
        icone="bi-activity",
    ),
    "caso.descricao": _meta(
        "caso.descricao",
        "Descrição do caso",
        GRUPO_CASO,
        tipo=TIPO_TEXTO_LONGO,
        editavel=False,
        ordem=10,
        icone="bi-file-text",
        largura=12,
    ),
    "caso.observacoes": _meta(
        "caso.observacoes",
        "Observações do caso",
        GRUPO_CASO,
        tipo=TIPO_TEXTO_LONGO,
        editavel=False,
        ordem=11,
        icone="bi-card-text",
        largura=12,
    ),

    # ------------------------------------------------------------------
    # Processo
    # ------------------------------------------------------------------
    "processo.numero_cnj": _meta(
        "processo.numero_cnj",
        "Número do processo",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=1,
        icone="bi-hash",
    ),
    "processo.numero": _meta(
        "processo.numero",
        "Número do processo",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=1,
        icone="bi-hash",
    ),
    "processo.tribunal": _meta(
        "processo.tribunal",
        "Tribunal",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=2,
        icone="bi-bank",
    ),
    "processo.comarca": _meta(
        "processo.comarca",
        "Comarca",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=3,
        icone="bi-geo-alt",
    ),
    "processo.vara": _meta(
        "processo.vara",
        "Vara",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=4,
        icone="bi-building",
    ),
    "processo.classe": _meta(
        "processo.classe",
        "Classe processual",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=5,
        icone="bi-folder",
    ),
    "processo.assunto": _meta(
        "processo.assunto",
        "Assunto do processo",
        GRUPO_PROCESSO,
        editavel=False,
        ordem=6,
        icone="bi-bookmark",
    ),
    "processo.valor_causa": _meta(
        "processo.valor_causa",
        "Valor da causa",
        GRUPO_PROCESSO,
        tipo=TIPO_MOEDA,
        editavel=False,
        mascara="moeda",
        ordem=7,
        icone="bi-currency-dollar",
    ),

    # ------------------------------------------------------------------
    # Honorários e financeiro
    # ------------------------------------------------------------------
    "honorario.valor": _meta(
        "honorario.valor",
        "Valor dos honorários",
        GRUPO_HONORARIOS,
        tipo=TIPO_MOEDA,
        obrigatoria=True,
        placeholder="0,00",
        mascara="moeda",
        ordem=1,
        origem=ORIGEM_MANUAL,
        icone="bi-cash-coin",
    ),
    "honorarios.valor": _meta(
        "honorarios.valor",
        "Valor dos honorários",
        GRUPO_HONORARIOS,
        tipo=TIPO_MOEDA,
        obrigatoria=True,
        placeholder="0,00",
        mascara="moeda",
        ordem=1,
        origem=ORIGEM_MANUAL,
        icone="bi-cash-coin",
    ),
    "honorario.forma_pagamento": _meta(
        "honorario.forma_pagamento",
        "Forma de pagamento",
        GRUPO_HONORARIOS,
        tipo=TIPO_SELECT,
        obrigatoria=True,
        ordem=2,
        origem=ORIGEM_MANUAL,
        icone="bi-credit-card",
        opcoes=("À vista", "Parcelado", "Êxito", "Misto"),
    ),
    "honorario.entrada": _meta(
        "honorario.entrada",
        "Valor da entrada",
        GRUPO_HONORARIOS,
        tipo=TIPO_MOEDA,
        placeholder="0,00",
        mascara="moeda",
        ordem=3,
        origem=ORIGEM_MANUAL,
        icone="bi-wallet2",
    ),
    "honorario.parcelas": _meta(
        "honorario.parcelas",
        "Quantidade de parcelas",
        GRUPO_HONORARIOS,
        tipo=TIPO_INTEIRO,
        placeholder="0",
        ordem=4,
        origem=ORIGEM_MANUAL,
        icone="bi-list-ol",
    ),
    "honorario.primeiro_vencimento": _meta(
        "honorario.primeiro_vencimento",
        "Primeiro vencimento",
        GRUPO_HONORARIOS,
        tipo=TIPO_DATA,
        ordem=5,
        origem=ORIGEM_MANUAL,
        icone="bi-calendar-check",
    ),

    # ------------------------------------------------------------------
    # Assinatura, documento e sistema
    # ------------------------------------------------------------------
    "assinatura.cidade": _meta(
        "assinatura.cidade",
        "Cidade da assinatura",
        GRUPO_ASSINATURA,
        obrigatoria=True,
        ordem=1,
        origem=ORIGEM_MANUAL,
        icone="bi-geo-alt",
    ),
    "assinatura.data": _meta(
        "assinatura.data",
        "Data da assinatura",
        GRUPO_ASSINATURA,
        tipo=TIPO_DATA,
        obrigatoria=True,
        ordem=2,
        origem=ORIGEM_MANUAL,
        icone="bi-calendar-check",
    ),
    "documento.observacoes": _meta(
        "documento.observacoes",
        "Observações do documento",
        GRUPO_DOCUMENTO,
        tipo=TIPO_TEXTO_LONGO,
        ordem=1,
        origem=ORIGEM_MANUAL,
        icone="bi-card-text",
        largura=12,
    ),
    "sistema.data_atual": _meta(
        "sistema.data_atual",
        "Data atual",
        GRUPO_SISTEMA,
        tipo=TIPO_DATA,
        editavel=False,
        ordem=1,
        origem=ORIGEM_SISTEMA,
        icone="bi-calendar-date",
    ),
    "sistema.usuario_nome": _meta(
        "sistema.usuario_nome",
        "Usuário responsável",
        GRUPO_SISTEMA,
        editavel=False,
        ordem=2,
        origem=ORIGEM_SISTEMA,
        icone="bi-person-badge",
    ),
}


ALIASES_VARIAVEIS: dict[str, str] = {
    "nome_cliente": "cliente.nome",
    "cliente_nome": "cliente.nome",
    "cpf_cliente": "cliente.cpf",
    "cliente_cpf": "cliente.cpf",
    "rg_cliente": "cliente.rg",
    "cliente_rg": "cliente.rg",
    "email_cliente": "cliente.email",
    "cliente_email": "cliente.email",
    "telefone_cliente": "cliente.telefone",
    "cliente_telefone": "cliente.telefone",
    "whatsapp_cliente": "cliente.whatsapp",
    "cliente_whatsapp": "cliente.whatsapp",
    "numero_processo": "processo.numero_cnj",
    "processo_numero": "processo.numero_cnj",
    "numero_cnj": "processo.numero_cnj",
    "valor_honorarios": "honorario.valor",
    "honorarios_valor": "honorario.valor",
    "data_assinatura": "assinatura.data",
    "cidade_assinatura": "assinatura.cidade",
    "data_atual": "sistema.data_atual",
}


def normalizar_codigo(codigo: str | None) -> str:
    if not codigo:
        return ""

    texto = str(codigo).strip()

    texto = texto.replace("{{", "").replace("}}", "")
    texto = texto.strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = texto.lower()
    texto = re.sub(r"\s+", "_", texto)
    texto = texto.replace("-", "_")
    texto = re.sub(r"_+", "_", texto)

    return texto.strip("._ ")


def resolver_alias(codigo: str | None) -> str:
    codigo_normalizado = normalizar_codigo(codigo)
    return ALIASES_VARIAVEIS.get(codigo_normalizado, codigo_normalizado)


def _humanizar_codigo(codigo: str) -> str:
    trecho = codigo.split(".")[-1]
    trecho = trecho.replace("_", " ").strip()

    substituicoes = {
        "cpf": "CPF",
        "cnpj": "CNPJ",
        "rg": "RG",
        "cep": "CEP",
        "cnj": "CNJ",
        "email": "E-mail",
        "whatsapp": "WhatsApp",
    }

    palavras = []

    for palavra in trecho.split():
        palavras.append(substituicoes.get(palavra.lower(), palavra.capitalize()))

    return " ".join(palavras) or "Campo adicional"


def _inferir_grupo(codigo: str) -> str:
    prefixo = codigo.split(".")[0].split("_")[0]

    grupos = {
        "cliente": GRUPO_CLIENTE,
        "caso": GRUPO_CASO,
        "processo": GRUPO_PROCESSO,
        "escritorio": GRUPO_ESCRITORIO,
        "advogado": GRUPO_ADVOGADO,
        "usuario": GRUPO_ADVOGADO,
        "honorario": GRUPO_HONORARIOS,
        "honorarios": GRUPO_HONORARIOS,
        "financeiro": GRUPO_FINANCEIRO,
        "assinatura": GRUPO_ASSINATURA,
        "documento": GRUPO_DOCUMENTO,
        "sistema": GRUPO_SISTEMA,
    }

    return grupos.get(prefixo, GRUPO_OUTROS)


def _contem_token(codigo: str, *tokens: str) -> bool:
    texto = codigo.replace(".", "_")
    partes = set(filter(None, texto.split("_")))

    return any(
        token in partes or token in texto
        for token in tokens
    )


def _inferir_tipo(codigo: str) -> tuple[str, str | None, bool]:
    if _contem_token(codigo, "cpf"):
        return TIPO_CPF, "cpf", True

    if _contem_token(codigo, "cnpj"):
        return TIPO_CNPJ, "cnpj", True

    if _contem_token(codigo, "email"):
        return TIPO_EMAIL, "email", True

    if _contem_token(codigo, "telefone", "celular", "whatsapp"):
        return TIPO_TELEFONE, "telefone", True

    if _contem_token(codigo, "data", "nascimento", "vencimento", "expedicao"):
        return TIPO_DATA, None, False

    if _contem_token(codigo, "hora", "horario"):
        return TIPO_HORA, None, False

    if _contem_token(
        codigo,
        "valor",
        "honorario",
        "salario",
        "renda",
        "custas",
        "multa",
        "entrada",
        "total",
        "preco",
    ):
        return TIPO_MOEDA, "moeda", False

    if _contem_token(
        codigo,
        "quantidade",
        "parcelas",
        "numero_parcelas",
        "idade",
        "anos",
        "meses",
        "dias",
    ):
        return TIPO_INTEIRO, None, False

    if _contem_token(
        codigo,
        "observacao",
        "observacoes",
        "descricao",
        "fundamentacao",
        "pedido",
        "clausula",
        "texto",
        "relato",
        "detalhe",
        "resumo",
    ):
        return TIPO_TEXTO_LONGO, None, False

    if _contem_token(codigo, "ativo", "casado", "aposentado", "sim_nao"):
        return TIPO_BOOLEANO, None, False

    return TIPO_TEXTO, None, False


def _inferir_icone(tipo: str) -> str:
    icones = {
        TIPO_TEXTO: "bi-input-cursor-text",
        TIPO_TEXTO_LONGO: "bi-card-text",
        TIPO_DATA: "bi-calendar-event",
        TIPO_HORA: "bi-clock",
        TIPO_EMAIL: "bi-envelope",
        TIPO_CPF: "bi-person-vcard",
        TIPO_CNPJ: "bi-building-vcard",
        TIPO_TELEFONE: "bi-telephone",
        TIPO_MOEDA: "bi-cash-coin",
        TIPO_NUMERO: "bi-123",
        TIPO_INTEIRO: "bi-123",
        TIPO_BOOLEANO: "bi-toggle-on",
        TIPO_SELECT: "bi-list-check",
    }

    return icones.get(tipo, "bi-input-cursor-text")


def inferir_metadados(codigo: str | None) -> MetaVariavel:
    codigo_resolvido = resolver_alias(codigo)

    tipo, mascara, sensivel = _inferir_tipo(codigo_resolvido)
    grupo = _inferir_grupo(codigo_resolvido)

    largura = 12 if tipo == TIPO_TEXTO_LONGO else 6

    placeholder = ""

    if tipo == TIPO_EMAIL:
        placeholder = "exemplo@email.com"
    elif tipo == TIPO_CPF:
        placeholder = "000.000.000-00"
    elif tipo == TIPO_CNPJ:
        placeholder = "00.000.000/0000-00"
    elif tipo == TIPO_TELEFONE:
        placeholder = "(00) 00000-0000"
    elif tipo == TIPO_MOEDA:
        placeholder = "0,00"
    elif tipo == TIPO_INTEIRO:
        placeholder = "0"

    origem = (
        ORIGEM_SISTEMA
        if grupo == GRUPO_SISTEMA
        else ORIGEM_MANUAL
    )

    return MetaVariavel(
        codigo=codigo_resolvido,
        descricao=_humanizar_codigo(codigo_resolvido),
        grupo=grupo,
        tipo=tipo,
        obrigatoria=False,
        editavel=True,
        placeholder=placeholder,
        ajuda="Variável personalizada encontrada no modelo.",
        mascara=mascara,
        ordem=999,
        origem=origem,
        icone=_inferir_icone(tipo),
        largura=largura,
        opcoes=(),
        valor_padrao=None,
        sensivel=sensivel,
    )


def obter_metadados(
    codigo: str | None,
    *,
    obrigatoria: bool | None = None,
    editavel: bool | None = None,
    origem: str | None = None,
) -> MetaVariavel:
    codigo_resolvido = resolver_alias(codigo)

    meta = METADADOS_VARIAVEIS.get(codigo_resolvido)

    if meta is None:
        meta = inferir_metadados(codigo_resolvido)

    alteracoes: dict[str, Any] = {}

    if obrigatoria is not None:
        alteracoes["obrigatoria"] = obrigatoria

    if editavel is not None:
        alteracoes["editavel"] = editavel

    if origem is not None:
        alteracoes["origem"] = origem

    if alteracoes:
        meta = replace(meta, **alteracoes)

    return meta


def obter_metadados_dict(
    codigo: str | None,
    *,
    obrigatoria: bool | None = None,
    editavel: bool | None = None,
    origem: str | None = None,
) -> dict[str, Any]:
    return obter_metadados(
        codigo,
        obrigatoria=obrigatoria,
        editavel=editavel,
        origem=origem,
    ).para_dict()


def variavel_conhecida(codigo: str | None) -> bool:
    return resolver_alias(codigo) in METADADOS_VARIAVEIS


def listar_metadados(
    *,
    grupo: str | None = None,
    tipo: str | None = None,
) -> list[MetaVariavel]:
    itens = list(METADADOS_VARIAVEIS.values())

    if grupo is not None:
        itens = [
            item
            for item in itens
            if item.grupo.casefold() == grupo.casefold()
        ]

    if tipo is not None:
        itens = [
            item
            for item in itens
            if item.tipo == tipo
        ]

    return sorted(
        itens,
        key=lambda item: (
            item.grupo.casefold(),
            item.ordem,
            item.descricao.casefold(),
        ),
    )


def registrar_metadado(meta: MetaVariavel, *, substituir: bool = False) -> None:
    codigo = resolver_alias(meta.codigo)

    if codigo in METADADOS_VARIAVEIS and not substituir:
        raise ValueError(
            f"A variável '{codigo}' já possui metadados cadastrados."
        )

    METADADOS_VARIAVEIS[codigo] = replace(meta, codigo=codigo)


def atualizar_metadados(
    codigo: str,
    **alteracoes: Any,
) -> MetaVariavel:
    codigo_resolvido = resolver_alias(codigo)
    atual = obter_metadados(codigo_resolvido)

    campos_validos = set(MetaVariavel.__dataclass_fields__)
    desconhecidos = set(alteracoes) - campos_validos

    if desconhecidos:
        nomes = ", ".join(sorted(desconhecidos))
        raise ValueError(f"Campos de metadados inválidos: {nomes}.")

    atualizado = replace(
        atual,
        codigo=codigo_resolvido,
        **alteracoes,
    )

    METADADOS_VARIAVEIS[codigo_resolvido] = atualizado
    return atualizado


__all__ = [
    "MetaVariavel",
    "METADADOS_VARIAVEIS",
    "ALIASES_VARIAVEIS",
    "TIPO_TEXTO",
    "TIPO_TEXTO_LONGO",
    "TIPO_DATA",
    "TIPO_HORA",
    "TIPO_EMAIL",
    "TIPO_CPF",
    "TIPO_CNPJ",
    "TIPO_TELEFONE",
    "TIPO_MOEDA",
    "TIPO_NUMERO",
    "TIPO_INTEIRO",
    "TIPO_BOOLEANO",
    "TIPO_SELECT",
    "ORIGEM_AUTOMATICA",
    "ORIGEM_MANUAL",
    "ORIGEM_SISTEMA",
    "ORIGEM_CALCULADA",
    "normalizar_codigo",
    "resolver_alias",
    "inferir_metadados",
    "obter_metadados",
    "obter_metadados_dict",
    "variavel_conhecida",
    "listar_metadados",
    "registrar_metadado",
    "atualizar_metadados",
]