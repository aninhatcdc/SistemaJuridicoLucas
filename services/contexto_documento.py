from datetime import date, datetime
from typing import Any


MESES_PORTUGUES = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


def obter_atributo(objeto: Any, nome: str, padrao: Any = "") -> Any:
    if objeto is None:
        return padrao

    valor = getattr(objeto, nome, padrao)

    if valor is None:
        return padrao

    return valor


def obter_primeiro_atributo(
    objeto: Any,
    nomes: list[str],
    padrao: Any = "",
) -> Any:
    for nome in nomes:
        valor = obter_atributo(objeto, nome, None)

        if valor not in (None, ""):
            return valor

    return padrao


def formatar_data(valor: Any) -> str:
    if not valor:
        return ""

    if isinstance(valor, datetime):
        valor = valor.date()

    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")

    return str(valor)


def formatar_data_extenso(valor: Any) -> str:
    if not valor:
        return ""

    if isinstance(valor, datetime):
        valor = valor.date()

    if not isinstance(valor, date):
        return str(valor)

    mes = MESES_PORTUGUES.get(valor.month, "")

    return f"{valor.day} de {mes} de {valor.year}"


def formatar_cpf(valor: Any) -> str:
    if not valor:
        return ""

    numeros = "".join(
        caractere
        for caractere in str(valor)
        if caractere.isdigit()
    )

    if len(numeros) != 11:
        return str(valor)

    return (
        f"{numeros[0:3]}."
        f"{numeros[3:6]}."
        f"{numeros[6:9]}-"
        f"{numeros[9:11]}"
    )


def formatar_cep(valor: Any) -> str:
    if not valor:
        return ""

    numeros = "".join(
        caractere
        for caractere in str(valor)
        if caractere.isdigit()
    )

    if len(numeros) != 8:
        return str(valor)

    return f"{numeros[0:5]}-{numeros[5:8]}"


def formatar_valor(valor: Any) -> str:
    if valor is None:
        return ""

    if isinstance(valor, datetime):
        return formatar_data(valor)

    if isinstance(valor, date):
        return formatar_data(valor)

    if isinstance(valor, bool):
        return "Sim" if valor else "Não"

    return str(valor)


def montar_endereco(objeto: Any) -> str:
    if objeto is None:
        return ""

    logradouro = formatar_valor(
        obter_primeiro_atributo(
            objeto,
            ["logradouro", "rua"],
        )
    ).strip()

    numero = formatar_valor(
        obter_atributo(objeto, "numero")
    ).strip()

    complemento = formatar_valor(
        obter_atributo(objeto, "complemento")
    ).strip()

    bairro = formatar_valor(
        obter_atributo(objeto, "bairro")
    ).strip()

    cidade = formatar_valor(
        obter_atributo(objeto, "cidade")
    ).strip()

    estado = formatar_valor(
        obter_atributo(objeto, "estado")
    ).strip().upper()

    cep = formatar_cep(
        obter_atributo(objeto, "cep")
    ).strip()

    partes = []
    linha_logradouro = logradouro

    if numero:
        if linha_logradouro:
            linha_logradouro += f", nº {numero}"
        else:
            linha_logradouro = f"nº {numero}"

    if complemento:
        if linha_logradouro:
            linha_logradouro += f", {complemento}"
        else:
            linha_logradouro = complemento

    if linha_logradouro:
        partes.append(linha_logradouro)

    if bairro:
        partes.append(f"Bairro {bairro}")

    cidade_estado = cidade

    if estado:
        cidade_estado = (
            f"{cidade_estado}/{estado}"
            if cidade_estado
            else estado
        )

    if cidade_estado:
        partes.append(cidade_estado)

    if cep:
        partes.append(f"CEP {cep}")

    return ", ".join(partes)


def montar_rg_completo(cliente: Any) -> str:
    rg = formatar_valor(
        obter_atributo(cliente, "rg")
    ).strip()

    expedidor = formatar_valor(
        obter_atributo(cliente, "orgao_expedidor")
    ).strip()

    uf = formatar_valor(
        obter_atributo(cliente, "uf_rg")
    ).strip().upper()

    orgao_completo = ""

    if expedidor and uf:
        orgao_completo = f"{expedidor}/{uf}"
    elif expedidor:
        orgao_completo = expedidor
    elif uf:
        orgao_completo = uf

    if rg and orgao_completo:
        return f"{rg} - {orgao_completo}"

    return rg or orgao_completo


