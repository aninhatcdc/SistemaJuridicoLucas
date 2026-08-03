"""
Cria ou atualiza as entrevistas das áreas:

- Previdenciário
- Cível
- Consumidor
- Criminal

Uso:
    python scripts/criar_entrevistas_areas.py

O script é idempotente:
- não duplica formulários;
- não duplica perguntas;
- atualiza perguntas existentes pelo código;
- preserva formulários já preenchidos.
"""

import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from app import create_app
from models import db
from models.area_juridica import AreaJuridica
from models.formulario_modelo import FormularioModelo
from models.pergunta_formulario import PerguntaFormulario


AREAS = {
    "previdenciario": {
        "nome": "Previdenciário",
        "icone": "👴",
        "cor": "#6f42c1",
        "ordem": 20,
    },
    "civel": {
        "nome": "Cível",
        "icone": "📑",
        "cor": "#0d6efd",
        "ordem": 30,
    },
    "consumidor": {
        "nome": "Consumidor",
        "icone": "🛒",
        "cor": "#fd7e14",
        "ordem": 40,
    },
    "criminal": {
        "nome": "Criminal",
        "icone": "⚖️",
        "cor": "#dc3545",
        "ordem": 50,
    },
}


FORMULARIOS = {
    "previdenciario": {
        "nome": "Entrevista Previdenciária",
        "codigo": "entrevista_previdenciaria",
        "descricao": (
            "Entrevista inicial para levantamento da situação "
            "previdenciária, histórico contributivo e benefício pretendido."
        ),
        "perguntas": [
            {
                "codigo": "segurado_inss",
                "texto": "É segurado(a) do INSS?",
                "tipo": "SIM_NAO",
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
                "obrigatoria": True,
            },
            {
                "codigo": "categoria_segurado",
                "texto": (
                    "Em qual categoria se enquadra "
                    "(empregado, contribuinte individual, facultativo, "
                    "segurado especial rural ou outra)?"
                ),
                "tipo": "SELECAO",
                "opcoes": [
                    "Empregado",
                    "Contribuinte individual",
                    "Facultativo",
                    "Segurado especial rural",
                    "Desempregado",
                    "Outro",
                ],
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "contribuindo_atualmente",
                "texto": "Está contribuindo atualmente?",
                "tipo": "SIM_NAO",
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "desde_quando_contribui",
                "texto": "Desde quando está contribuindo atualmente?",
                "tipo": "TEXTO",
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "beneficio_ja_requerido",
                "texto": "Já requereu algum benefício ao INSS?",
                "tipo": "SIM_NAO",
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "beneficio_ja_requerido_detalhes",
                "texto": (
                    "Qual benefício foi requerido e qual foi o resultado "
                    "(concedido, negado ou em análise)?"
                ),
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação previdenciária atual",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "beneficio_pretendido",
                "texto": "Qual benefício pretende requerer ou está questionando?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Benefício pretendido",
                "ordem_etapa": 2,
                "icone": "📄",
                "obrigatoria": True,
            },
            {
                "codigo": "numero_beneficio",
                "texto": "Número do benefício (NB), se houver",
                "tipo": "TEXTO",
                "etapa": "Benefício pretendido",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "data_requerimento_der",
                "texto": "Data do requerimento administrativo (DER), se houver",
                "tipo": "DATA",
                "etapa": "Benefício pretendido",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "situacao_beneficio",
                "texto": "Situação atual do benefício",
                "tipo": "SELECAO",
                "opcoes": [
                    "Não requerido",
                    "Em análise",
                    "Concedido",
                    "Negado",
                    "Cessado",
                    "Suspenso",
                    "Outro",
                ],
                "etapa": "Benefício pretendido",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "possui_documentos_medicos",
                "texto": "Possui laudos, exames ou atestados médicos?",
                "tipo": "SIM_NAO",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "documentos_medicos_detalhes",
                "texto": "Descreva os documentos médicos disponíveis",
                "tipo": "TEXTO_LONGO",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "afastado_trabalho",
                "texto": "Está afastado(a) do trabalho atualmente?",
                "tipo": "SIM_NAO",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "data_inicio_afastamento",
                "texto": "Desde quando está afastado(a)?",
                "tipo": "DATA",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "passou_pericia_inss",
                "texto": "Já passou por perícia do INSS?",
                "tipo": "SIM_NAO",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "resultado_pericia",
                "texto": "Qual foi o resultado da perícia?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Incapacidade e perícia",
                "ordem_etapa": 3,
                "icone": "🩺",
            },
            {
                "codigo": "trabalhou_carteira_assinada",
                "texto": "Já trabalhou com carteira assinada?",
                "tipo": "SIM_NAO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "empregos_e_periodos",
                "texto": "Informe empresas e períodos trabalhados",
                "tipo": "TEXTO_LONGO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "contribuiu_autonomo",
                "texto": "Já contribuiu como autônomo(a) ou contribuinte individual?",
                "tipo": "SIM_NAO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "possui_carnes",
                "texto": "Possui carnês ou comprovantes dessas contribuições?",
                "tipo": "SIM_NAO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "atividade_rural",
                "texto": "Já exerceu atividade rural?",
                "tipo": "SIM_NAO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "provas_atividade_rural",
                "texto": "Como pode comprovar a atividade rural?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "periodos_sem_contribuicao",
                "texto": "Houve períodos sem contribuição? Explique os motivos",
                "tipo": "TEXTO_LONGO",
                "etapa": "Histórico contributivo",
                "ordem_etapa": 4,
                "icone": "📚",
            },
            {
                "codigo": "grau_parentesco_falecido",
                "texto": "Para pensão por morte: qual o grau de parentesco com o falecido?",
                "tipo": "TEXTO",
                "etapa": "Pensão por morte",
                "ordem_etapa": 5,
                "icone": "🕊️",
            },
            {
                "codigo": "falecido_segurado",
                "texto": "O falecido era segurado do INSS e contribuía na data do óbito?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Pensão por morte",
                "ordem_etapa": 5,
                "icone": "🕊️",
            },
            {
                "codigo": "outros_dependentes",
                "texto": "Há outros dependentes habilitados ou a habilitar?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Pensão por morte",
                "ordem_etapa": 5,
                "icone": "🕊️",
            },
            {
                "codigo": "renda_grupo_familiar",
                "texto": "Para BPC/LOAS: qual a renda mensal do grupo familiar?",
                "tipo": "MOEDA",
                "etapa": "BPC/LOAS",
                "ordem_etapa": 6,
                "icone": "🏠",
            },
            {
                "codigo": "quantidade_grupo_familiar",
                "texto": "Quantas pessoas compõem o grupo familiar?",
                "tipo": "NUMERO",
                "etapa": "BPC/LOAS",
                "ordem_etapa": 6,
                "icone": "🏠",
            },
            {
                "codigo": "laudo_deficiencia_bpc",
                "texto": "Possui laudo médico comprovando deficiência ou incapacidade?",
                "tipo": "SIM_NAO",
                "etapa": "BPC/LOAS",
                "ordem_etapa": 6,
                "icone": "🏠",
            },
            {
                "codigo": "possui_cnis_atualizado",
                "texto": "Possui CNIS atualizado?",
                "tipo": "SIM_NAO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 7,
                "icone": "📎",
            },
            {
                "codigo": "possui_carta_indeferimento",
                "texto": "Possui carta de indeferimento ou decisão do INSS?",
                "tipo": "SIM_NAO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 7,
                "icone": "📎",
            },
            {
                "codigo": "urgencia_previdenciaria",
                "texto": "Há urgência? Descreva",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas",
                "ordem_etapa": 8,
                "icone": "🎯",
            },
            {
                "codigo": "recurso_administrativo",
                "texto": "Já tentou recurso administrativo junto ao INSS?",
                "tipo": "SIM_NAO",
                "etapa": "Expectativas",
                "ordem_etapa": 8,
                "icone": "🎯",
            },
        ],
    },

    "civel": {
        "nome": "Entrevista Cível",
        "codigo": "entrevista_civel",
        "descricao": (
            "Entrevista inicial para delimitar as partes, a relação "
            "jurídica, os fatos controvertidos, danos e provas."
        ),
        "perguntas": [
            {
                "codigo": "parte_contraria_nome",
                "texto": "Quem é a parte contrária? Informe nome ou razão social",
                "tipo": "TEXTO",
                "etapa": "Identificação das partes",
                "ordem_etapa": 1,
                "icone": "👥",
                "obrigatoria": True,
            },
            {
                "codigo": "parte_contraria_cpf_cnpj",
                "texto": "CPF ou CNPJ da parte contrária, se conhecido",
                "tipo": "TEXTO",
                "etapa": "Identificação das partes",
                "ordem_etapa": 1,
                "icone": "👥",
            },
            {
                "codigo": "parte_contraria_endereco",
                "texto": "Endereço e contato da parte contrária",
                "tipo": "TEXTO_LONGO",
                "etapa": "Identificação das partes",
                "ordem_etapa": 1,
                "icone": "👥",
            },
            {
                "codigo": "relacao_entre_partes",
                "texto": "Qual é a relação entre o cliente e a parte contrária?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Identificação das partes",
                "ordem_etapa": 1,
                "icone": "👥",
            },
            {
                "codigo": "existe_contrato",
                "texto": "Existe contrato por escrito?",
                "tipo": "SIM_NAO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "contrato_detalhes",
                "texto": "Quais são as principais cláusulas envolvidas?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "origem_conflito",
                "texto": "Quando e como surgiu o problema ou conflito?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
                "obrigatoria": True,
            },
            {
                "codigo": "obrigacao_descumprida",
                "texto": "Houve descumprimento de alguma obrigação? Por quem?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "tentativa_amigavel",
                "texto": "Já tentou resolver a questão amigavelmente?",
                "tipo": "SIM_NAO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "resultado_tentativa_amigavel",
                "texto": "Como reagiu a parte contrária?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato e relação jurídica",
                "ordem_etapa": 2,
                "icone": "📄",
            },
            {
                "codigo": "tipos_danos",
                "texto": "Quais danos foram sofridos?",
                "tipo": "MULTIPLA_SELECAO",
                "opcoes": [
                    "Danos materiais",
                    "Danos morais",
                    "Lucros cessantes",
                    "Danos estéticos",
                    "Outros",
                ],
                "etapa": "Danos e prejuízos",
                "ordem_etapa": 3,
                "icone": "💰",
            },
            {
                "codigo": "valor_prejuizo",
                "texto": "Qual o valor estimado do prejuízo financeiro?",
                "tipo": "MOEDA",
                "etapa": "Danos e prejuízos",
                "ordem_etapa": 3,
                "icone": "💰",
            },
            {
                "codigo": "comprovantes_prejuizo",
                "texto": "Há comprovantes do prejuízo? Quais?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Danos e prejuízos",
                "ordem_etapa": 3,
                "icone": "💰",
            },
            {
                "codigo": "impacto_dano_moral",
                "texto": "Como os fatos afetaram a rotina, saúde, imagem ou dignidade do cliente?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Danos e prejuízos",
                "ordem_etapa": 3,
                "icone": "💰",
            },
            {
                "codigo": "documentos_provas",
                "texto": "Quais documentos e provas estão disponíveis?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 4,
                "icone": "📎",
            },
            {
                "codigo": "testemunhas",
                "texto": "Há testemunhas? Informe nome e contato",
                "tipo": "TEXTO_LONGO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 4,
                "icone": "📎",
            },
            {
                "codigo": "fotos_videos_laudos",
                "texto": "Existem fotos, vídeos ou laudos que comprovem os fatos?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 4,
                "icone": "📎",
            },
            {
                "codigo": "processo_em_andamento",
                "texto": "Já existe processo judicial em andamento sobre o mesmo fato?",
                "tipo": "SIM_NAO",
                "etapa": "Situação processual",
                "ordem_etapa": 5,
                "icone": "⚖️",
            },
            {
                "codigo": "numero_processo_relacionado",
                "texto": "Número do processo relacionado, se houver",
                "tipo": "TEXTO",
                "etapa": "Situação processual",
                "ordem_etapa": 5,
                "icone": "⚖️",
            },
            {
                "codigo": "notificacao_recebida",
                "texto": "Já recebeu notificação extrajudicial ou judicial?",
                "tipo": "SIM_NAO",
                "etapa": "Situação processual",
                "ordem_etapa": 5,
                "icone": "⚖️",
            },
            {
                "codigo": "notificacao_detalhes",
                "texto": "Detalhe a notificação recebida",
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação processual",
                "ordem_etapa": 5,
                "icone": "⚖️",
            },
            {
                "codigo": "pretensao_civel",
                "texto": "O que o cliente pretende obter?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas",
                "ordem_etapa": 6,
                "icone": "🎯",
                "obrigatoria": True,
            },
            {
                "codigo": "urgencia_civel",
                "texto": "Há urgência, risco de prescrição ou necessidade de tutela?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas",
                "ordem_etapa": 6,
                "icone": "🎯",
            },
        ],
    },

    "consumidor": {
        "nome": "Entrevista Consumidor",
        "codigo": "entrevista_consumidor",
        "descricao": (
            "Entrevista inicial sobre relação de consumo, falha do produto "
            "ou serviço, tentativas de solução, prejuízos e provas."
        ),
        "perguntas": [
            {
                "codigo": "produto_servico",
                "texto": "Qual produto ou serviço foi adquirido?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
                "obrigatoria": True,
            },
            {
                "codigo": "data_compra",
                "texto": "Data da compra ou contratação",
                "tipo": "DATA",
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
            },
            {
                "codigo": "valor_compra",
                "texto": "Valor da compra ou contratação",
                "tipo": "MOEDA",
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
            },
            {
                "codigo": "fornecedor_nome",
                "texto": "Nome ou razão social do fornecedor",
                "tipo": "TEXTO",
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
                "obrigatoria": True,
            },
            {
                "codigo": "fornecedor_cnpj",
                "texto": "CNPJ do fornecedor, se conhecido",
                "tipo": "CNPJ",
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
            },
            {
                "codigo": "forma_contratacao",
                "texto": "Como foi feita a contratação?",
                "tipo": "SELECAO",
                "opcoes": [
                    "Loja física",
                    "Internet",
                    "Aplicativo",
                    "Telefone",
                    "Representante",
                    "Outro",
                ],
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
            },
            {
                "codigo": "forma_pagamento",
                "texto": "Qual foi a forma de pagamento?",
                "tipo": "SELECAO",
                "opcoes": [
                    "Dinheiro",
                    "Cartão de crédito",
                    "Cartão de débito",
                    "Pix",
                    "Boleto",
                    "Financiamento",
                    "Outro",
                ],
                "etapa": "Relação de consumo",
                "ordem_etapa": 1,
                "icone": "🛒",
            },
            {
                "codigo": "problema_relato",
                "texto": "Qual foi o defeito do produto ou a falha do serviço?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Problema",
                "ordem_etapa": 2,
                "icone": "⚠️",
                "obrigatoria": True,
            },
            {
                "codigo": "data_inicio_problema",
                "texto": "Quando o problema começou?",
                "tipo": "DATA",
                "etapa": "Problema",
                "ordem_etapa": 2,
                "icone": "⚠️",
            },
            {
                "codigo": "contato_fornecedor",
                "texto": "Já entrou em contato com o fornecedor?",
                "tipo": "SIM_NAO",
                "etapa": "Problema",
                "ordem_etapa": 2,
                "icone": "⚠️",
            },
            {
                "codigo": "resposta_fornecedor",
                "texto": "Qual foi a resposta recebida?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Problema",
                "ordem_etapa": 2,
                "icone": "⚠️",
            },
            {
                "codigo": "protocolo_atendimento",
                "texto": "Informe os números de protocolo disponíveis",
                "tipo": "TEXTO_LONGO",
                "etapa": "Problema",
                "ordem_etapa": 2,
                "icone": "⚠️",
            },
            {
                "codigo": "solucao_oferecida",
                "texto": "O fornecedor ofereceu troca, reparo ou devolução?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Tentativas de solução",
                "ordem_etapa": 3,
                "icone": "🔧",
            },
            {
                "codigo": "solucao_aceita_recusada",
                "texto": "O que foi aceito ou recusado pelo cliente?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Tentativas de solução",
                "ordem_etapa": 3,
                "icone": "🔧",
            },
            {
                "codigo": "tempo_desde_reclamacao",
                "texto": "Quanto tempo se passou desde a primeira reclamação?",
                "tipo": "TEXTO",
                "etapa": "Tentativas de solução",
                "ordem_etapa": 3,
                "icone": "🔧",
            },
            {
                "codigo": "prejuizo_financeiro_extra",
                "texto": "Houve prejuízo financeiro além do valor pago?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prejuízos",
                "ordem_etapa": 4,
                "icone": "💰",
            },
            {
                "codigo": "dano_moral",
                "texto": "Houve constrangimento, abalo de crédito ou outro dano moral?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prejuízos",
                "ordem_etapa": 4,
                "icone": "💰",
            },
            {
                "codigo": "negativacao",
                "texto": "O nome do cliente está negativado no SPC ou Serasa?",
                "tipo": "SIM_NAO",
                "etapa": "Prejuízos",
                "ordem_etapa": 4,
                "icone": "💰",
            },
            {
                "codigo": "data_negativacao",
                "texto": "Desde quando ocorreu a negativação?",
                "tipo": "DATA",
                "etapa": "Prejuízos",
                "ordem_etapa": 4,
                "icone": "💰",
            },
            {
                "codigo": "possui_nota_contrato_pagamento",
                "texto": "Possui nota fiscal, contrato ou comprovantes de pagamento?",
                "tipo": "SIM_NAO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 5,
                "icone": "📎",
            },
            {
                "codigo": "possui_conversas_protocolos",
                "texto": "Possui prints, e-mails, conversas ou protocolos?",
                "tipo": "SIM_NAO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 5,
                "icone": "📎",
            },
            {
                "codigo": "possui_extrato_negativacao",
                "texto": "Possui extrato de negativação?",
                "tipo": "SIM_NAO",
                "etapa": "Documentos e provas",
                "ordem_etapa": 5,
                "icone": "📎",
            },
            {
                "codigo": "pretensao_consumidor",
                "texto": "O que pretende obter com a medida?",
                "tipo": "MULTIPLA_SELECAO",
                "opcoes": [
                    "Reparo",
                    "Troca",
                    "Cancelamento",
                    "Devolução do valor",
                    "Retirada da negativação",
                    "Indenização",
                    "Outro",
                ],
                "etapa": "Expectativas",
                "ordem_etapa": 6,
                "icone": "🎯",
                "obrigatoria": True,
            },
            {
                "codigo": "urgencia_consumidor",
                "texto": "Há alguma urgência específica?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas",
                "ordem_etapa": 6,
                "icone": "🎯",
            },
        ],
    },

    "criminal": {
        "nome": "Entrevista Criminal",
        "codigo": "entrevista_criminal",
        "descricao": (
            "Entrevista inicial criminal com ênfase em flagrante, prisão, "
            "inquérito, processo, provas e situação pessoal."
        ),
        "perguntas": [
            {
                "codigo": "nome_preferido",
                "texto": "Como o cliente prefere ser chamado(a)?",
                "tipo": "TEXTO",
                "etapa": "Identificação e contexto",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "situacao_liberdade",
                "texto": "Está preso(a) atualmente ou responde em liberdade?",
                "tipo": "SELECAO",
                "opcoes": [
                    "Preso(a)",
                    "Em liberdade",
                    "Prisão domiciliar",
                    "Foragido(a)",
                    "Outra situação",
                ],
                "etapa": "Identificação e contexto",
                "ordem_etapa": 1,
                "icone": "👤",
                "obrigatoria": True,
            },
            {
                "codigo": "acusacao_formal",
                "texto": "Já foi comunicado(a) formalmente da acusação ou do motivo da prisão?",
                "tipo": "SIM_NAO",
                "etapa": "Identificação e contexto",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "conhecimento_caso",
                "texto": "Como e quando tomou conhecimento do processo ou flagrante?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Identificação e contexto",
                "ordem_etapa": 1,
                "icone": "👤",
            },
            {
                "codigo": "data_prisao",
                "texto": "Data da prisão",
                "tipo": "DATA",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "hora_prisao",
                "texto": "Hora aproximada da prisão",
                "tipo": "HORA",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "local_prisao",
                "texto": "Local da prisão",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "responsavel_prisao",
                "texto": "Quem efetuou a prisão?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "direitos_informados",
                "texto": "Foi informado(a) dos seus direitos?",
                "tipo": "SIM_NAO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "uso_forca",
                "texto": "Houve uso de força, agressão ou tratamento inadequado?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "revista_mandado",
                "texto": "Foi realizada revista? Havia mandado de busca e apreensão?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "objetos_apreendidos",
                "texto": "Quais objetos foram apreendidos? Houve auto de apreensão?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "testemunhas_prisao",
                "texto": "Havia testemunhas da prisão? Informe nome e contato",
                "tipo": "TEXTO_LONGO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "tempo_ate_delegacia",
                "texto": "Quanto tempo levou entre a abordagem e a delegacia?",
                "tipo": "TEXTO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "exame_corpo_delito",
                "texto": "Foi submetido(a) a exame de corpo de delito?",
                "tipo": "SIM_NAO",
                "etapa": "Prisão em flagrante",
                "ordem_etapa": 2,
                "icone": "🚔",
            },
            {
                "codigo": "fato_imputado",
                "texto": "O que está sendo atribuído ao cliente?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato imputado",
                "ordem_etapa": 3,
                "icone": "⚠️",
                "obrigatoria": True,
            },
            {
                "codigo": "versao_cliente",
                "texto": "Qual é a versão do cliente sobre os fatos?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato imputado",
                "ordem_etapa": 3,
                "icone": "⚠️",
                "obrigatoria": True,
            },
            {
                "codigo": "alibi",
                "texto": "Onde estava e o que fazia no dia e horário dos fatos?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato imputado",
                "ordem_etapa": 3,
                "icone": "⚠️",
            },
            {
                "codigo": "outras_pessoas_envolvidas",
                "texto": "Havia outras pessoas envolvidas ou presentes?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato imputado",
                "ordem_etapa": 3,
                "icone": "⚠️",
            },
            {
                "codigo": "cameras_gravacoes",
                "texto": "Existem câmeras, gravações ou testemunhas que confirmem a versão?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Fato imputado",
                "ordem_etapa": 3,
                "icone": "⚠️",
            },
            {
                "codigo": "ouvido_policia",
                "texto": "Já foi ouvido(a) pela polícia?",
                "tipo": "SIM_NAO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "acompanhamento_advogado_depoimento",
                "texto": "Prestou depoimento com acompanhamento de advogado?",
                "tipo": "SIM_NAO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "citacao_intimacao",
                "texto": "Já foi citado(a) ou intimado(a) para algum ato?",
                "tipo": "SIM_NAO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "numero_processo_criminal",
                "texto": "Número do processo, se conhecido",
                "tipo": "TEXTO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "vara_criminal",
                "texto": "Vara ou juízo, se conhecido",
                "tipo": "TEXTO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "advogado_anterior",
                "texto": "Já teve outro advogado atuando no caso? Explique",
                "tipo": "TEXTO_LONGO",
                "etapa": "Inquérito e processo",
                "ordem_etapa": 4,
                "icone": "⚖️",
            },
            {
                "codigo": "antecedentes_criminais",
                "texto": "Já respondeu a outro processo criminal ou foi condenado(a)?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Antecedentes e vida pregressa",
                "ordem_etapa": 5,
                "icone": "📚",
            },
            {
                "codigo": "cumprindo_medida",
                "texto": "Está cumprindo pena, livramento ou suspensão condicional?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Antecedentes e vida pregressa",
                "ordem_etapa": 5,
                "icone": "📚",
            },
            {
                "codigo": "trabalho_residencia_vinculos",
                "texto": "Possui trabalho, residência fixa e vínculos familiares comprováveis?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Antecedentes e vida pregressa",
                "ordem_etapa": 5,
                "icone": "📚",
            },
            {
                "codigo": "testemunhas_defesa",
                "texto": "Há testemunhas que possam depor a favor? Informe contatos",
                "tipo": "TEXTO_LONGO",
                "etapa": "Provas e testemunhas",
                "ordem_etapa": 6,
                "icone": "📎",
            },
            {
                "codigo": "provas_defesa",
                "texto": "Existem documentos, mensagens, fotos ou vídeos favoráveis?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Provas e testemunhas",
                "ordem_etapa": 6,
                "icone": "📎",
            },
            {
                "codigo": "com_quem_reside",
                "texto": "Com quem reside e há quanto tempo mora no endereço?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação pessoal e familiar",
                "ordem_etapa": 7,
                "icone": "🏠",
            },
            {
                "codigo": "trabalho_renda",
                "texto": "Possui trabalho ou renda? Como pode comprovar?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação pessoal e familiar",
                "ordem_etapa": 7,
                "icone": "🏠",
            },
            {
                "codigo": "filhos_dependentes",
                "texto": "Possui filhos ou dependentes sob responsabilidade direta?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação pessoal e familiar",
                "ordem_etapa": 7,
                "icone": "🏠",
            },
            {
                "codigo": "condicao_saude",
                "texto": "Possui condição de saúde física ou mental relevante?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Situação pessoal e familiar",
                "ordem_etapa": 7,
                "icone": "🏠",
            },
            {
                "codigo": "condicao_honorarios",
                "texto": "Tem condições de arcar com honorários ou necessita de gratuidade?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas e providências",
                "ordem_etapa": 8,
                "icone": "🎯",
            },
            {
                "codigo": "urgencia_criminal",
                "texto": "Há audiência marcada, prazo em curso ou outra urgência?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas e providências",
                "ordem_etapa": 8,
                "icone": "🎯",
            },
            {
                "codigo": "duvidas_proximos_passos",
                "texto": "Restou alguma dúvida sobre os próximos passos?",
                "tipo": "TEXTO_LONGO",
                "etapa": "Expectativas e providências",
                "ordem_etapa": 8,
                "icone": "🎯",
            },
        ],
    },
}


