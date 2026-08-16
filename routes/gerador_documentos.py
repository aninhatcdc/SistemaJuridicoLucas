import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models import db
from models.caso import Caso
from models.documento_caso import DocumentoCaso
from models.evento_caso import EventoCaso
from models.formulario_caso import FormularioCaso
from models.formulario_modelo import FormularioModelo
from models.modelo_documento import ModeloDocumento
from models.processo import Processo

from routes.documentos_caso import (
    obter_pasta_caso,
    obter_pasta_upload,
)

from services.contexto_documento import montar_contexto_documento
from services.conversor_pdf import (
    ErroConversaoPDF,
    converter_docx_para_pdf,
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
from services.storage import ErroStorage
from services.storage_service import (
    baixar_temporariamente,
)


gerador_documentos_bp = Blueprint(
    "gerador_documentos",
    __name__,
    url_prefix="/gerador-documentos",
)


def obter_caminho_modelo(
    modelo: ModeloDocumento,
) -> Path:
    """
    Obtém uma cópia temporária do modelo DOCX.

    Funciona com arquivos armazenados localmente e com
    referências do Cloudflare R2.
    """
    return baixar_temporariamente(
        modelo.caminho_arquivo,
        sufixo=".docx",
    )


def remover_arquivo_temporario(
    caminho,
):
    if not caminho:
        return

    try:
        Path(caminho).unlink(
            missing_ok=True
        )

    except OSError:
        current_app.logger.warning(
            "Não foi possível remover o arquivo temporário %s.",
            caminho,
        )


def modelo_exige_processo(modelo: ModeloDocumento) -> bool:
    return any(
        str(variavel).strip().lower().startswith("processo.")
        for variavel in modelo.variaveis
    )


def criar_nome_documento(modelo: ModeloDocumento, caso: Caso) -> str:
    nome_modelo = (modelo.nome or "Documento").strip()
    nome_cliente = ""

    if caso.cliente:
        nome_cliente = (caso.cliente.nome or "").strip()

    partes = [nome_modelo]

    if nome_cliente:
        partes.append(nome_cliente)

    if caso.numero_interno:
        partes.append(caso.numero_interno)

    nome_seguro = secure_filename(" - ".join(partes))
    return f"{nome_seguro or 'documento_gerado'}.docx"


def voltar_para_caso(caso_id):
    return redirect(
        url_for(
            "casos.detalhes",
            caso_id=caso_id,
            _anchor="documentos",
        )
    )


def obter_modelo_e_processo(caso, modelo_id, processo_id):
    """Valida a seleção e retorna (modelo, processo, resposta_de_erro)."""
    if not modelo_id:
        flash("Selecione um modelo de documento.", "danger")
        return None, None, voltar_para_caso(caso.id)

    modelo = db.session.get(ModeloDocumento, modelo_id)

    if not modelo:
        flash("O modelo selecionado não foi encontrado.", "danger")
        return None, None, voltar_para_caso(caso.id)

    if not modelo.ativo:
        flash("O modelo selecionado está inativo.", "danger")
        return None, None, voltar_para_caso(caso.id)

    if not modelo.eh_docx:
        flash("Somente modelos DOCX podem ser gerados.", "danger")
        return None, None, voltar_para_caso(caso.id)

    processo = None

    if processo_id:
        processo = db.session.get(Processo, processo_id)

        if not processo:
            flash("O processo selecionado não foi encontrado.", "danger")
            return None, None, voltar_para_caso(caso.id)

        if processo.caso_id != caso.id:
            flash(
                "O processo selecionado não pertence a este caso.",
                "danger",
            )
            return None, None, voltar_para_caso(caso.id)

    if modelo_exige_processo(modelo) and not processo:
        flash(
            "Este modelo utiliza informações de processo. "
            "Selecione um processo antes de continuar.",
            "warning",
        )
        return None, None, voltar_para_caso(caso.id)

    return modelo, processo, None


def montar_campos_assistente(
    modelo,
    contexto,
    valores_informados=None,
):
    """
    Usa o resolvedor inteligente para separar variáveis preenchidas
    automaticamente das que ainda exigem digitação.
    """
    contexto_final = montar_contexto_final(
        contexto_automatico=contexto,
        valores_manuais=valores_informados,
    )

    resumo = montar_resumo_resolucao(
        variaveis=modelo.variaveis,
        contexto=contexto_final,
    )

    def preparar_item(item):
        return {
            **item,
            "automatica": item["origem"] == "automatica",
        }

    preenchidas = [
        preparar_item(item)
        for item in resumo["preenchidas"]
    ]

    faltantes = [
        preparar_item(item)
        for item in resumo["faltantes"]
    ]

    return preenchidas, faltantes


def extrair_valores_extras(formulario, modelo):
    """Lê apenas valores pertencentes às variáveis do modelo selecionado."""
    permitidas = {
        str(codigo).strip()
        for codigo in modelo.variaveis
        if str(codigo).strip()
    }
    valores = {}

    for chave, codigo in formulario.items():
        if not chave.startswith("codigo__"):
            continue

        indice = chave.removeprefix("codigo__")
        codigo = str(codigo).strip()

        if codigo not in permitidas:
            continue

        valores[codigo] = formulario.get(f"valor__{indice}", "").strip()

    return valores


def normalizar_texto_busca(valor):
    import unicodedata

    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )


