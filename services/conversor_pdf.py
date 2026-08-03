from pathlib import Path


class ErroConversaoPDF(Exception):
    """Erro controlado durante a conversão de DOCX para PDF."""


def converter_docx_para_pdf(
    caminho_docx,
    caminho_pdf,
) -> Path:
    """
    Converte um arquivo DOCX para PDF usando o Microsoft Word.

    Requisitos:
    - Windows;
    - Microsoft Word instalado;
    - pacote pywin32 instalado.
    """
    caminho_docx = Path(caminho_docx).resolve()
    caminho_pdf = Path(caminho_pdf).resolve()

    if not caminho_docx.is_file():
        raise ErroConversaoPDF(
            "O arquivo DOCX informado para conversão não foi encontrado."
        )

    caminho_pdf.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    word = None
    documento = None
    pythoncom = None

    try:
        import pythoncom as modulo_pythoncom
        import win32com.client

        pythoncom = modulo_pythoncom
        pythoncom.CoInitialize()

        word = win32com.client.DispatchEx(
            "Word.Application"
        )
        word.Visible = False
        word.DisplayAlerts = 0

        documento = word.Documents.Open(
            str(caminho_docx),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )

        documento.ExportAsFixedFormat(
            OutputFileName=str(caminho_pdf),
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0,
            CreateBookmarks=1,
        )

    except ImportError as erro:
        raise ErroConversaoPDF(
            "O pacote pywin32 não está instalado. "
            "Execute: pip install pywin32"
        ) from erro

    except Exception as erro:
        if caminho_pdf.is_file():
            caminho_pdf.unlink()

        raise ErroConversaoPDF(
            "Não foi possível converter o documento para PDF. "
            "Verifique se o Microsoft Word está instalado e funcionando."
        ) from erro

    finally:
        if documento is not None:
            try:
                documento.Close(
                    SaveChanges=False
                )
            except Exception:
                pass

        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass

        if pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    if not caminho_pdf.is_file():
        raise ErroConversaoPDF(
            "O Word concluiu a conversão, mas o arquivo PDF não foi criado."
        )

    return caminho_pdf