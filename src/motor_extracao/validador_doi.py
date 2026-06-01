import re


def extrair_doi(texto: str):
    padrao = r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)'

    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        doi = match.group(1)
        doi = doi.rstrip(".,;)")
        if doi.endswith(")"):
            abertos = doi.count("(")
            fechados = doi.count(")")
            if fechados > abertos:
                doi = doi[: doi.rfind(")")]
        return doi

    return None