def obter_slug_area_caso(caso):
    if not caso.area_juridica:
        return ""

    slug = normalizar_texto_busca(
        getattr(caso.area_juridica, "slug", None)
        or getattr(caso.area_juridica, "nome", None)
    )

    return slug.replace(" ", "_").replace("-", "_")


def obter_codigo_entrevista(caso):
    slug = obter_slug_area_caso(caso)

    codigos_especiais = {
        "trabalhista": "entrevista_trabalhista",
        "previdenciario": "entrevista_previdenciaria",
        "civel": "entrevista_civel",
        "consumidor": "entrevista_consumidor",
        "criminal": "entrevista_criminal",
        "familia": "entrevista_familia",
    }

    return codigos_especiais.get(
        slug,
        f"entrevista_{slug}" if slug else "",
    )


def obter_entrevista_area(caso):
    """
    Retorna a entrevista mais recente correspondente à área do caso.

    Dá preferência a uma ficha concluída. Se ainda não existir,
    utiliza o rascunho mais recente. Fichas canceladas são ignoradas.
    """
    codigo_entrevista = obter_codigo_entrevista(caso)

    if not codigo_entrevista:
        return None

    consulta = (
        FormularioCaso.query
        .join(
            FormularioModelo,
            FormularioCaso.formulario_modelo_id
            == FormularioModelo.id,
        )
        .filter(
            FormularioCaso.caso_id == caso.id,
            FormularioCaso.status != "CANCELADO",
            FormularioModelo.codigo == codigo_entrevista,
        )
        .order_by(
            db.case(
                (FormularioCaso.status == "CONCLUIDO", 0),
                else_=1,
            ),
            FormularioCaso.atualizado_em.desc(),
            FormularioCaso.criado_em.desc(),
        )
    )

    return consulta.first()


def montar_contexto(caso, processo, valores_extras=None):
    formulario_caso = obter_entrevista_area(caso)

    return montar_contexto_documento(
        cliente=caso.cliente,
        caso=caso,
        processo=processo,
        usuario=current_user,
        escritorio=None,
        formulario_caso=formulario_caso,
        valores_extras=valores_extras,
    )


@gerador_documentos_bp.route(
    "/caso/<string:caso_id>/preparar",
    methods=["POST"],
)
@login_required
def preparar(caso_id):
    caso = db.get_or_404(Caso, caso_id)
    modelo_id = request.form.get("modelo_id", "").strip()
    processo_id = request.form.get("processo_id", "").strip()

    modelo, processo, resposta_erro = obter_modelo_e_processo(
        caso,
        modelo_id,
        processo_id,
    )

    if resposta_erro:
        return resposta_erro

    contexto = montar_contexto(caso, processo)
    preenchidas, faltantes = montar_campos_assistente(modelo, contexto)

    return render_template(
        "gerador_documentos/preparar.html",
        caso=caso,
        modelo=modelo,
        processo=processo,
        preenchidas=preenchidas,
        faltantes=faltantes,
    )


