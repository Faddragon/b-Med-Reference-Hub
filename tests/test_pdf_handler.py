import os
import fitz
import pytest

from src.motor_extracao import pdf_handler


def _criar_pdf(tmp_path, nome="artigo.pdf", texto="Conteúdo de teste com 10.1234/abc.2024.001"):
    caminho = tmp_path / nome
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"{texto} página {i}")
    doc.save(str(caminho))
    doc.close()
    return str(caminho)


def test_info_pdf_retorna_metadados(tmp_path):
    caminho = _criar_pdf(tmp_path)
    info = pdf_handler.info_pdf(caminho)
    assert info["nome"] == "artigo.pdf"
    assert info["tamanho_bytes"] > 0
    assert info["tamanho_kb"] >= 0
    assert info["paginas_total"] == 2


def test_info_pdf_arquivo_inexistente_retorna_vazio(tmp_path):
    info = pdf_handler.info_pdf(str(tmp_path / "nao_existe.pdf"))
    assert info == {}


def test_info_pdf_diretorio_retorna_vazio(tmp_path):
    info = pdf_handler.info_pdf(str(tmp_path))
    assert info == {}


def test_processar_pdf_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        pdf_handler.processar_pdf(str(tmp_path / "fantasma.pdf"))


def test_processar_pdf_caminho_nao_arquivo(tmp_path):
    with pytest.raises(ValueError):
        pdf_handler.processar_pdf(str(tmp_path))


def test_processar_pdf_arquiva_copia(tmp_path, monkeypatch):
    pdfs_dir = tmp_path / "pdfs_armazenados"
    pdfs_dir.mkdir()
    monkeypatch.setattr(pdf_handler, "PDFS_DIR", str(pdfs_dir))

    caminho = _criar_pdf(tmp_path)
    texto = pdf_handler.processar_pdf(caminho)
    assert "10.1234/abc.2024.001" in texto
    assert os.path.isfile(pdfs_dir / "artigo.pdf")


def test_preview_texto_curto_nao_trunca():
    assert pdf_handler.preview_texto("Olá mundo") == "Olá mundo"


def test_preview_texto_vazio_retorna_vazio():
    assert pdf_handler.preview_texto("") == ""


def test_preview_texto_longo_trunca_em_palavra():
    texto = " ".join(["palavra"] * 100)
    preview = pdf_handler.preview_texto(texto, max_caracteres=40)
    assert preview.endswith("...")
    assert len(preview) <= 43
    assert "  " not in preview


def test_preview_texto_colapsa_espacos_e_quebras():
    texto = "linha1\n\n   linha2\tlinha3"
    assert pdf_handler.preview_texto(texto) == "linha1 linha2 linha3"
