"""
Seed da Ficha de Atendimento Trabalhista.

Cria ou atualiza o modelo "Entrevista Trabalhista" e suas perguntas
sem apagar formulários já preenchidos ou respostas existentes.

O seed é idempotente:
- cria o formulário quando ele ainda não existe;
- cria perguntas novas;
- atualiza perguntas existentes pelo código;
- não duplica registros.
"""

from models import db
from models.area_juridica import AreaJuridica
from models.formulario_modelo import FormularioModelo
from models.pergunta_formulario import PerguntaFormulario


CODIGO_FORMULARIO = "entrevista_trabalhista"


PERGUNTAS = [
    # ============================================================
    # ETAPA 1 — EMPREGADOR
    # ============================================================
    {
        "codigo": "empregador_nome",
        "texto": "Nome do empregador ou razão social",
        "tipo": "TEXTO",
        "etapa": "Dados do empregador",
        "ordem_etapa": 1,
        "icone": "🏢",
        "grupo": "Identificação",
        "descricao_etapa": (
            "Informe os dados da empresa ou pessoa para quem "
            "o cliente trabalhou."
        ),
        "placeholder": "Ex.: Empresa Exemplo LTDA",
        "obrigatoria": True,
    },
    {
        "codigo": "empregador_cnpj",
        "texto": "CNPJ do empregador",
        "tipo": "CNPJ",
        "etapa": "Dados do empregador",
        "ordem_etapa": 1,
        "icone": "🏢",
        "grupo": "Identificação",
        "placeholder": "00.000.000/0000-00",
        "obrigatoria": False,
    },
    {
        "codigo": "empregador_endereco",
        "texto": "Endereço completo do empregador",
        "tipo": "TEXTO_LONGO",
        "etapa": "Dados do empregador",
        "ordem_etapa": 1,
        "icone": "🏢",
        "grupo": "Endereço",
        "placeholder": (
            "Logradouro, número, complemento, bairro, cidade, UF e CEP"
        ),
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 2 — CONTRATO
    # ============================================================
    {
        "codigo": "cargo_exercido",
        "texto": "Cargo registrado",
        "tipo": "TEXTO",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Função",
        "descricao_etapa": (
            "Registre as informações principais do vínculo de trabalho."
        ),
        "placeholder": "Ex.: Auxiliar administrativo",
        "obrigatoria": True,
    },
    {
        "codigo": "funcao_exercida",
        "texto": "Função efetivamente exercida",
        "tipo": "TEXTO",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Função",
        "placeholder": "Descreva a atividade realmente desempenhada",
        "obrigatoria": False,
    },
    {
        "codigo": "data_admissao",
        "texto": "Data de admissão",
        "tipo": "DATA",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Período",
        "obrigatoria": True,
    },
    {
        "codigo": "data_demissao",
        "texto": "Data de demissão ou término do vínculo",
        "tipo": "DATA",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Período",
        "obrigatoria": False,
    },
    {
        "codigo": "tipo_rescisao",
        "texto": "Tipo de rescisão",
        "tipo": "SELECAO",
        "opcoes": [
            "Ainda trabalha",
            "Dispensa sem justa causa",
            "Pedido de demissão",
            "Dispensa por justa causa",
            "Rescisão indireta",
            "Acordo entre as partes",
            "Contrato por prazo determinado",
            "Outro",
        ],
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Rescisão",
        "obrigatoria": False,
    },
    {
        "codigo": "ctps_numero_serie",
        "texto": "CTPS — número e série",
        "tipo": "TEXTO",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Registro",
        "placeholder": "Ex.: 1234567 / 001-PB",
        "obrigatoria": False,
    },
    {
        "codigo": "pis_nit",
        "texto": "PIS/PASEP ou NIT",
        "tipo": "TEXTO",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Registro",
        "obrigatoria": False,
    },
    {
        "codigo": "registro_ctps",
        "texto": "O vínculo foi registrado na CTPS?",
        "tipo": "SIM_NAO",
        "etapa": "Contrato de trabalho",
        "ordem_etapa": 2,
        "icone": "💼",
        "grupo": "Registro",
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 3 — REMUNERAÇÃO E JORNADA
    # ============================================================
    {
        "codigo": "ultimo_salario",
        "texto": "Último salário ou remuneração mensal",
        "tipo": "MOEDA",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Remuneração",
        "descricao_etapa": (
            "Informe salário, horários e condições da jornada."
        ),
        "placeholder": "Ex.: 2.500,00",
        "obrigatoria": True,
    },
    {
        "codigo": "jornada_contratual",
        "texto": "Jornada de trabalho contratual",
        "tipo": "TEXTO_LONGO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "placeholder": (
            "Ex.: segunda a sexta, das 08h às 18h, "
            "com 1 hora de intervalo"
        ),
        "obrigatoria": False,
    },
    {
        "codigo": "horario_entrada",
        "texto": "Horário habitual de entrada",
        "tipo": "HORA",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "obrigatoria": False,
    },
    {
        "codigo": "horario_saida",
        "texto": "Horário habitual de saída",
        "tipo": "HORA",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "obrigatoria": False,
    },
    {
        "codigo": "intervalo_intrajornada",
        "texto": "O intervalo para refeição e descanso era respeitado?",
        "tipo": "SIM_NAO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "obrigatoria": False,
    },
    {
        "codigo": "duracao_intervalo",
        "texto": "Quanto tempo de intervalo era efetivamente concedido?",
        "tipo": "TEXTO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "placeholder": "Ex.: 30 minutos",
        "obrigatoria": False,
    },
    {
        "codigo": "realizava_horas_extras",
        "texto": "Realizava horas extras?",
        "tipo": "SIM_NAO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Horas extras",
        "obrigatoria": False,
    },
    {
        "codigo": "detalhes_horas_extras",
        "texto": "Descreva a frequência e a quantidade das horas extras",
        "tipo": "TEXTO_LONGO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Horas extras",
        "placeholder": (
            "Ex.: trabalhava duas horas além da jornada, "
            "três vezes por semana"
        ),
        "obrigatoria": False,
    },
    {
        "codigo": "trabalho_domingo_feriado",
        "texto": "Trabalhava aos domingos ou feriados?",
        "tipo": "SIM_NAO",
        "etapa": "Remuneração e jornada",
        "ordem_etapa": 3,
        "icone": "💰",
        "grupo": "Jornada",
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 4 — VERBAS E CONDIÇÕES
    # ============================================================
    {
        "codigo": "fgts_regular",
        "texto": "Os depósitos do FGTS eram realizados corretamente?",
        "tipo": "SIM_NAO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Verbas",
        "descricao_etapa": (
            "Registre possíveis irregularidades contratuais "
            "e condições de trabalho."
        ),
        "obrigatoria": False,
    },
    {
        "codigo": "ferias_regulares",
        "texto": "As férias eram concedidas e pagas corretamente?",
        "tipo": "SIM_NAO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Verbas",
        "obrigatoria": False,
    },
    {
        "codigo": "decimo_terceiro_regular",
        "texto": "O 13º salário era pago corretamente?",
        "tipo": "SIM_NAO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Verbas",
        "obrigatoria": False,
    },
    {
        "codigo": "recebia_insalubridade",
        "texto": "Recebia adicional de insalubridade?",
        "tipo": "SIM_NAO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Adicionais",
        "obrigatoria": False,
    },
    {
        "codigo": "recebia_periculosidade",
        "texto": "Recebia adicional de periculosidade?",
        "tipo": "SIM_NAO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Adicionais",
        "obrigatoria": False,
    },
    {
        "codigo": "condicoes_trabalho",
        "texto": "Descreva as condições de trabalho relevantes",
        "tipo": "TEXTO_LONGO",
        "etapa": "Verbas e condições de trabalho",
        "ordem_etapa": 4,
        "icone": "⚖️",
        "grupo": "Condições",
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 5 — DEMANDA
    # ============================================================
    {
        "codigo": "tipos_demanda",
        "texto": "Quais são os principais temas da demanda?",
        "tipo": "MULTIPLA_SELECAO",
        "opcoes": [
            "Rescisão indireta",
            "Verbas rescisórias não pagas",
            "Horas extras",
            "Equiparação salarial",
            "Assédio moral ou dano existencial",
            "Acidente de trabalho",
            "Doença ocupacional",
            "Reconhecimento de vínculo empregatício",
            "FGTS não depositado",
            "Insalubridade",
            "Periculosidade",
            "Estabilidade",
            "Outro",
        ],
        "etapa": "Demanda trabalhista",
        "ordem_etapa": 5,
        "icone": "📋",
        "grupo": "Pedidos",
        "descricao_etapa": (
            "Selecione os assuntos e registre o relato completo do cliente."
        ),
        "obrigatoria": False,
    },
    {
        "codigo": "outro_tipo_demanda",
        "texto": "Outro tema ou pedido não listado",
        "tipo": "TEXTO",
        "etapa": "Demanda trabalhista",
        "ordem_etapa": 5,
        "icone": "📋",
        "grupo": "Pedidos",
        "obrigatoria": False,
    },
    {
        "codigo": "resumo_caso",
        "texto": "Resumo do caso e motivo do atendimento",
        "tipo": "TEXTO_LONGO",
        "etapa": "Demanda trabalhista",
        "ordem_etapa": 5,
        "icone": "📋",
        "grupo": "Relato",
        "placeholder": (
            "Registre os fatos na ordem em que ocorreram, "
            "incluindo datas, pessoas envolvidas e prejuízos."
        ),
        "obrigatoria": True,
    },
    {
        "codigo": "encaminhamentos",
        "texto": "Encaminhamentos e próximos passos",
        "tipo": "TEXTO_LONGO",
        "etapa": "Demanda trabalhista",
        "ordem_etapa": 5,
        "icone": "📋",
        "grupo": "Encaminhamento",
        "obrigatoria": False,
    },
    {
        "codigo": "testemunhas",
        "texto": "Testemunhas — nomes e contatos",
        "tipo": "TEXTO_LONGO",
        "etapa": "Demanda trabalhista",
        "ordem_etapa": 5,
        "icone": "📋",
        "grupo": "Provas",
        "placeholder": (
            "Informe nome, telefone e o que cada testemunha presenciou."
        ),
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 6 — DOCUMENTOS
    # ============================================================
    {
        "codigo": "documentos_apresentados",
        "texto": "Documentos já apresentados pelo cliente",
        "tipo": "MULTIPLA_SELECAO",
        "opcoes": [
            "Documento de identidade (RG ou CNH)",
            "CPF",
            "Comprovante de residência atualizado",
            "Carteira de Trabalho (CTPS)",
            "Contrato de trabalho",
            "Holerites ou contracheques",
            "TRCT",
            "Extrato do FGTS",
            "Extrato do PIS/PASEP",
            "Comprovante de seguro-desemprego",
            "Cartões de ponto ou controle de jornada",
            "Exames admissionais ou demissionais",
            "Atestados médicos ou CAT",
            "E-mails ou mensagens",
            "Fotos ou vídeos",
            "Dados de testemunhas",
            "Procuração assinada",
            "Contrato de honorários assinado",
            "Declaração de hipossuficiência",
        ],
        "etapa": "Documentos e provas",
        "ordem_etapa": 6,
        "icone": "📎",
        "grupo": "Checklist",
        "descricao_etapa": (
            "Marque os documentos recebidos durante o atendimento."
        ),
        "obrigatoria": False,
    },
    {
        "codigo": "documentos_pendentes",
        "texto": "Documentos que ainda precisam ser apresentados",
        "tipo": "TEXTO_LONGO",
        "etapa": "Documentos e provas",
        "ordem_etapa": 6,
        "icone": "📎",
        "grupo": "Pendências",
        "obrigatoria": False,
    },
    {
        "codigo": "outras_provas",
        "texto": "Outras provas disponíveis",
        "tipo": "TEXTO_LONGO",
        "etapa": "Documentos e provas",
        "ordem_etapa": 6,
        "icone": "📎",
        "grupo": "Provas",
        "obrigatoria": False,
    },

    # ============================================================
    # ETAPA 7 — FINALIZAÇÃO
    # ============================================================
    {
        "codigo": "observacoes_atendimento",
        "texto": "Observações finais do atendimento",
        "tipo": "TEXTO_LONGO",
        "etapa": "Finalização",
        "ordem_etapa": 7,
        "icone": "📝",
        "grupo": "Observações",
        "descricao_etapa": (
            "Registre informações internas relevantes para o escritório."
        ),
        "obrigatoria": False,
    },
]


def obter_area_trabalhista():
    return (
        AreaJuridica.query
        .filter_by(slug="trabalhista")
        .first()
    )


def obter_ou_criar_formulario():
    formulario = (
        FormularioModelo.query
        .filter_by(codigo=CODIGO_FORMULARIO)
        .first()
    )

    if formulario is None:
        formulario = FormularioModelo(
            nome="Entrevista Trabalhista",
            codigo=CODIGO_FORMULARIO,
            descricao=(
                "Ficha de atendimento trabalhista utilizada para "
                "qualificação, entrevista, checklist e geração "
                "automática de documentos."
            ),
            versao=1,
            ativo=True,
        )

        db.session.add(formulario)
        db.session.flush()

    formulario.nome = "Entrevista Trabalhista"
    formulario.descricao = (
        "Ficha de atendimento trabalhista utilizada para "
        "qualificação, entrevista, checklist e geração "
        "automática de documentos."
    )
    formulario.ativo = True

    area = obter_area_trabalhista()

    if area:
        formulario.area_juridica = area

    return formulario


def atualizar_pergunta(pergunta, item, ordem):
    pergunta.texto = item["texto"]
    pergunta.tipo = item.get("tipo", "TEXTO")
    pergunta.ordem = ordem
    pergunta.etapa = item.get("etapa", "Geral")
    pergunta.ordem_etapa = item.get("ordem_etapa", 1)
    pergunta.icone = item.get("icone", "📄")
    pergunta.grupo = item.get("grupo") or None
    pergunta.descricao = item.get("descricao") or None
    pergunta.descricao_etapa = (
        item.get("descricao_etapa")
        or None
    )
    pergunta.placeholder = item.get("placeholder") or None
    pergunta.valor_padrao = item.get("valor_padrao") or None
    pergunta.obrigatoria = item.get("obrigatoria", False)
    pergunta.ativo = item.get("ativo", True)

    if pergunta.tipo in {
        "SELECAO",
        "MULTIPLA_SELECAO",
    }:
        pergunta.opcoes = item.get("opcoes", [])
    else:
        pergunta.opcoes = []


def sincronizar_perguntas(formulario):
    existentes = {
        pergunta.codigo: pergunta
        for pergunta in formulario.perguntas
    }

    codigos_seed = set()

    for ordem, item in enumerate(
        PERGUNTAS,
        start=1,
    ):
        codigo = item["codigo"].strip()
        codigos_seed.add(codigo)

        pergunta = existentes.get(codigo)

        if pergunta is None:
            pergunta = PerguntaFormulario(
                formulario_modelo=formulario,
                codigo=codigo,
            )

            db.session.add(pergunta)

        atualizar_pergunta(
            pergunta,
            item,
            ordem,
        )

    # Não exclui perguntas antigas para preservar respostas.
    # Perguntas que saíram do seed ficam inativas.
    for codigo, pergunta in existentes.items():
        if codigo not in codigos_seed:
            pergunta.ativo = False


def criar_formulario_trabalhista():
    try:
        formulario = obter_ou_criar_formulario()

        sincronizar_perguntas(
            formulario
        )

        db.session.commit()

        return formulario

    except Exception:
        db.session.rollback()
        raise