@gerador_documentos_bp.route(
    "/caso/<string:caso_id>/gerar",
    methods=["POST"],
)
@login_required
def gerar(caso_id):
    caso = db.get_or_404(Caso, caso_id)
    modelo_id = request.form.get("modelo_id", "").strip()
    processo_id = request.form.get("processo_id", "").strip()

    modelo, processo, resposta_erro = obter_modelo_e_processo(
        caso,
        modelo_id,
        processo_id,
    )

    if resposta_erro:
        return resposta_erro

    valores_extras = extrair_valores_extras(
        request.form,
        modelo,
    )

    contexto_automatico = montar_contexto(
        caso,
        processo,
    )

    contexto = montar_contexto_final(
        contexto_automatico=contexto_automatico,
        valores_manuais=valores_extras,
    )

    validacao = validar_preenchimento_final(
        variaveis=modelo.variaveis,
        contexto_final=contexto,
    )

    preenchidas, faltantes = montar_campos_assistente(
        modelo,
        contexto_automatico,
        valores_extras,
    )

    if not validacao["valido"]:
        flash(
            validacao["mensagem"],
            "warning",
        )

        return render_template(
            "gerador_documentos/preparar.html",
            caso=caso,
            modelo=modelo,
            processo=processo,
            preenchidas=preenchidas,
            faltantes=faltantes,
        )

    caminho_modelo = None
    pasta_upload = obter_pasta_upload().resolve()

    try:
        caminho_modelo = obter_caminho_modelo(
            modelo
        )

    except ErroStorage as erro:
        current_app.logger.exception(
            "Não foi possível obter o modelo %s do armazenamento.",
            modelo.id,
        )

        flash(
            str(erro),
            "danger",
        )

        return voltar_para_caso(
            caso.id
        )

    if not caminho_modelo.is_file():
        remover_arquivo_temporario(
            caminho_modelo
        )

        flash(
            "O arquivo físico do modelo não foi encontrado.",
            "danger",
        )

        return voltar_para_caso(
            caso.id
        )

    pasta_caso = obter_pasta_caso(caso)
    nome_original = criar_nome_documento(modelo, caso)
    nome_arquivo = f"{uuid.uuid4().hex}.docx"
    caminho_saida = pasta_caso / nome_arquivo

    nome_original_pdf = f"{Path(nome_original).stem}.pdf"
    nome_arquivo_pdf = f"{uuid.uuid4().hex}.pdf"
    caminho_saida_pdf = pasta_caso / nome_arquivo_pdf

    try:
        resultado = renderizar_documento_docx(
            caminho_modelo=caminho_modelo,
            caminho_saida=caminho_saida,
            contexto=contexto,
            manter_nao_encontradas=True,
        )

        if not caminho_saida.is_file():
            raise ErroRenderizacaoDocumento(
                "O documento não foi criado no servidor."
            )

        caminho_relativo = caminho_saida.resolve().relative_to(pasta_upload)
        observacoes = (
            "Documento gerado automaticamente a partir do modelo "
            f"“{modelo.nome}”, versão {modelo.versao}."
        )

        if processo:
            numero_processo = (
                getattr(processo, "numero_cnj", None)
                or getattr(processo, "numero", None)
            )
            if numero_processo:
                observacoes += f" Processo utilizado: {numero_processo}."

        documento = DocumentoCaso(
            nome_original=nome_original,
            nome_arquivo=nome_arquivo,
            caminho_arquivo=str(caminho_relativo),
            tipo_documento=(
                modelo.tipo_documento
                or modelo.categoria
                or "Documento gerado"
            ),
            extensao="docx",
            tamanho_bytes=caminho_saida.stat().st_size,
            observacoes=observacoes,
            caso_id=caso.id,
            usuario_id=current_user.id,
        )
        db.session.add(documento)

        erro_conversao_pdf = None
        pdf_gerado = False
        documento_pdf = None

        try:
            converter_docx_para_pdf(
                caminho_docx=caminho_saida,
                caminho_pdf=caminho_saida_pdf,
            )

            caminho_relativo_pdf = (
                caminho_saida_pdf.resolve().relative_to(pasta_upload)
            )

            documento_pdf = DocumentoCaso(
                nome_original=nome_original_pdf,
                nome_arquivo=nome_arquivo_pdf,
                caminho_arquivo=str(caminho_relativo_pdf),
                tipo_documento=(
                    modelo.tipo_documento
                    or modelo.categoria
                    or "Documento gerado"
                ),
                extensao="pdf",
                tamanho_bytes=caminho_saida_pdf.stat().st_size,
                observacoes=(
                    "PDF gerado automaticamente a partir do documento "
                    f"“{nome_original}”. Modelo utilizado: “{modelo.nome}”, "
                    f"versão {modelo.versao}."
                ),
                caso_id=caso.id,
                usuario_id=current_user.id,
            )
            db.session.add(documento_pdf)
            pdf_gerado = True

        except ErroConversaoPDF as erro:
            erro_conversao_pdf = str(erro)
            current_app.logger.warning(
                "DOCX do caso %s foi gerado, mas a conversão para PDF falhou: %s",
                caso.id,
                erro_conversao_pdf,
            )

        evento = EventoCaso(
            tipo=EventoCaso.TIPO_DOCUMENTO_GERADO,
            titulo=f"Documento gerado: {nome_original}",
            descricao=(
                f"Modelo “{modelo.nome}”, versão {modelo.versao}. "
                + ("Arquivos DOCX e PDF salvos." if pdf_gerado else "Arquivo DOCX salvo.")
            ),
            icone="📄",
            cor="success",
            url=url_for(
                "casos.detalhes",
                caso_id=caso.id,
                _anchor="documentos",
            ),
            caso_id=caso.id,
            usuario_id=current_user.id,
        )
        evento.dados = {
            "modelo_id": modelo.id,
            "modelo_nome": modelo.nome,
            "modelo_versao": modelo.versao,
            "documento_docx": nome_original,
            "documento_pdf": nome_original_pdf if pdf_gerado else None,
            "processo_id": processo.id if processo else None,
            "variaveis_manuais": sorted(valores_extras.keys()),
        }
        db.session.add(evento)
        db.session.commit()

        quantidade_faltantes = resultado.get(
            "quantidade_nao_encontradas",
            0,
        )
        variaveis_faltantes = resultado.get(
            "variaveis_nao_encontradas",
            [],
        )
        avisos = []

        if quantidade_faltantes:
            avisos.append(
                "algumas variáveis não foram preenchidas: "
                + ", ".join(variaveis_faltantes)
            )

        if erro_conversao_pdf:
            avisos.append(
                "o DOCX foi salvo, mas o PDF não pôde ser criado: "
                + erro_conversao_pdf
            )

        if avisos:
            flash(
                "Documento gerado e salvo, porém "
                + "; ".join(avisos)
                + ".",
                "warning",
            )
        elif pdf_gerado:
            flash(
                "Documento DOCX e PDF gerados e salvos com sucesso.",
                "success",
            )
        else:
            flash("Documento DOCX gerado e salvo com sucesso.", "success")

    except ErroRenderizacaoDocumento as erro:
        db.session.rollback()
        if caminho_saida.is_file():
            caminho_saida.unlink()
        if caminho_saida_pdf.is_file():
            caminho_saida_pdf.unlink()
        flash(str(erro), "danger")

    except ValueError:
        db.session.rollback()
        if caminho_saida.is_file():
            caminho_saida.unlink()
        if caminho_saida_pdf.is_file():
            caminho_saida_pdf.unlink()
        flash(
            "Não foi possível determinar a pasta do documento gerado.",
            "danger",
        )

    except ErroStorage as erro:
        db.session.rollback()

        if caminho_saida.is_file():
            caminho_saida.unlink()

        if caminho_saida_pdf.is_file():
            caminho_saida_pdf.unlink()

        current_app.logger.exception(
            "Erro de armazenamento ao gerar documento do caso %s.",
            caso.id,
        )

        flash(
            str(erro),
            "danger",
        )

    except Exception:
        db.session.rollback()

        if caminho_saida.is_file():
            caminho_saida.unlink()

        if caminho_saida_pdf.is_file():
            caminho_saida_pdf.unlink()

        current_app.logger.exception(
            "Erro ao gerar documento do caso %s.",
            caso.id,
        )

        flash(
            "Não foi possível gerar o documento. "
            "Consulte o terminal para verificar o erro.",
            "danger",
        )

    finally:
        remover_arquivo_temporario(
            caminho_modelo
        )

    return voltar_para_caso(caso.id)