def obter_ou_criar_area(slug, dados):
    area = AreaJuridica.query.filter_by(
        slug=slug
    ).first()

    if not area:
        area = AreaJuridica(
            slug=slug,
            nome=dados["nome"],
        )
        db.session.add(area)

    area.nome = dados["nome"]
    area.icone = dados.get("icone")
    area.cor = dados.get("cor")
    area.ordem = dados.get("ordem", 0)
    area.ativa = True

    return area


def obter_ou_criar_formulario(area, dados):
    formulario = FormularioModelo.query.filter_by(
        codigo=dados["codigo"]
    ).first()

    if not formulario:
        formulario = FormularioModelo(
            codigo=dados["codigo"],
        )
        db.session.add(formulario)

    formulario.nome = dados["nome"]
    formulario.descricao = dados.get("descricao")
    formulario.versao = 1
    formulario.ativo = True
    formulario.area_juridica = area

    return formulario


def atualizar_perguntas(formulario, perguntas):
    existentes = {
        pergunta.codigo: pergunta
        for pergunta in formulario.perguntas
    }

    codigos_atuais = set()

    for indice, dados in enumerate(
        perguntas,
        start=1,
    ):
        codigo = dados["codigo"]
        codigos_atuais.add(codigo)

        pergunta = existentes.get(codigo)

        if not pergunta:
            pergunta = PerguntaFormulario(
                codigo=codigo,
                formulario_modelo=formulario,
            )
            db.session.add(pergunta)

        pergunta.texto = dados["texto"]
        pergunta.descricao = dados.get("descricao")
        pergunta.tipo = dados.get("tipo", "TEXTO")
        pergunta.ordem = indice
        pergunta.etapa = dados.get("etapa", "Geral")
        pergunta.ordem_etapa = dados.get(
            "ordem_etapa",
            1,
        )
        pergunta.grupo = dados.get("grupo")
        pergunta.icone = dados.get("icone", "📄")
        pergunta.descricao_etapa = dados.get(
            "descricao_etapa"
        )
        pergunta.obrigatoria = dados.get(
            "obrigatoria",
            False,
        )
        pergunta.ativo = True
        pergunta.placeholder = dados.get(
            "placeholder"
        )
        pergunta.valor_padrao = dados.get(
            "valor_padrao"
        )
        pergunta.opcoes = dados.get("opcoes", [])

    # Perguntas antigas que não pertencem mais ao roteiro
    # são apenas desativadas, nunca excluídas.
    for codigo, pergunta in existentes.items():
        if codigo not in codigos_atuais:
            pergunta.ativo = False


def executar():
    app = create_app()

    with app.app_context():
        formularios_processados = []

        try:
            for slug, dados_area in AREAS.items():
                area = obter_ou_criar_area(
                    slug,
                    dados_area,
                )

                dados_formulario = FORMULARIOS[slug]

                formulario = obter_ou_criar_formulario(
                    area,
                    dados_formulario,
                )

                db.session.flush()

                atualizar_perguntas(
                    formulario,
                    dados_formulario["perguntas"],
                )

                formularios_processados.append(
                    (
                        formulario.nome,
                        len(
                            dados_formulario[
                                "perguntas"
                            ]
                        ),
                    )
                )

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        print("")
        print("=" * 65)
        print("ENTREVISTAS CRIADAS/ATUALIZADAS COM SUCESSO")
        print("=" * 65)

        for nome, quantidade in formularios_processados:
            print(
                f"- {nome}: "
                f"{quantidade} pergunta(s)"
            )

        print("=" * 65)
        print(
            "Agora abra o sistema e confira o menu "
            "Formulários."
        )
        print("")


if __name__ == "__main__":
    executar()