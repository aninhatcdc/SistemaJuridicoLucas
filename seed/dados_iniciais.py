from models import db
from models.area_juridica import AreaJuridica
from models.status_caso import StatusCaso
from seed.formulario_trabalhista import criar_formulario_trabalhista

AREAS_JURIDICAS = [
    {
        "nome": "Cível",
        "slug": "civel",
        "descricao": "Demandas de natureza cível em geral.",
        "icone": "⚖",
        "cor": "#355C8A",
        "ordem": 1,
    },
    {
        "nome": "Família",
        "slug": "familia",
        "descricao": "Divórcio, guarda, alimentos, inventário e sucessões.",
        "icone": "⌂",
        "cor": "#8B5E83",
        "ordem": 2,
    },
    {
        "nome": "Trabalhista",
        "slug": "trabalhista",
        "descricao": "Reclamações e consultoria trabalhista.",
        "icone": "▤",
        "cor": "#9D6B3D",
        "ordem": 3,
    },
    {
        "nome": "Previdenciário",
        "slug": "previdenciario",
        "descricao": "Benefícios, aposentadorias e revisões previdenciárias.",
        "icone": "◷",
        "cor": "#477A64",
        "ordem": 4,
    },
    {
        "nome": "Consumidor",
        "slug": "consumidor",
        "descricao": "Relações de consumo e responsabilidade de fornecedores.",
        "icone": "◇",
        "cor": "#4D6A91",
        "ordem": 5,
    },
    {
        "nome": "Criminal",
        "slug": "criminal",
        "descricao": "Defesa e acompanhamento de demandas criminais.",
        "icone": "⚑",
        "cor": "#7B3F3F",
        "ordem": 6,
    },
]


STATUS_CASOS = [
    {
        "nome": "Novo",
        "slug": "novo",
        "descricao": "Caso recém-cadastrado.",
        "cor": "#6C757D",
        "ordem": 1,
        "encerrado": False,
    },
    {
        "nome": "Triagem",
        "slug": "triagem",
        "descricao": "Caso em análise inicial.",
        "cor": "#C08A32",
        "ordem": 2,
        "encerrado": False,
    },
    {
        "nome": "Aguardando documentos",
        "slug": "aguardando-documentos",
        "descricao": "Pendência de documentos do cliente.",
        "cor": "#A56A2A",
        "ordem": 3,
        "encerrado": False,
    },
    {
        "nome": "Em andamento",
        "slug": "em-andamento",
        "descricao": "Caso em desenvolvimento.",
        "cor": "#2868A8",
        "ordem": 4,
        "encerrado": False,
    },
    {
        "nome": "Aguardando cliente",
        "slug": "aguardando-cliente",
        "descricao": "Caso parado por dependência do cliente.",
        "cor": "#8B6F3D",
        "ordem": 5,
        "encerrado": False,
    },
    {
        "nome": "Judicializado",
        "slug": "judicializado",
        "descricao": "Caso com processo judicial relacionado.",
        "cor": "#634B8A",
        "ordem": 6,
        "encerrado": False,
    },
    {
        "nome": "Finalizado",
        "slug": "finalizado",
        "descricao": "Caso concluído.",
        "cor": "#2F7D4A",
        "ordem": 7,
        "encerrado": True,
    },
    {
        "nome": "Arquivado",
        "slug": "arquivado",
        "descricao": "Caso arquivado pelo escritório.",
        "cor": "#495057",
        "ordem": 8,
        "encerrado": True,
    },
]


def criar_dados_iniciais():
    criar_areas_juridicas()
    criar_status_casos()
    criar_formulario_trabalhista()


def criar_areas_juridicas():
    for dados in AREAS_JURIDICAS:
        area = AreaJuridica.query.filter_by(
            slug=dados["slug"]
        ).first()

        if area:
            continue

        db.session.add(
            AreaJuridica(
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                icone=dados["icone"],
                cor=dados["cor"],
                ordem=dados["ordem"],
                ativa=True,
            )
        )

    db.session.commit()


def criar_status_casos():
    for dados in STATUS_CASOS:
        status = StatusCaso.query.filter_by(
            slug=dados["slug"]
        ).first()

        if status:
            continue

        db.session.add(
            StatusCaso(
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                cor=dados["cor"],
                ordem=dados["ordem"],
                encerrado=dados["encerrado"],
                ativo=True,
            )
        )

    db.session.commit()