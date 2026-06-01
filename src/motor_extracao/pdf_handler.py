import os
import shutil
import fitz
from src.config import PDFS_DIR


def processar_pdf(caminho_origem: str) -> str:
    if not os.path.exists(caminho_origem):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_origem}")
    if not os.path.isfile(caminho_origem):
        raise ValueError(f"O caminho não é um arquivo: {caminho_origem}")

    print(f"[PDF Handler] Lendo {caminho_origem}")

    texto_completo = ""
    try:
        doc = fitz.open(caminho_origem)
        max_paginas = min(doc.page_count, 3)
        textos = [doc[i].get_text() for i in range(max_paginas)]
        texto_completo = "\n".join(textos)
        doc.close()
    except Exception as e:
        print(f"[Erro PyMuPDF] {e}")
        return ""

    nome_arquivo = os.path.basename(caminho_origem)
    destino = os.path.join(PDFS_DIR, nome_arquivo)
    try:
        shutil.copy2(caminho_origem, destino)
        print(f"[PDF Handler] Cópia arquivada em: {destino}")
    except Exception as e:
        print(f"[Aviso] Não foi possível arquivar o PDF: {e}")

    return texto_completo


def info_pdf(caminho_origem: str) -> dict:
    if not os.path.isfile(caminho_origem):
        return {}
    tamanho_bytes = os.path.getsize(caminho_origem)
    info = {
        "caminho": os.path.abspath(caminho_origem),
        "nome": os.path.basename(caminho_origem),
        "tamanho_bytes": tamanho_bytes,
        "tamanho_kb": round(tamanho_bytes / 1024, 1),
        "paginas_total": None,
    }
    try:
        doc = fitz.open(caminho_origem)
        info["paginas_total"] = doc.page_count
        doc.close()
    except Exception:
        pass
    return info


def preview_texto(texto: str, max_caracteres: int = 240) -> str:
    if not texto:
        return ""
    limpo = " ".join(texto.split())
    if len(limpo) <= max_caracteres:
        return limpo
    return limpo[:max_caracteres].rsplit(" ", 1)[0] + "..."