# ================================================================
# KIT GENÉRICO POR ÁREA JURÍDICA
# ================================================================

AREAS_GERAIS_MODELO = {
    "geral",
    "gerais",
    "todas",
    "todas_as_areas",
    "institucional",
    "institucionais",
}


def obter_nome_area_caso(caso):
    if not caso.area_juridica:
        return "Jurídico"

    return (
        getattr(caso.area_juridica, "nome", None)
        or "Jurídico"
    ).strip()


def modelo_compativel_com_area(modelo, caso):
    area_modelo = normalizar_texto_busca(
        modelo.area_juridica
    ).replace(" ", "_").replace("-", "_")

    area_caso_nome = normalizar_texto_busca(
        getattr(caso.area_juridica, "nome", None)
    ).replace(" ", "_").replace("-", "_")

    area_caso_slug = obter_slug_area_caso(caso)

    if not area_modelo:
        return False

    if area_modelo in AREAS_GERAIS_MODELO:
        return True

    return area_modelo in {
        area_caso_nome,
        area_caso_slug,
    }


def obter_modelos_kit(caso):
    """
    Retorna todos os modelos DOCX ativos da área do caso,
    incluindo os modelos cadastrados como Geral.
    """
    modelos = (
        ModeloDocumento.query
        .filter(
            ModeloDocumento.ativo.is_(True),
        )
        .order_by(
            ModeloDocumento.categoria.asc(),
            ModeloDocumento.tipo_documento.asc(),
            ModeloDocumento.nome.asc(),
        )
        .all()
    )

    return [
        modelo
        for modelo in modelos
        if (
            modelo.eh_docx
            and modelo_compativel_com_area(
                modelo,
                caso,
            )
        )
    ]