def montar_naturalidade_completa(cliente: Any) -> str:
    naturalidade = formatar_valor(
        obter_atributo(cliente, "naturalidade")
    ).strip()

    uf = formatar_valor(
        obter_atributo(cliente, "uf_naturalidade")
    ).strip().upper()

    if naturalidade and uf:
        return f"{naturalidade}/{uf}"

    return naturalidade or uf


def montar_contexto_cliente(cliente: Any) -> dict[str, str]:
    if cliente is None:
        return {}

    logradouro = formatar_valor(
        obter_primeiro_atributo(
            cliente,
            ["logradouro", "rua"],
        )
    )

    endereco = formatar_valor(
        obter_atributo(
            cliente,
            "endereco_completo",
            montar_endereco(cliente),
        )
    )

    if not endereco:
        endereco = montar_endereco(cliente)

    rg_completo = formatar_valor(
        obter_atributo(
            cliente,
            "rg_completo",
            montar_rg_completo(cliente),
        )
    )

    if not rg_completo:
        rg_completo = montar_rg_completo(cliente)

    naturalidade_completa = formatar_valor(
        obter_atributo(
            cliente,
            "naturalidade_completa",
            montar_naturalidade_completa(cliente),
        )
    )

    if not naturalidade_completa:
        naturalidade_completa = montar_naturalidade_completa(
            cliente
        )

    return {
        "cliente.nome": formatar_valor(
            obter_atributo(cliente, "nome")
        ),
        "cliente.cpf": formatar_cpf(
            obter_atributo(cliente, "cpf")
        ),
        "cliente.rg": formatar_valor(
            obter_atributo(cliente, "rg")
        ),
        "cliente.rg_completo": rg_completo,
        "cliente.orgao_expedidor": formatar_valor(
            obter_atributo(cliente, "orgao_expedidor")
        ),
        "cliente.uf_rg": formatar_valor(
            obter_atributo(cliente, "uf_rg")
        ).upper(),
        "cliente.data_nascimento": formatar_data(
            obter_atributo(cliente, "data_nascimento")
        ),
        "cliente.sexo": formatar_valor(
            obter_atributo(cliente, "sexo")
        ),
        "cliente.nacionalidade": formatar_valor(
            obter_atributo(
                cliente,
                "nacionalidade",
                "Brasileira",
            )
        ),
        "cliente.naturalidade": formatar_valor(
            obter_atributo(cliente, "naturalidade")
        ),
        "cliente.uf_naturalidade": formatar_valor(
            obter_atributo(cliente, "uf_naturalidade")
        ).upper(),
        "cliente.naturalidade_completa": naturalidade_completa,
        "cliente.estado_civil": formatar_valor(
            obter_atributo(cliente, "estado_civil")
        ),
        "cliente.profissao": formatar_valor(
            obter_atributo(cliente, "profissao")
        ),
        "cliente.nome_mae": formatar_valor(
            obter_atributo(cliente, "nome_mae")
        ),
        "cliente.nome_pai": formatar_valor(
            obter_atributo(cliente, "nome_pai")
        ),
        "cliente.telefone": formatar_valor(
            obter_atributo(cliente, "telefone")
        ),
        "cliente.whatsapp": formatar_valor(
            obter_atributo(cliente, "whatsapp")
        ),
        "cliente.email": formatar_valor(
            obter_atributo(cliente, "email")
        ),
        "cliente.cep": formatar_cep(
            obter_atributo(cliente, "cep")
        ),
        "cliente.logradouro": logradouro,
        "cliente.rua": logradouro,
        "cliente.numero": formatar_valor(
            obter_atributo(cliente, "numero")
        ),
        "cliente.complemento": formatar_valor(
            obter_atributo(cliente, "complemento")
        ),
        "cliente.bairro": formatar_valor(
            obter_atributo(cliente, "bairro")
        ),
        "cliente.cidade": formatar_valor(
            obter_atributo(cliente, "cidade")
        ),
        "cliente.estado": formatar_valor(
            obter_atributo(cliente, "estado")
        ).upper(),
        "cliente.endereco": endereco,
        "cliente.endereco_completo": endereco,
        "cliente.origem": formatar_valor(
            obter_atributo(cliente, "origem")
        ),
        "cliente.observacoes": formatar_valor(
            obter_atributo(cliente, "observacoes")
        ),
        "cliente.ativo": formatar_valor(
            obter_atributo(cliente, "ativo")
        ),
        "cliente.criado_em": formatar_data(
            obter_atributo(cliente, "criado_em")
        ),
        "cliente.atualizado_em": formatar_data(
            obter_atributo(cliente, "atualizado_em")
        ),
    }


