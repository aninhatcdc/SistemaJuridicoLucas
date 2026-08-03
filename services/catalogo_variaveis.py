from collections import OrderedDict


CATALOGO_VARIAVEIS = OrderedDict(
    {
        "cliente": OrderedDict(
            {
                "nome": "Nome completo do cliente",
                "cpf": "CPF do cliente",
                "rg": "Número do RG",
                "rg_completo": "RG com órgão expedidor e UF",
                "orgao_expedidor": "Órgão expedidor do RG",
                "uf_rg": "UF do RG",
                "data_nascimento": "Data de nascimento",
                "sexo": "Sexo",
                "nacionalidade": "Nacionalidade",
                "naturalidade": "Cidade de nascimento",
                "uf_naturalidade": "UF de nascimento",
                "naturalidade_completa": "Naturalidade com cidade e UF",
                "estado_civil": "Estado civil",
                "profissao": "Profissão",
                "nome_mae": "Nome da mãe",
                "nome_pai": "Nome do pai",
                "telefone": "Telefone",
                "whatsapp": "WhatsApp",
                "email": "E-mail",
                "cep": "CEP",
                "logradouro": "Logradouro",
                "rua": "Logradouro (nome antigo, mantido por compatibilidade)",
                "numero": "Número do endereço",
                "complemento": "Complemento",
                "bairro": "Bairro",
                "cidade": "Cidade",
                "estado": "Estado",
                "endereco": "Endereço completo",
                "endereco_completo": "Endereço completo",
                "origem": "Origem do cliente",
                "observacoes": "Observações do cliente",
                "ativo": "Indica se o cliente está ativo",
                "criado_em": "Data de criação do cadastro",
                "atualizado_em": "Data da última atualização",
            }
        ),

        "caso": OrderedDict(
            {
                "numero_interno": "Número interno do caso",
                "titulo": "Título do caso",
                "area": "Área jurídica do caso",
                "status": "Status do caso",
                "descricao": "Descrição do caso",
                "data_abertura": "Data de abertura",
            }
        ),

        "processo": OrderedDict(
            {
                "numero_cnj": "Número CNJ",
                "numero": "Número do processo",
                "tribunal": "Tribunal",
                "comarca": "Comarca",
                "vara": "Vara",
                "fase": "Fase processual",
                "situacao": "Situação do processo",
                "data_entrada": "Data de entrada",
                "proximo_prazo": "Próximo prazo",
                "advogado": "Advogado responsável",
            }
        ),

        "usuario": OrderedDict(
            {
                "nome": "Nome do usuário",
                "email": "E-mail do usuário",
                "telefone": "Telefone do usuário",
                "cargo": "Cargo do usuário",
                "perfil": "Perfil de acesso",
            }
        ),

        "escritorio": OrderedDict(
            {
                "nome": "Nome do escritório",
                "razao_social": "Razão social",
                "cnpj": "CNPJ",
                "oab": "Registro da OAB",
                "telefone": "Telefone",
                "email": "E-mail",
                "site": "Site",
                "cep": "CEP",
                "logradouro": "Logradouro",
                "rua": "Logradouro (nome antigo, mantido por compatibilidade)",
                "numero": "Número",
                "complemento": "Complemento",
                "bairro": "Bairro",
                "cidade": "Cidade",
                "estado": "Estado",
                "endereco": "Endereço completo",
                "endereco_completo": "Endereço completo",
            }
        ),
    }
)


VARIAVEIS_DO_SISTEMA = OrderedDict(
    {
        "data_atual": "Data atual",
        "data_atual_extenso": "Data atual por extenso",
        "hora_atual": "Hora atual",
        "dia_atual": "Dia atual",
        "mes_atual": "Mês atual",
        "ano_atual": "Ano atual",
        "sistema.data_atual": "Data atual",
        "sistema.data_atual_extenso": "Data atual por extenso",
        "sistema.hora_atual": "Hora atual",
        "sistema.dia_atual": "Dia atual",
        "sistema.mes_atual": "Mês atual",
        "sistema.ano_atual": "Ano atual",
    }
)


def normalizar_codigo(codigo):
    if codigo is None:
        return ""

    return str(codigo).strip()


def listar_variaveis():
    variaveis = []

    for grupo, campos in CATALOGO_VARIAVEIS.items():
        for campo, descricao in campos.items():
            variaveis.append(
                {
                    "codigo": f"{grupo}.{campo}",
                    "grupo": grupo,
                    "campo": campo,
                    "descricao": descricao,
                    "tipo": "cadastro",
                }
            )

    for codigo, descricao in VARIAVEIS_DO_SISTEMA.items():
        campo = (
            codigo.split(".", 1)[1]
            if codigo.startswith("sistema.")
            else codigo
        )

        variaveis.append(
            {
                "codigo": codigo,
                "grupo": "sistema",
                "campo": campo,
                "descricao": descricao,
                "tipo": "sistema",
            }
        )

    return variaveis


def obter_dados_variavel(codigo):
    codigo = normalizar_codigo(codigo)

    if not codigo:
        return None

    if codigo in VARIAVEIS_DO_SISTEMA:
        campo = (
            codigo.split(".", 1)[1]
            if codigo.startswith("sistema.")
            else codigo
        )

        return {
            "codigo": codigo,
            "grupo": "sistema",
            "campo": campo,
            "descricao": VARIAVEIS_DO_SISTEMA[codigo],
            "tipo": "sistema",
        }

    if "." not in codigo:
        return None

    grupo, campo = codigo.split(".", 1)

    grupo = grupo.strip()
    campo = campo.strip()

    if not grupo or not campo:
        return None

    campos_grupo = CATALOGO_VARIAVEIS.get(grupo)

    if not campos_grupo:
        return None

    descricao = campos_grupo.get(campo)

    if not descricao:
        return None

    return {
        "codigo": codigo,
        "grupo": grupo,
        "campo": campo,
        "descricao": descricao,
        "tipo": "cadastro",
    }


def existe_variavel(codigo):
    return obter_dados_variavel(codigo) is not None


def validar_variavel(codigo):
    codigo = normalizar_codigo(codigo)

    dados = obter_dados_variavel(codigo)

    if dados:
        return {
            **dados,
            "valida": True,
            "mensagem": "Variável reconhecida pelo sistema.",
        }

    grupo = None
    campo = codigo

    if "." in codigo:
        grupo, campo = codigo.split(".", 1)

    return {
        "codigo": codigo,
        "grupo": grupo or "desconhecido",
        "campo": campo,
        "descricao": "Variável inexistente no catálogo",
        "tipo": "desconhecido",
        "valida": False,
        "mensagem": (
            "Esta variável não está cadastrada e não poderá "
            "ser preenchida automaticamente."
        ),
    }


def validar_variaveis(variaveis):
    resultado = []
    codigos_adicionados = set()

    for variavel in variaveis or []:
        codigo = normalizar_codigo(variavel)

        if not codigo or codigo in codigos_adicionados:
            continue

        codigos_adicionados.add(codigo)
        resultado.append(validar_variavel(codigo))

    return sorted(
        resultado,
        key=lambda item: (
            not item["valida"],
            item["codigo"].lower(),
        ),
    )


def contar_variaveis_validas(variaveis):
    return sum(
        1
        for item in validar_variaveis(variaveis)
        if item["valida"]
    )


def contar_variaveis_invalidas(variaveis):
    return sum(
        1
        for item in validar_variaveis(variaveis)
        if not item["valida"]
    )