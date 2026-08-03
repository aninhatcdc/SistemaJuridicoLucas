from flask import url_for
from flask_login import current_user

from models import db
from models.evento_caso import EventoCaso


class TimelineService:
    @staticmethod
    def registrar_evento(
        caso,
        tipo,
        titulo,
        descricao=None,
        icone="📝",
        cor="secondary",
        usuario=None,
        url=None,
        dados=None,
        realizar_commit=False,
    ):
        if not caso:
            raise ValueError(
                "Um caso é obrigatório para registrar o evento."
            )

        if not tipo:
            raise ValueError(
                "O tipo do evento é obrigatório."
            )

        if not titulo:
            raise ValueError(
                "O título do evento é obrigatório."
            )

        usuario_evento = usuario

        if usuario_evento is None:
            try:
                if (
                    current_user
                    and current_user.is_authenticated
                ):
                    usuario_evento = current_user
            except RuntimeError:
                usuario_evento = None

        evento = EventoCaso(
            caso_id=caso.id,
            usuario_id=(
                usuario_evento.id
                if usuario_evento
                else None
            ),
            tipo=tipo,
            titulo=titulo.strip(),
            descricao=(
                descricao.strip()
                if isinstance(descricao, str)
                and descricao.strip()
                else None
            ),
            icone=icone or "📝",
            cor=cor or "secondary",
            url=url,
        )

        evento.dados = dados

        db.session.add(evento)

        if realizar_commit:
            db.session.commit()

        return evento

    @staticmethod
    def registrar_caso_criado(
        caso,
        usuario=None,
        realizar_commit=False,
    ):
        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=EventoCaso.TIPO_CASO_CRIADO,
            titulo="Caso criado",
            descricao=(
                f"O caso {caso.numero_interno} foi cadastrado."
            ),
            icone="⚖",
            cor="success",
            url=TimelineService._url_caso(caso),
            dados={
                "caso_id": caso.id,
                "numero_interno": caso.numero_interno,
                "titulo": caso.titulo,
                "cliente_id": caso.cliente_id,
                "area_juridica_id": caso.area_juridica_id,
                "status_id": caso.status_id,
                "prioridade": caso.prioridade,
                "responsavel_id": caso.responsavel_id,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_caso_editado(
        caso,
        alteracoes=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = "Os dados do caso foram atualizados."

        if alteracoes:
            descricao = TimelineService._montar_descricao_alteracoes(
                alteracoes
            )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=EventoCaso.TIPO_CASO_EDITADO,
            titulo="Caso atualizado",
            descricao=descricao,
            icone="✏️",
            cor="primary",
            url=TimelineService._url_caso(caso),
            dados={
                "caso_id": caso.id,
                "alteracoes": alteracoes or {},
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_status_alterado(
        caso,
        status_anterior,
        novo_status,
        usuario=None,
        realizar_commit=False,
    ):
        nome_anterior = (
            status_anterior.nome
            if status_anterior
            else "Sem status"
        )

        nome_novo = (
            novo_status.nome
            if novo_status
            else "Sem status"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=EventoCaso.TIPO_STATUS_ALTERADO,
            titulo="Status alterado",
            descricao=(
                f"{nome_anterior} → {nome_novo}"
            ),
            icone="🔄",
            cor="info",
            url=TimelineService._url_caso(caso),
            dados={
                "status_anterior_id": (
                    status_anterior.id
                    if status_anterior
                    else None
                ),
                "status_anterior_nome": nome_anterior,
                "novo_status_id": (
                    novo_status.id
                    if novo_status
                    else None
                ),
                "novo_status_nome": nome_novo,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_prioridade_alterada(
        caso,
        prioridade_anterior,
        nova_prioridade,
        usuario=None,
        realizar_commit=False,
    ):
        anterior_formatada = (
            TimelineService.formatar_prioridade(
                prioridade_anterior
            )
        )

        nova_formatada = (
            TimelineService.formatar_prioridade(
                nova_prioridade
            )
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=EventoCaso.TIPO_PRIORIDADE_ALTERADA,
            titulo="Prioridade alterada",
            descricao=(
                f"{anterior_formatada} → {nova_formatada}"
            ),
            icone="🚩",
            cor=TimelineService.cor_prioridade(
                nova_prioridade
            ),
            url=TimelineService._url_caso(caso),
            dados={
                "prioridade_anterior": prioridade_anterior,
                "nova_prioridade": nova_prioridade,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_responsavel_alterado(
        caso,
        responsavel_anterior,
        novo_responsavel,
        usuario=None,
        realizar_commit=False,
    ):
        nome_anterior = (
            responsavel_anterior.nome
            if responsavel_anterior
            else "Não definido"
        )

        nome_novo = (
            novo_responsavel.nome
            if novo_responsavel
            else "Não definido"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=EventoCaso.TIPO_RESPONSAVEL_ALTERADO,
            titulo="Responsável alterado",
            descricao=(
                f"{nome_anterior} → {nome_novo}"
            ),
            icone="👤",
            cor="warning",
            url=TimelineService._url_caso(caso),
            dados={
                "responsavel_anterior_id": (
                    responsavel_anterior.id
                    if responsavel_anterior
                    else None
                ),
                "responsavel_anterior_nome": nome_anterior,
                "novo_responsavel_id": (
                    novo_responsavel.id
                    if novo_responsavel
                    else None
                ),
                "novo_responsavel_nome": nome_novo,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_documento_enviado(
        caso,
        documento,
        usuario=None,
        realizar_commit=False,
    ):
        tipo_documento = (
            documento.tipo_documento
            or "Não informado"
        )

        descricao = (
            f"{documento.nome_original} "
            f"({tipo_documento})"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="DOCUMENTO_ENVIADO",
            titulo="Documento enviado",
            descricao=descricao,
            icone="📄",
            cor="success",
            url=TimelineService._url_documento(
                documento
            ),
            dados={
                "documento_id": documento.id,
                "nome_original": documento.nome_original,
                "nome_arquivo": documento.nome_arquivo,
                "tipo_documento": documento.tipo_documento,
                "extensao": documento.extensao,
                "tamanho_bytes": documento.tamanho_bytes,
                "observacoes": documento.observacoes,
                "caso_id": caso.id,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_documento_excluido(
        caso,
        documento,
        usuario=None,
        realizar_commit=False,
    ):
        tipo_documento = (
            documento.tipo_documento
            or "Não informado"
        )

        descricao = (
            f"{documento.nome_original} "
            f"({tipo_documento})"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="DOCUMENTO_EXCLUIDO",
            titulo="Documento excluído",
            descricao=descricao,
            icone="🗑️",
            cor="danger",
            url=TimelineService._url_caso(caso),
            dados={
                "documento_id": documento.id,
                "nome_original": documento.nome_original,
                "nome_arquivo": documento.nome_arquivo,
                "tipo_documento": documento.tipo_documento,
                "extensao": documento.extensao,
                "tamanho_bytes": documento.tamanho_bytes,
                "observacoes": documento.observacoes,
                "caso_id": caso.id,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_documento_gerado(
        caso,
        documento,
        modelo=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = documento.nome_original

        if modelo:
            descricao = (
                f"{documento.nome_original} — "
                f"modelo: {modelo.nome}"
            )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="DOCUMENTO_GERADO",
            titulo="Documento gerado pelo sistema",
            descricao=descricao,
            icone="✨",
            cor="primary",
            url=TimelineService._url_documento(
                documento
            ),
            dados={
                "documento_id": documento.id,
                "nome_original": documento.nome_original,
                "tipo_documento": documento.tipo_documento,
                "extensao": documento.extensao,
                "modelo_id": (
                    modelo.id
                    if modelo
                    else None
                ),
                "modelo_nome": (
                    modelo.nome
                    if modelo
                    else None
                ),
                "caso_id": caso.id,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_processo_criado(
        caso,
        processo,
        usuario=None,
        realizar_commit=False,
    ):
        identificacao = (
            processo.numero_cnj
            or processo.classe_processual
            or "Processo sem número"
        )

        descricao = identificacao

        if processo.tribunal:
            descricao = (
                f"{descricao} — {processo.tribunal}"
            )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PROCESSO_CRIADO",
            titulo="Processo cadastrado",
            descricao=descricao,
            icone="⚖",
            cor="success",
            url=TimelineService._url_caso_secao(
                caso,
                "processos",
            ),
            dados=TimelineService._dados_processo(
                processo
            ),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_processo_editado(
        caso,
        processo,
        alteracoes=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = "Os dados do processo foram atualizados."

        if alteracoes:
            descricao = TimelineService._montar_descricao_alteracoes(
                alteracoes
            )

        dados = TimelineService._dados_processo(
            processo
        )
        dados["alteracoes"] = alteracoes or {}

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PROCESSO_EDITADO",
            titulo="Processo atualizado",
            descricao=descricao,
            icone="✏️",
            cor="primary",
            url=TimelineService._url_caso_secao(
                caso,
                "processos",
            ),
            dados=dados,
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_situacao_processo_alterada(
        caso,
        processo,
        situacao_anterior,
        nova_situacao,
        usuario=None,
        realizar_commit=False,
    ):
        anterior = TimelineService.formatar_situacao_processo(
            situacao_anterior
        )
        nova = TimelineService.formatar_situacao_processo(
            nova_situacao
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="SITUACAO_PROCESSO_ALTERADA",
            titulo="Situação do processo alterada",
            descricao=f"{anterior} → {nova}",
            icone="🔄",
            cor=TimelineService.cor_situacao_processo(
                nova_situacao
            ),
            url=TimelineService._url_caso_secao(
                caso,
                "processos",
            ),
            dados={
                "processo_id": processo.id,
                "numero_cnj": processo.numero_cnj,
                "situacao_anterior": situacao_anterior,
                "nova_situacao": nova_situacao,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_processo_excluido(
        caso,
        processo,
        usuario=None,
        realizar_commit=False,
    ):
        identificacao = (
            processo.numero_cnj
            or processo.classe_processual
            or "Processo sem número"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PROCESSO_EXCLUIDO",
            titulo="Processo excluído",
            descricao=identificacao,
            icone="🗑️",
            cor="danger",
            url=TimelineService._url_caso_secao(
                caso,
                "processos",
            ),
            dados=TimelineService._dados_processo(
                processo
            ),
            realizar_commit=realizar_commit,
        )


    @staticmethod
    def registrar_honorario_criado(
        caso,
        honorario,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{honorario.descricao} — "
            f"{TimelineService._formatar_moeda(honorario.valor_total)}"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="HONORARIO_CRIADO",
            titulo="Contrato de honorários criado",
            descricao=descricao,
            icone="💰",
            cor="success",
            url=TimelineService._url_honorario(honorario),
            dados=TimelineService._dados_honorario(honorario),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_parcelamento_gerado(
        caso,
        honorario,
        usuario=None,
        realizar_commit=False,
    ):
        quantidade = honorario.quantidade_parcelas or 1
        valor_parcelado = (
            (honorario.valor_total or 0)
            - (honorario.valor_entrada or 0)
        )

        descricao = (
            f"{quantidade} parcela(s), total parcelado de "
            f"{TimelineService._formatar_moeda(valor_parcelado)}"
        )

        if honorario.primeiro_vencimento:
            descricao += (
                " — primeiro vencimento em "
                f"{honorario.primeiro_vencimento.strftime('%d/%m/%Y')}"
            )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PARCELAMENTO_GERADO",
            titulo="Parcelamento de honorários gerado",
            descricao=descricao,
            icone="💳",
            cor="info",
            url=TimelineService._url_honorario(honorario),
            dados={
                "honorario_id": honorario.id,
                "quantidade_parcelas": quantidade,
                "valor_total": str(honorario.valor_total or 0),
                "valor_entrada": str(honorario.valor_entrada or 0),
                "valor_parcelado": str(valor_parcelado),
                "primeiro_vencimento": (
                    honorario.primeiro_vencimento.isoformat()
                    if honorario.primeiro_vencimento
                    else None
                ),
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_honorario_editado(
        caso,
        honorario,
        alteracoes=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = "Os dados do contrato de honorários foram atualizados."

        if alteracoes:
            descricao = TimelineService._montar_descricao_alteracoes(
                alteracoes
            )

        dados = TimelineService._dados_honorario(honorario)
        dados["alteracoes"] = alteracoes or {}

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="HONORARIO_EDITADO",
            titulo="Contrato de honorários atualizado",
            descricao=descricao,
            icone="✏️",
            cor="primary",
            url=TimelineService._url_honorario(honorario),
            dados=dados,
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_status_honorario_alterado(
        caso,
        honorario,
        status_anterior,
        novo_status,
        usuario=None,
        realizar_commit=False,
    ):
        anterior = TimelineService.formatar_status_honorario(
            status_anterior
        )
        novo = TimelineService.formatar_status_honorario(
            novo_status
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="STATUS_HONORARIO_ALTERADO",
            titulo="Status dos honorários alterado",
            descricao=f"{anterior} → {novo}",
            icone="🔄",
            cor=TimelineService.cor_status_honorario(novo_status),
            url=TimelineService._url_honorario(honorario),
            dados={
                "honorario_id": honorario.id,
                "status_anterior": status_anterior,
                "novo_status": novo_status,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_honorario_excluido(
        caso,
        honorario,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{honorario.descricao} — "
            f"{TimelineService._formatar_moeda(honorario.valor_total)}"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="HONORARIO_EXCLUIDO",
            titulo="Contrato de honorários excluído",
            descricao=descricao,
            icone="🗑️",
            cor="danger",
            url=TimelineService._url_caso_secao(caso, "honorarios"),
            dados=TimelineService._dados_honorario(honorario),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_pagamento_recebido(
        caso,
        honorario,
        parcela,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"Parcela {parcela.numero}/"
            f"{honorario.quantidade_parcelas or len(honorario.parcelas)} — "
            f"{TimelineService._formatar_moeda(parcela.valor)}"
        )

        if parcela.forma_pagamento:
            descricao += f" — {parcela.forma_pagamento}"

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PAGAMENTO_RECEBIDO",
            titulo="Pagamento de honorários recebido",
            descricao=descricao,
            icone="✅",
            cor="success",
            url=TimelineService._url_honorario(honorario),
            dados=TimelineService._dados_parcela(parcela),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_pagamento_reaberto(
        caso,
        honorario,
        parcela,
        status_anterior="PAGO",
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"Parcela {parcela.numero}/"
            f"{honorario.quantidade_parcelas or len(honorario.parcelas)} — "
            f"{TimelineService._formatar_moeda(parcela.valor)} — "
            f"{TimelineService.formatar_status_parcela(status_anterior)} → "
            f"{TimelineService.formatar_status_parcela(parcela.status)}"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="PAGAMENTO_REABERTO",
            titulo="Pagamento de honorários reaberto",
            descricao=descricao,
            icone="↩️",
            cor="warning",
            url=TimelineService._url_honorario(honorario),
            dados=TimelineService._dados_parcela(parcela),
            realizar_commit=realizar_commit,
        )



    @staticmethod
    def registrar_atendimento_criado(
        caso,
        atendimento,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{TimelineService.formatar_tipo_atendimento(atendimento.tipo)} — "
            f"{atendimento.assunto} — "
            f"{TimelineService._formatar_data(atendimento.data_atendimento)}"
        )

        if atendimento.horario:
            descricao += f" às {atendimento.horario.strftime('%H:%M')}"

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="ATENDIMENTO_CRIADO",
            titulo="Atendimento cadastrado",
            descricao=descricao,
            icone="📞",
            cor="success",
            url=TimelineService._url_caso_secao(caso, "atendimentos"),
            dados=TimelineService._dados_atendimento(atendimento),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_atendimento_editado(
        caso,
        atendimento,
        alteracoes=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = "Os dados do atendimento foram atualizados."

        if alteracoes:
            descricao = TimelineService._montar_descricao_alteracoes(
                alteracoes
            )

        dados = TimelineService._dados_atendimento(atendimento)
        dados["alteracoes"] = alteracoes or {}

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="ATENDIMENTO_EDITADO",
            titulo="Atendimento atualizado",
            descricao=descricao,
            icone="✏️",
            cor="primary",
            url=TimelineService._url_caso_secao(caso, "atendimentos"),
            dados=dados,
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_status_atendimento_alterado(
        caso,
        atendimento,
        status_anterior,
        novo_status,
        usuario=None,
        realizar_commit=False,
    ):
        anterior = TimelineService.formatar_status_atendimento(
            status_anterior
        )
        novo = TimelineService.formatar_status_atendimento(
            novo_status
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="STATUS_ATENDIMENTO_ALTERADO",
            titulo="Status do atendimento alterado",
            descricao=f"{anterior} → {novo}",
            icone="🔄",
            cor=TimelineService.cor_status_atendimento(novo_status),
            url=TimelineService._url_caso_secao(caso, "atendimentos"),
            dados={
                "atendimento_id": atendimento.id,
                "status_anterior": status_anterior,
                "novo_status": novo_status,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_retorno_atendimento_alterado(
        caso,
        atendimento,
        retorno_anterior,
        novo_retorno,
        usuario=None,
        realizar_commit=False,
    ):
        if retorno_anterior is None and novo_retorno is not None:
            titulo = "Retorno agendado"
            descricao = TimelineService._formatar_data(novo_retorno)
            icone = "📅"
            cor = "info"
            tipo = "RETORNO_ATENDIMENTO_AGENDADO"
        elif retorno_anterior is not None and novo_retorno is None:
            titulo = "Retorno removido"
            descricao = (
                "Retorno anteriormente previsto para "
                f"{TimelineService._formatar_data(retorno_anterior)}"
            )
            icone = "🗑️"
            cor = "secondary"
            tipo = "RETORNO_ATENDIMENTO_REMOVIDO"
        else:
            titulo = "Data de retorno alterada"
            descricao = (
                f"{TimelineService._formatar_data(retorno_anterior)} → "
                f"{TimelineService._formatar_data(novo_retorno)}"
            )
            icone = "📅"
            cor = "warning"
            tipo = "RETORNO_ATENDIMENTO_ALTERADO"

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            descricao=descricao,
            icone=icone,
            cor=cor,
            url=TimelineService._url_caso_secao(caso, "atendimentos"),
            dados={
                "atendimento_id": atendimento.id,
                "retorno_anterior": (
                    retorno_anterior.isoformat()
                    if retorno_anterior
                    else None
                ),
                "novo_retorno": (
                    novo_retorno.isoformat()
                    if novo_retorno
                    else None
                ),
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_atendimento_excluido(
        caso,
        atendimento,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{TimelineService.formatar_tipo_atendimento(atendimento.tipo)} — "
            f"{atendimento.assunto}"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="ATENDIMENTO_EXCLUIDO",
            titulo="Atendimento excluído",
            descricao=descricao,
            icone="🗑️",
            cor="danger",
            url=TimelineService._url_caso_secao(caso, "atendimentos"),
            dados=TimelineService._dados_atendimento(atendimento),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_evento_agenda_criado(
        caso,
        evento_agenda,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{TimelineService.formatar_tipo_agenda(evento_agenda.tipo)} — "
            f"{evento_agenda.titulo} — "
            f"{TimelineService._formatar_data(evento_agenda.data)}"
        )

        if evento_agenda.hora_inicio:
            descricao += (
                f" às {evento_agenda.hora_inicio.strftime('%H:%M')}"
            )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="AGENDA_EVENTO_CRIADO",
            titulo="Compromisso cadastrado",
            descricao=descricao,
            icone="📅",
            cor="success",
            url=TimelineService._url_caso_secao(caso, "agenda"),
            dados=TimelineService._dados_evento_agenda(evento_agenda),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_evento_agenda_editado(
        caso,
        evento_agenda,
        alteracoes=None,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = "Os dados do compromisso foram atualizados."

        if alteracoes:
            descricao = TimelineService._montar_descricao_alteracoes(
                alteracoes
            )

        dados = TimelineService._dados_evento_agenda(evento_agenda)
        dados["alteracoes"] = alteracoes or {}

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="AGENDA_EVENTO_EDITADO",
            titulo="Compromisso atualizado",
            descricao=descricao,
            icone="✏️",
            cor="primary",
            url=TimelineService._url_caso_secao(caso, "agenda"),
            dados=dados,
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_status_evento_agenda_alterado(
        caso,
        evento_agenda,
        status_anterior,
        novo_status,
        usuario=None,
        realizar_commit=False,
    ):
        anterior = TimelineService.formatar_status_agenda(status_anterior)
        novo = TimelineService.formatar_status_agenda(novo_status)

        configuracoes = {
            "CONCLUIDO": (
                "Compromisso concluído",
                "✅",
                "success",
                "AGENDA_EVENTO_CONCLUIDO",
            ),
            "CANCELADO": (
                "Compromisso cancelado",
                "🚫",
                "danger",
                "AGENDA_EVENTO_CANCELADO",
            ),
            "PENDENTE": (
                "Compromisso reaberto",
                "↩️",
                "warning",
                "AGENDA_EVENTO_REABERTO",
            ),
        }

        titulo, icone, cor, tipo = configuracoes.get(
            novo_status,
            (
                "Status do compromisso alterado",
                "🔄",
                "info",
                "AGENDA_STATUS_ALTERADO",
            ),
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            descricao=f"{anterior} → {novo}",
            icone=icone,
            cor=cor,
            url=TimelineService._url_caso_secao(caso, "agenda"),
            dados={
                "evento_agenda_id": evento_agenda.id,
                "status_anterior": status_anterior,
                "novo_status": novo_status,
            },
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def registrar_evento_agenda_excluido(
        caso,
        evento_agenda,
        usuario=None,
        realizar_commit=False,
    ):
        descricao = (
            f"{TimelineService.formatar_tipo_agenda(evento_agenda.tipo)} — "
            f"{evento_agenda.titulo} — "
            f"{TimelineService._formatar_data(evento_agenda.data)}"
        )

        return TimelineService.registrar_evento(
            caso=caso,
            usuario=usuario,
            tipo="AGENDA_EVENTO_EXCLUIDO",
            titulo="Compromisso excluído",
            descricao=descricao,
            icone="🗑️",
            cor="danger",
            url=TimelineService._url_caso_secao(caso, "agenda"),
            dados=TimelineService._dados_evento_agenda(evento_agenda),
            realizar_commit=realizar_commit,
        )

    @staticmethod
    def listar_eventos_do_caso(
        caso_id,
        limite=None,
    ):
        consulta = (
            EventoCaso.query
            .filter_by(caso_id=caso_id)
            .order_by(EventoCaso.criado_em.desc())
        )

        if limite:
            consulta = consulta.limit(limite)

        return consulta.all()

    @staticmethod
    def formatar_prioridade(prioridade):
        prioridades = {
            "BAIXA": "Baixa",
            "NORMAL": "Normal",
            "ALTA": "Alta",
            "URGENTE": "Urgente",
        }

        return prioridades.get(
            prioridade,
            prioridade or "Não definida",
        )

    @staticmethod
    def cor_prioridade(prioridade):
        cores = {
            "BAIXA": "secondary",
            "NORMAL": "primary",
            "ALTA": "warning",
            "URGENTE": "danger",
        }

        return cores.get(
            prioridade,
            "secondary",
        )

    @staticmethod
    def formatar_situacao_processo(situacao):
        situacoes = {
            "ATIVO": "Ativo",
            "SUSPENSO": "Suspenso",
            "ARQUIVADO": "Arquivado",
            "ENCERRADO": "Encerrado",
            "BAIXADO": "Baixado",
        }

        return situacoes.get(
            situacao,
            situacao or "Não informada",
        )

    @staticmethod
    def cor_situacao_processo(situacao):
        cores = {
            "ATIVO": "success",
            "SUSPENSO": "warning",
            "ARQUIVADO": "secondary",
            "ENCERRADO": "primary",
            "BAIXADO": "dark",
        }

        return cores.get(
            situacao,
            "info",
        )




    @staticmethod
    def formatar_tipo_atendimento(tipo):
        tipos = {
            "CONSULTA": "Consulta",
            "REUNIAO": "Reunião",
            "LIGACAO": "Ligação",
            "WHATSAPP": "WhatsApp",
            "EMAIL": "E-mail",
            "AUDIENCIA": "Audiência",
            "DILIGENCIA": "Diligência",
            "OUTRO": "Outro",
        }

        return tipos.get(tipo, tipo or "Não informado")

    @staticmethod
    def formatar_status_atendimento(status):
        status_map = {
            "AGENDADO": "Agendado",
            "REALIZADO": "Realizado",
            "CANCELADO": "Cancelado",
        }

        return status_map.get(status, status or "Não informado")

    @staticmethod
    def cor_status_atendimento(status):
        cores = {
            "AGENDADO": "primary",
            "REALIZADO": "success",
            "CANCELADO": "secondary",
        }

        return cores.get(status, "secondary")

    @staticmethod
    def formatar_tipo_agenda(tipo):
        tipos = {
            "AUDIENCIA": "Audiência",
            "PRAZO": "Prazo",
            "REUNIAO": "Reunião",
            "ATENDIMENTO": "Atendimento",
            "TAREFA": "Tarefa",
            "LEMBRETE": "Lembrete",
        }

        return tipos.get(tipo, tipo or "Não informado")

    @staticmethod
    def formatar_status_agenda(status):
        status_map = {
            "PENDENTE": "Pendente",
            "CONCLUIDO": "Concluído",
            "CANCELADO": "Cancelado",
        }

        return status_map.get(status, status or "Não informado")

    @staticmethod
    def formatar_status_honorario(status):
        status_map = {
            "ATIVO": "Ativo",
            "QUITADO": "Quitado",
            "CANCELADO": "Cancelado",
            "SUSPENSO": "Suspenso",
        }

        return status_map.get(
            status,
            status or "Não informado",
        )

    @staticmethod
    def cor_status_honorario(status):
        cores = {
            "ATIVO": "success",
            "QUITADO": "primary",
            "CANCELADO": "danger",
            "SUSPENSO": "warning",
        }

        return cores.get(status, "secondary")

    @staticmethod
    def formatar_status_parcela(status):
        status_map = {
            "PENDENTE": "Pendente",
            "PAGO": "Pago",
            "ATRASADO": "Atrasado",
            "CANCELADO": "Cancelado",
        }

        return status_map.get(
            status,
            status or "Não informado",
        )

    @staticmethod
    def _formatar_moeda(valor):
        if valor is None:
            return "R$ 0,00"

        valor_formatado = f"{valor:,.2f}"

        return (
            "R$ "
            + valor_formatado
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )



    @staticmethod
    def _formatar_data(valor):
        if not valor:
            return "Não informada"
        return valor.strftime("%d/%m/%Y")

    @staticmethod
    def _dados_atendimento(atendimento):
        return {
            "atendimento_id": atendimento.id,
            "caso_id": atendimento.caso_id,
            "tipo": atendimento.tipo,
            "assunto": atendimento.assunto,
            "data_atendimento": (
                atendimento.data_atendimento.isoformat()
                if atendimento.data_atendimento
                else None
            ),
            "horario": (
                atendimento.horario.strftime("%H:%M")
                if atendimento.horario
                else None
            ),
            "status": atendimento.status,
            "descricao": atendimento.descricao,
            "retorno_em": (
                atendimento.retorno_em.isoformat()
                if atendimento.retorno_em
                else None
            ),
            "usuario_id": atendimento.usuario_id,
            "responsavel_nome": (
                atendimento.usuario.nome
                if atendimento.usuario
                else None
            ),
        }

    @staticmethod
    def _dados_evento_agenda(evento_agenda):
        return {
            "evento_agenda_id": evento_agenda.id,
            "caso_id": evento_agenda.caso_id,
            "processo_id": evento_agenda.processo_id,
            "responsavel_id": evento_agenda.responsavel_id,
            "titulo": evento_agenda.titulo,
            "descricao": evento_agenda.descricao,
            "tipo": evento_agenda.tipo,
            "status": evento_agenda.status,
            "prioridade": evento_agenda.prioridade,
            "data": (
                evento_agenda.data.isoformat()
                if evento_agenda.data
                else None
            ),
            "hora_inicio": (
                evento_agenda.hora_inicio.strftime("%H:%M")
                if evento_agenda.hora_inicio
                else None
            ),
            "hora_fim": (
                evento_agenda.hora_fim.strftime("%H:%M")
                if evento_agenda.hora_fim
                else None
            ),
            "local": evento_agenda.local,
            "concluido_em": (
                evento_agenda.concluido_em.isoformat()
                if evento_agenda.concluido_em
                else None
            ),
            "responsavel_nome": (
                evento_agenda.responsavel.nome
                if evento_agenda.responsavel
                else None
            ),
            "processo_numero": (
                evento_agenda.processo.numero_cnj
                if evento_agenda.processo
                else None
            ),
        }

    @staticmethod
    def _dados_honorario(honorario):
        return {
            "honorario_id": honorario.id,
            "caso_id": honorario.caso_id,
            "descricao": honorario.descricao,
            "tipo_cobranca": honorario.tipo_cobranca,
            "valor_total": str(honorario.valor_total or 0),
            "valor_entrada": str(honorario.valor_entrada or 0),
            "quantidade_parcelas": honorario.quantidade_parcelas,
            "forma_pagamento": honorario.forma_pagamento,
            "percentual_exito": (
                str(honorario.percentual_exito)
                if honorario.percentual_exito is not None
                else None
            ),
            "data_contrato": (
                honorario.data_contrato.isoformat()
                if honorario.data_contrato
                else None
            ),
            "primeiro_vencimento": (
                honorario.primeiro_vencimento.isoformat()
                if honorario.primeiro_vencimento
                else None
            ),
            "status": honorario.status,
            "observacoes": honorario.observacoes,
        }

    @staticmethod
    def _dados_parcela(parcela):
        return {
            "parcela_id": parcela.id,
            "honorario_id": parcela.honorario_id,
            "numero": parcela.numero,
            "valor": str(parcela.valor or 0),
            "data_vencimento": (
                parcela.data_vencimento.isoformat()
                if parcela.data_vencimento
                else None
            ),
            "data_pagamento": (
                parcela.data_pagamento.isoformat()
                if parcela.data_pagamento
                else None
            ),
            "forma_pagamento": parcela.forma_pagamento,
            "status": parcela.status,
            "observacoes": parcela.observacoes,
        }

    @staticmethod
    def _montar_descricao_alteracoes(alteracoes):
        descricoes = []

        for campo, valores in alteracoes.items():
            if not isinstance(valores, dict):
                continue

            rotulo = valores.get(
                "rotulo",
                campo.replace("_", " ").capitalize(),
            )

            anterior = valores.get(
                "anterior",
                "Não informado",
            )

            novo = valores.get(
                "novo",
                "Não informado",
            )

            descricoes.append(
                f"{rotulo}: {anterior} → {novo}"
            )

        if not descricoes:
            return "Os dados foram atualizados."

        return "; ".join(descricoes)

    @staticmethod
    def _dados_processo(processo):
        return {
            "processo_id": processo.id,
            "caso_id": processo.caso_id,
            "numero_cnj": processo.numero_cnj,
            "tribunal": processo.tribunal,
            "comarca": processo.comarca,
            "vara": processo.vara,
            "classe_processual": processo.classe_processual,
            "assunto": processo.assunto,
            "polo_ativo": processo.polo_ativo,
            "polo_passivo": processo.polo_passivo,
            "data_distribuicao": (
                processo.data_distribuicao.isoformat()
                if processo.data_distribuicao
                else None
            ),
            "situacao": processo.situacao,
            "valor_causa": (
                str(processo.valor_causa)
                if processo.valor_causa is not None
                else None
            ),
            "observacoes": processo.observacoes,
        }

    @staticmethod
    def _url_caso(caso):
        try:
            return url_for(
                "casos.detalhes",
                caso_id=caso.id,
            )
        except RuntimeError:
            return None

    @staticmethod
    def _url_caso_secao(caso, secao):
        try:
            return (
                url_for(
                    "casos.detalhes",
                    caso_id=caso.id,
                )
                + f"#{secao}"
            )
        except RuntimeError:
            return None


    @staticmethod
    def _url_honorario(honorario):
        try:
            return url_for(
                "honorarios.detalhes",
                honorario_id=honorario.id,
            )
        except RuntimeError:
            return None

    @staticmethod
    def _url_documento(documento):
        try:
            return url_for(
                "documentos_caso.download",
                documento_id=documento.id,
            )
        except RuntimeError:
            return None