def obter_processo_padrao_kit(caso):
    return (
        Processo.query
        .filter_by(caso_id=caso.id)
        .order_by(Processo.criado_em.desc())
        .first()
    )


def listar_codigos_faltantes(validacao):
    """
    Converte a lista de variáveis faltantes em nomes legíveis.
    """
    codigos = []

    for item in validacao.get("faltantes", []) or []:
        if isinstance(item, dict):
            codigo = (
                item.get("codigo")
                or item.get("variavel")
                or item.get("nome")
                or item.get("campo")
            )
        else:
            codigo = str(item).strip()

        if codigo:
            codigos.append(str(codigo).strip())

    return codigos


def remover_arquivo_se_existir(caminho):
    try:
        if caminho and caminho.is_file():
            caminho.unlink()
    except OSError:
        current_app.logger.warning(
            "Não foi possível remover o arquivo temporário %s.",
            caminho,
        )


def criar_documento_caso_gerado(
    *,
    caso,
    modelo,
    nome_original,
    nome_arquivo,
    caminho_arquivo,
    extensao,
    tamanho_bytes,
    observacoes,
):
    return DocumentoCaso(
        nome_original=nome_original,
        nome_arquivo=nome_arquivo,
        caminho_arquivo=str(caminho_arquivo),
        tipo_documento=(
            modelo.tipo_documento
            or modelo.categoria
            or "Documento gerado"
        ),
        extensao=extensao,
        tamanho_bytes=tamanho_bytes,
        observacoes=observacoes,
        caso_id=caso.id,
        usuario_id=current_user.id,
    )


