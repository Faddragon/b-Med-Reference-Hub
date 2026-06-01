import sys
import json
import os
from src.motor_extracao.pubmed_api import (
    buscar_pubmed_por_doi,
    buscar_pubmed_por_titulo,
    buscar_pubmed_por_pmid,
)
from src.motor_extracao.pdf_handler import processar_pdf, info_pdf, preview_texto
from src.motor_extracao.validador_doi import extrair_doi
from src.formatador.vancouver import gerar_vancouver
from src.formatador.abnt import gerar_abnt


def exibir_resultado(resultado, fonte):
    if not resultado:
        print(f"\n[Erro] Nenhum artigo encontrado para a busca por {fonte}.")
        return
    print(f"\n[Sucesso] Artigo Encontrado (PubMed - {fonte})!")
    print("---------------------------------------------------------")
    print("\nREFERÊNCIA VANCOUVER:")
    print(gerar_vancouver(resultado))
    print("\nREFERÊNCIA ABNT:")
    print(gerar_abnt(resultado))
    print("\nMETADADOS ESTRUTURADOS (JSON):")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


def escolher_da_lista(resultados):
    if not resultados:
        return None
    if len(resultados) == 1:
        return resultados[0]

    print(f"\nForam encontrados {len(resultados)} artigos. Escolha um:")
    for i, r in enumerate(resultados, start=1):
        titulo = (r.get("titulo") or "(sem título)").strip()
        revista = (r.get("revista") or "").strip()
        ano = r.get("ano") or "s/ ano"
        pmid = r.get("pmid") or "s/ pmid"
        print(f"  {i}. [{pmid}] {titulo}  -  {revista}, {ano}")

    while True:
        escolha = input(f"Digite 1-{len(resultados)} (ou 0 para cancelar): ").strip()
        if escolha == "0":
            return None
        if escolha.isdigit():
            n = int(escolha)
            if 1 <= n <= len(resultados):
                return resultados[n - 1]
        print("Escolha inválida.")


def _exibir_info_pdf(info):
    if not info:
        return
    print("\n[Info PDF]")
    print(f"  Arquivo: {info.get('nome')}")
    print(f"  Tamanho: {info.get('tamanho_kb')} KB ({info.get('tamanho_bytes')} bytes)")
    paginas = info.get("paginas_total")
    if paginas is not None:
        print(f"  Páginas: {paginas} (lendo até 3 para extração)")


def _buscar_fallback_por_termo(termo, tipo):
    if tipo == "doi":
        return buscar_pubmed_por_doi(termo)
    if tipo == "pmid":
        return buscar_pubmed_por_pmid(termo)
    resultados = buscar_pubmed_por_titulo(termo)
    return escolher_da_lista(resultados)


def processar_e_exibir_pdf(caminho_pdf):
    caminho_pdf = caminho_pdf.strip().strip('"').strip("'")
    if not os.path.splitext(caminho_pdf)[1].lower() == ".pdf":
        print(f"\n[Erro] O arquivo precisa ter extensão .pdf: {caminho_pdf}")
        return

    info = info_pdf(caminho_pdf)
    _exibir_info_pdf(info)

    try:
        texto = processar_pdf(caminho_pdf)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[Erro] {e}")
        return

    if not texto:
        print("\n[Erro] Não foi possível extrair texto do PDF.")
        return

    preview = preview_texto(texto)
    if preview:
        print(f"\n[Preview do texto extraído]\n  {preview}")

    doi = extrair_doi(texto)
    if doi:
        print(f"\n[OK] DOI extraído: {doi}")
        resultado = buscar_pubmed_por_doi(doi)
        exibir_resultado(resultado, f"DOI {doi} (via PDF)")
        return

    print("\n[Aviso] Não foi possível extrair um DOI do PDF.")
    print("Como deseja prosseguir?")
    print("  1. Informar DOI manualmente")
    print("  2. Informar PMID")
    print("  3. Buscar por título do artigo")
    print("  0. Cancelar")
    sub = input("> ").strip()

    if sub == "1":
        doi_manual = input("Digite o DOI: ").strip()
        if not doi_manual:
            print("[Erro] DOI não pode ser vazio.")
            return
        resultado = buscar_pubmed_por_doi(doi_manual)
        exibir_resultado(resultado, f"DOI {doi_manual} (manual, via PDF)")
    elif sub == "2":
        pmid = input("Digite o PMID: ").strip()
        if not pmid:
            print("[Erro] PMID não pode ser vazio.")
            return
        resultado = buscar_pubmed_por_pmid(pmid)
        exibir_resultado(resultado, f"PMID {pmid} (via PDF)")
    elif sub == "3":
        titulo = input("Digite o Título: ").strip()
        if not titulo:
            print("[Erro] Título não pode ser vazio.")
            return
        resultados = buscar_pubmed_por_titulo(titulo)
        escolhido = escolher_da_lista(resultados)
        if escolhido is not None:
            exibir_resultado(escolhido, f"título '{titulo}' (via PDF)")
    else:
        print("Operação cancelada.")


def main():
    print("Bem-vindo ao b-Med Reference Hub!")
    print("---------------------------------")

    while True:
        print("\nEscolha uma opção:")
        print("1. Buscar artigo por DOI")
        print("2. Buscar artigo por Título (top-5)")
        print("3. Buscar artigo por PMID")
        print("4. Processar PDF local")
        print("0. Sair")

        escolha = input("> ").strip()

        if escolha == "0":
            print("Saindo do sistema. Até logo!")
            sys.exit(0)
        elif escolha == "1":
            doi = input("Digite o DOI: ").strip()
            if not doi:
                print("[Erro] DOI não pode ser vazio.")
                continue
            resultado = buscar_pubmed_por_doi(doi)
            exibir_resultado(resultado, f"DOI {doi}")
        elif escolha == "2":
            titulo = input("Digite o Título: ").strip()
            if not titulo:
                print("[Erro] Título não pode ser vazio.")
                continue
            resultados = buscar_pubmed_por_titulo(titulo)
            escolhido = escolher_da_lista(resultados)
            if escolhido is not None:
                exibir_resultado(escolhido, f"título '{titulo}'")
        elif escolha == "3":
            pmid = input("Digite o PMID: ").strip()
            if not pmid:
                print("[Erro] PMID não pode ser vazio.")
                continue
            resultado = buscar_pubmed_por_pmid(pmid)
            exibir_resultado(resultado, f"PMID {pmid}")
        elif escolha == "4":
            caminho_pdf = input("Digite o caminho do PDF: ").strip()
            if not caminho_pdf:
                print("[Erro] Caminho não pode ser vazio.")
                continue
            processar_e_exibir_pdf(caminho_pdf)
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
