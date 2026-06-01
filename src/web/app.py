import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src.formatador.abnt import gerar_abnt
from src.formatador.vancouver import gerar_vancouver
from src.motor_extracao.pdf_handler import info_pdf, preview_texto, processar_pdf
from src.motor_extracao.pubmed_api import (
    buscar_pubmed_por_doi,
    buscar_pubmed_por_pmid,
    buscar_pubmed_por_titulo,
)
from src.motor_extracao.validador_doi import extrair_doi


def _formatar(meta):
    return {
        "metadados": meta,
        "vancouver": gerar_vancouver(meta),
        "abnt": gerar_abnt(meta),
    }


def _erro(msg, status=400):
    return jsonify({"erro": msg}), status


def criar_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/buscar/doi")
    def api_doi():
        dado = (request.get_json(silent=True) or {}).get("doi", "").strip()
        if not dado:
            return _erro("DOI não pode ser vazio.")
        meta = buscar_pubmed_por_doi(dado)
        if not meta:
            return _erro(f"Nenhum artigo encontrado para o DOI {dado}.", 404)
        return jsonify(_formatar(meta))

    @app.post("/api/buscar/pmid")
    def api_pmid():
        dado = (request.get_json(silent=True) or {}).get("pmid", "").strip()
        if not dado:
            return _erro("PMID não pode ser vazio.")
        meta = buscar_pubmed_por_pmid(dado)
        if not meta:
            return _erro(f"Nenhum artigo encontrado para o PMID {dado}.", 404)
        return jsonify(_formatar(meta))

    @app.post("/api/buscar/titulo")
    def api_titulo():
        body = request.get_json(silent=True) or {}
        termo = (body.get("titulo") or "").strip()
        if not termo:
            return _erro("Título não pode ser vazio.")
        resultados = buscar_pubmed_por_titulo(termo)
        if not resultados:
            return _erro(f"Nenhum artigo encontrado para o título '{termo}'.", 404)
        return jsonify(
            {
                "resultados": [
                    {
                        **r,
                        "vancouver": gerar_vancouver(r),
                        "abnt": gerar_abnt(r),
                    }
                    for r in resultados
                ]
            }
        )

    @app.post("/api/upload")
    def api_upload():
        arquivo = request.files.get("pdf")
        if not arquivo or not arquivo.filename:
            return _erro("Nenhum arquivo enviado.")
        if not arquivo.filename.lower().endswith(".pdf"):
            return _erro("O arquivo precisa ter extensão .pdf.")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            caminho_tmp = tmp.name
            arquivo.save(caminho_tmp)

        try:
            info = info_pdf(caminho_tmp)
            texto = processar_pdf(caminho_tmp)
        finally:
            try:
                os.unlink(caminho_tmp)
            except OSError:
                pass

        if not texto:
            return _erro("Não foi possível extrair texto do PDF.", 422)

        doi = extrair_doi(texto)
        resposta = {
            "info_pdf": info,
            "preview": preview_texto(texto),
        }
        if not doi:
            resposta["aviso"] = "Nenhum DOI encontrado no PDF."
            resposta["sugestoes"] = ["doi", "pmid", "titulo"]
            return jsonify(resposta), 422

        meta = buscar_pubmed_por_doi(doi)
        if not meta:
            resposta["doi_extraido"] = doi
            resposta["aviso"] = f"DOI {doi} extraído, mas sem metadados no PubMed."
            return jsonify(resposta), 404

        resposta.update(
            {
                "doi_extraido": doi,
                **_formatar(meta),
            }
        )
        return jsonify(resposta)

    return app


if __name__ == "__main__":
    criar_app().run(debug=True, host="127.0.0.1", port=5000)