def gerar_item_kit(
    *,
    caso,
    modelo,
    processo,
    contexto,
    nome_area,
    slug_area,
):
    caminho_modelo = obter_caminho_modelo(
        modelo
    )

    pasta_upload = obter_pasta_upload().resolve()

    if not caminho_modelo.is_file():
        remover_arquivo_temporario(
            caminho_modelo
        )

        raise FileNotFoundError(
            "O arquivo físico do modelo não foi encontrado."
        )

    if modelo_exige_processo(modelo) and not processo:
        raise ValueError(
            "O modelo exige dados de processo, mas este caso "
            "não possui processo cadastrado."
        )

    validacao = validar_preenchimento_final(
        variaveis=modelo.variaveis,
        contexto_final=contexto,
    )

    if not validacao["valido"]:
        codigos_faltantes = listar_codigos_faltantes(
            validacao
        )

        mensagem = validacao.get(
            "mensagem",
            "Existem variáveis obrigatórias sem valor.",
        )

        if codigos_faltantes:
            mensagem += (
                " Variáveis: "
                + ", ".join(codigos_faltantes)
                + "."
            )

        raise ValueError(mensagem)

    pasta_caso = obter_pasta_caso(caso)
    nome_original = criar_nome_documento(modelo, caso)
    nome_arquivo = f"{uuid.uuid4().hex}.docx"
    caminho_saida = pasta_caso / nome_arquivo

    nome_original_pdf = f"{Path(nome_original).stem}.pdf"
    nome_arquivo_pdf = f"{uuid.uuid4().hex}.pdf"
    caminho_saida_pdf = pasta_caso / nome_arquivo_pdf

    try:
        resultado = renderizar_documento_docx(
            caminho_modelo=caminho_modelo,
            caminho_saida=caminho_saida,
            contexto=contexto,
            manter_nao_encontradas=True,
        )

        if not caminho_saida.is_file():
            raise ErroRenderizacaoDocumento(
                "O documento não foi criado no servidor."
            )

        caminho_relativo = (
            caminho_saida
            .resolve()
            .relative_to(pasta_upload)
        )

        observacoes = (
            "Documento gerado automaticamente pelo Kit "
            f"{nome_area} a partir do modelo “{modelo.nome}”, "
            f"versão {modelo.versao}."
        )

        documento = criar_documento_caso_gerado(
            caso=caso,
            modelo=modelo,
            nome_original=nome_original,
            nome_arquivo=nome_arquivo,
            caminho_arquivo=caminho_relativo,
            extensao="docx",
            tamanho_bytes=caminho_saida.stat().st_size,
            observacoes=observacoes,
        )

        db.session.add(documento)

        pdf_gerado = False
        erro_pdf = None

        try:
            converter_docx_para_pdf(
                caminho_docx=caminho_saida,
                caminho_pdf=caminho_saida_pdf,
            )

            caminho_relativo_pdf = (
                caminho_saida_pdf
                .resolve()
                .relative_to(pasta_upload)
            )

            documento_pdf = criar_documento_caso_gerado(
                caso=caso,
                modelo=modelo,
                nome_original=nome_original_pdf,
                nome_arquivo=nome_arquivo_pdf,
                caminho_arquivo=caminho_relativo_pdf,
                extensao="pdf",
                tamanho_bytes=caminho_saida_pdf.stat().st_size,
                observacoes=(
                    "PDF gerado automaticamente pelo Kit "
                    f"{nome_area} a partir de “{nome_original}”."
                ),
            )

            db.session.add(documento_pdf)
            pdf_gerado = True

        except ErroConversaoPDF as erro:
            erro_pdf = str(erro)
            remover_arquivo_se_existir(caminho_saida_pdf)

            current_app.logger.warning(
                "O DOCX do modelo %s foi gerado, mas o PDF falhou: %s",
                modelo.id,
                erro_pdf,
            )

        evento = EventoCaso(
            tipo=EventoCaso.TIPO_DOCUMENTO_GERADO,
            titulo=f"Documento gerado: {nome_original}",
            descricao=(
                f"Gerado pelo Kit {nome_area} com o modelo "
                f"“{modelo.nome}”, versão {modelo.versao}. "
                + (
                    "Arquivos DOCX e PDF salvos."
                    if pdf_gerado
                    else "Arquivo DOCX salvo."
                )
            ),
            icone="📄",
            cor="success",
            url=url_for(
                "casos.detalhes",
                caso_id=caso.id,
                _anchor="documentos",
            ),
            caso_id=caso.id,
            usuario_id=current_user.id,
        )

        evento.dados = {
            "kit": slug_area,
            "area": nome_area,
            "modelo_id": modelo.id,
            "modelo_nome": modelo.nome,
            "documento_docx": nome_original,
            "documento_pdf": (
                nome_original_pdf
                if pdf_gerado
                else None
            ),
            "processo_id": (
                processo.id
                if processo
                else None
            ),
        }

        db.session.add(evento)
        db.session.commit()

        remover_arquivo_temporario(
            caminho_modelo
        )

        return {
            "modelo": modelo.nome,
            "docx": nome_original,
            "pdf_gerado": pdf_gerado,
            "erro_pdf": erro_pdf,
            "variaveis_nao_encontradas": resultado.get(
                "variaveis_nao_encontradas",
                [],
            ),
        }

    except Exception:
        db.session.rollback()
        remover_arquivo_se_existir(
            caminho_saida
        )
        remover_arquivo_se_existir(
            caminho_saida_pdf
        )
        raise

    finally:
        remover_arquivo_temporario(
            caminho_modelo
        )


