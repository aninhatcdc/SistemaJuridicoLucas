from pathlib import Path

from services.contexto_documento import (
    montar_contexto_documento,
)

from services.renderizador_docx import (
    renderizar_documento_docx,
)


class ClienteTeste:
    nome = "Maria da Silva"
    cpf = "12345678901"
    rg = "1234567"
    profissao = "Professora"
    estado_civil = "Casada"
    telefone = "(83) 99999-9999"
    whatsapp = "(83) 99999-9999"
    email = "maria@email.com"
    rua = "Rua das Flores"
    numero = "100"
    complemento = "Apartamento 201"
    bairro = "Centro"
    cidade = "João Pessoa"
    estado = "PB"
    cep = "58000000"


class CasoTeste:
    numero_interno = "2026-001"
    titulo = "Benefício previdenciário"
    area = "Previdenciário"
    status = "Em andamento"
    descricao = "Pedido de concessão de benefício"


class ProcessoTeste:
    numero = "0800000-00.2026.8.15.0001"
    numero_cnj = "0800000-00.2026.8.15.0001"
    tribunal = "Tribunal de Justiça da Paraíba"
    comarca = "João Pessoa"
    vara = "1ª Vara Cível"
    fase = "Conhecimento"
    situacao = "Em andamento"
    advogado = "Dra. Flávia Ferreira"


class UsuarioTeste:
    nome = "Dra. Flávia Ferreira"
    email = "flavia@escritorio.com"
    telefone = "(83) 99999-0000"
    cargo = "Advogada"
    perfil = "ADMIN"


BASE_DIR = Path(__file__).resolve().parent

CAMINHO_MODELO = (
    BASE_DIR
    / "uploads"
    / "modelos_documentos"
    / "8c2d8fb1-fb9b-4ad1-9ce3-c668ff4eb4c9.docx"
)

CAMINHO_SAIDA = (
    BASE_DIR
    / "documento_gerado_teste.docx"
)


contexto = montar_contexto_documento(
    cliente=ClienteTeste(),
    caso=CasoTeste(),
    processo=ProcessoTeste(),
    usuario=UsuarioTeste(),
)


resultado = renderizar_documento_docx(
    caminho_modelo=CAMINHO_MODELO,
    caminho_saida=CAMINHO_SAIDA,
    contexto=contexto,
)


print()
print("DOCUMENTO GERADO COM SUCESSO")
print("--------------------------------")
print(f"Arquivo: {resultado['caminho']}")

if resultado["variaveis_nao_encontradas"]:
    print()
    print("Variáveis sem valor:")

    for variavel in resultado[
        "variaveis_nao_encontradas"
    ]:
        print(f"- {variavel}")
else:
    print()
    print("Todas as variáveis foram preenchidas.")