def montar_contexto_caso(caso: Any) -> dict[str, str]:
    if caso is None:
        return {}

    numero_interno = obter_atributo(
        caso,
        "numero_interno",
        obter_atributo(caso, "numero"),
    )

    area = obter_atributo(
        caso,
        "area",
        obter_atributo(caso, "area_juridica"),
    )

    status = obter_atributo(
        caso,
        "status",
        obter_atributo(caso, "situacao"),
    )

    data_abertura = obter_atributo(
        caso,
        "data_abertura",
        obter_atributo(caso, "criado_em"),
    )

    return {
        "caso.numero_interno": formatar_valor(numero_interno),
        "caso.titulo": formatar_valor(
            obter_atributo(caso, "titulo")
        ),
        "caso.area": formatar_valor(area),
        "caso.status": formatar_valor(status),
        "caso.descricao": formatar_valor(
            obter_atributo(caso, "descricao")
        ),
        "caso.data_abertura": formatar_data(data_abertura),
    }


def montar_contexto_processo(
    processo: Any,
) -> dict[str, str]:
    if processo is None:
        return {}

    numero = obter_atributo(processo, "numero")

    numero_cnj = obter_atributo(
        processo,
        "numero_cnj",
        numero,
    )

    fase = obter_atributo(
        processo,
        "fase",
        obter_atributo(processo, "situacao"),
    )

    return {
        "processo.numero_cnj": formatar_valor(numero_cnj),
        "processo.numero": formatar_valor(numero),
        "processo.tribunal": formatar_valor(
            obter_atributo(processo, "tribunal")
        ),
        "processo.comarca": formatar_valor(
            obter_atributo(processo, "comarca")
        ),
        "processo.vara": formatar_valor(
            obter_atributo(processo, "vara")
        ),
        "processo.fase": formatar_valor(fase),
        "processo.situacao": formatar_valor(
            obter_atributo(processo, "situacao")
        ),
        "processo.data_entrada": formatar_data(
            obter_atributo(processo, "data_entrada")
        ),
        "processo.proximo_prazo": formatar_data(
            obter_atributo(processo, "proximo_prazo")
        ),
        "processo.advogado": formatar_valor(
            obter_atributo(processo, "advogado")
        ),
    }


def montar_contexto_usuario(
    usuario: Any,
) -> dict[str, str]:
    if usuario is None:
        return {}

    return {
        "usuario.nome": formatar_valor(
            obter_atributo(usuario, "nome")
        ),
        "usuario.email": formatar_valor(
            obter_atributo(usuario, "email")
        ),
        "usuario.telefone": formatar_valor(
            obter_atributo(usuario, "telefone")
        ),
        "usuario.cargo": formatar_valor(
            obter_atributo(usuario, "cargo")
        ),
        "usuario.perfil": formatar_valor(
            obter_atributo(usuario, "perfil")
        ),
    }


def montar_contexto_escritorio(
    escritorio: Any,
) -> dict[str, str]:
    if escritorio is None:
        return {}

    nome = obter_atributo(
        escritorio,
        "nome",
        obter_atributo(escritorio, "nome_escritorio"),
    )

    logradouro = formatar_valor(
        obter_primeiro_atributo(
            escritorio,
            ["logradouro", "rua"],
        )
    )

    endereco = montar_endereco(escritorio)

    return {
        "escritorio.nome": formatar_valor(nome),
        "escritorio.razao_social": formatar_valor(
            obter_atributo(escritorio, "razao_social")
        ),
        "escritorio.cnpj": formatar_valor(
            obter_atributo(escritorio, "cnpj")
        ),
        "escritorio.oab": formatar_valor(
            obter_atributo(escritorio, "oab")
        ),
        "escritorio.telefone": formatar_valor(
            obter_atributo(escritorio, "telefone")
        ),
        "escritorio.email": formatar_valor(
            obter_atributo(escritorio, "email")
        ),
        "escritorio.site": formatar_valor(
            obter_atributo(escritorio, "site")
        ),
        "escritorio.cep": formatar_cep(
            obter_atributo(escritorio, "cep")
        ),
        "escritorio.logradouro": logradouro,
        "escritorio.rua": logradouro,
        "escritorio.numero": formatar_valor(
            obter_atributo(escritorio, "numero")
        ),
        "escritorio.complemento": formatar_valor(
            obter_atributo(escritorio, "complemento")
        ),
        "escritorio.bairro": formatar_valor(
            obter_atributo(escritorio, "bairro")
        ),
        "escritorio.cidade": formatar_valor(
            obter_atributo(escritorio, "cidade")
        ),
        "escritorio.estado": formatar_valor(
            obter_atributo(escritorio, "estado")
        ).upper(),
        "escritorio.endereco": endereco,
        "escritorio.endereco_completo": endereco,
    }