@gerador_documentos_bp.route(
    "/caso/<string:caso_id>/gerar-kit",
    methods=["POST"],
)
@login_required
def gerar_kit(caso_id):
    caso = db.get_or_404(Caso, caso_id)

    if not caso.area_juridica:
        flash(
            "Defina a área jurídica do caso antes de gerar o kit.",
            "warning",
        )
        return voltar_para_caso(caso.id)

    nome_area = obter_nome_area_caso(caso)
    slug_area = obter_slug_area_caso(caso)
    formulario = obter_entrevista_area(caso)
    modelos = obter_modelos_kit(caso)

    if not modelos:
        flash(
            f"Nenhum modelo ativo foi localizado para a área "
            f"{nome_area}. Cadastre os modelos com essa área ou "
            f"como Geral.",
            "warning",
        )
        return voltar_para_caso(caso.id)

    processo = obter_processo_padrao_kit(caso)

    contexto = montar_contexto_documento(
        cliente=caso.cliente,
        caso=caso,
        processo=processo,
        usuario=current_user,
        escritorio=None,
        formulario_caso=formulario,
    )

    gerados = []
    falhas = []
    avisos_pdf = []

    for modelo in modelos:
        try:
            resultado = gerar_item_kit(
                caso=caso,
                modelo=modelo,
                processo=processo,
                contexto=contexto,
                nome_area=nome_area,
                slug_area=slug_area,
            )

            gerados.append(resultado["modelo"])

            if resultado["erro_pdf"]:
                avisos_pdf.append(resultado["modelo"])

        except Exception as erro:
            current_app.logger.exception(
                "Erro ao gerar o modelo %s no Kit %s do caso %s.",
                modelo.id,
                nome_area,
                caso.id,
            )

            falhas.append(
                f"{modelo.nome}: {erro}"
            )

    if gerados and not falhas:
        mensagem = (
            f"Kit {nome_area} gerado com sucesso: "
            f"{len(gerados)} documento(s)."
        )

        if not formulario:
            mensagem += (
                " Nenhuma entrevista específica da área foi "
                "localizada; foram usados os dados disponíveis "
                "no cliente, caso e processo."
            )

        if avisos_pdf:
            mensagem += (
                " O DOCX foi salvo, mas o PDF não pôde ser "
                "criado para: "
                + ", ".join(avisos_pdf)
                + "."
            )
            categoria = "warning"
        else:
            categoria = "success"

        flash(mensagem, categoria)

    elif gerados:
        flash(
            f"{len(gerados)} documento(s) foram gerados, mas "
            f"{len(falhas)} modelo(s) apresentaram erro: "
            + " | ".join(falhas),
            "warning",
        )

    else:
        flash(
            "Nenhum documento do kit pôde ser gerado: "
            + " | ".join(falhas),
            "danger",
        )

    return voltar_para_caso(caso.id)


@gerador_documentos_bp.route(
    "/caso/<string:caso_id>/gerar-kit-trabalhista",
    methods=["POST"],
)
@login_required
def gerar_kit_trabalhista(caso_id):
    """
    Mantém compatibilidade com o botão antigo enquanto o template
    ainda não foi atualizado para o endpoint genérico.
    """
    return gerar_kit(caso_id)