def formatar_valor_resposta(resposta: Any) -> str:
    """
    Converte uma RespostaFormulario para o texto utilizado nos DOCX.

    Prioriza ``valor_formatado`` porque o próprio modelo de resposta
    já conhece as regras de moeda, data, hora, booleano e listas.
    """
    if resposta is None:
        return ""

    valor_formatado = obter_atributo(
        resposta,
        "valor_formatado",
        None,
    )

    if valor_formatado not in (None, ""):
        return str(valor_formatado)

    valor = obter_atributo(
        resposta,
        "valor",
        "",
    )

    if isinstance(valor, (list, tuple, set, frozenset)):
        return ", ".join(
            formatar_valor(item)
            for item in valor
        )

    return formatar_valor(valor)


def montar_contexto_formulario(
    formulario_caso: Any,
) -> dict[str, str]:
    """
    Transforma as respostas de uma ficha em variáveis de documento.

    Para uma pergunta cujo código seja ``empregador_nome``, são
    disponibilizadas estas formas equivalentes:

        {{ empregador_nome }}
        {{ formulario.empregador_nome }}
        {{ entrevista.empregador_nome }}

    Isso permite usar placeholders simples nos modelos atuais e manter
    um padrão com prefixo nos modelos criados futuramente.
    """
    if formulario_caso is None:
        return {}

    contexto: dict[str, str] = {}

    contexto["formulario.id"] = formatar_valor(
        obter_atributo(formulario_caso, "id")
    )
    contexto["formulario.titulo"] = formatar_valor(
        obter_atributo(formulario_caso, "titulo")
    )
    contexto["formulario.status"] = formatar_valor(
        obter_atributo(formulario_caso, "status")
    )
    contexto["formulario.versao"] = formatar_valor(
        obter_atributo(
            formulario_caso,
            "versao_modelo",
        )
    )
    contexto["formulario.iniciado_em"] = formatar_data(
        obter_atributo(
            formulario_caso,
            "iniciado_em",
        )
    )
    contexto["formulario.concluido_em"] = formatar_data(
        obter_atributo(
            formulario_caso,
            "concluido_em",
        )
    )
    contexto["formulario.observacoes"] = formatar_valor(
        obter_atributo(
            formulario_caso,
            "observacoes",
        )
    )

    respostas = obter_atributo(
        formulario_caso,
        "respostas",
        [],
    ) or []

    for resposta in respostas:
        pergunta = obter_atributo(
            resposta,
            "pergunta",
            None,
        )

        if pergunta is None:
            continue

        codigo = formatar_valor(
            obter_atributo(pergunta, "codigo")
        ).strip()

        if not codigo:
            continue

        valor = formatar_valor_resposta(resposta)

        contexto[codigo] = valor
        contexto[f"formulario.{codigo}"] = valor
        contexto[f"entrevista.{codigo}"] = valor

    return contexto

def montar_contexto_sistema() -> dict[str, str]:
    agora = datetime.now()
    hoje = agora.date()

    valores = {
        "data_atual": formatar_data(hoje),
        "data_atual_extenso": formatar_data_extenso(hoje),
        "hora_atual": agora.strftime("%H:%M"),
        "dia_atual": str(hoje.day),
        "mes_atual": MESES_PORTUGUES.get(
            hoje.month,
            "",
        ),
        "ano_atual": str(hoje.year),
    }

    return {
        **valores,
        **{
            f"sistema.{chave}": valor
            for chave, valor in valores.items()
        },
    }


def montar_contexto_documento(
    cliente: Any = None,
    caso: Any = None,
    processo: Any = None,
    usuario: Any = None,
    escritorio: Any = None,
    formulario_caso: Any = None,
    valores_extras: dict[str, Any] | None = None,
) -> dict[str, str]:
    contexto: dict[str, str] = {}

    contexto.update(montar_contexto_cliente(cliente))
    contexto.update(montar_contexto_caso(caso))
    contexto.update(montar_contexto_processo(processo))
    contexto.update(montar_contexto_usuario(usuario))
    contexto.update(montar_contexto_escritorio(escritorio))
    contexto.update(montar_contexto_formulario(formulario_caso))
    contexto.update(montar_contexto_sistema())

    if valores_extras:
        for chave, valor in valores_extras.items():
            contexto[str(chave).strip()] = formatar_valor(
                valor
            )

    return contexto