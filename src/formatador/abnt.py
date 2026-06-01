import datetime


def _formatar_autor_abnt(autor: str) -> str:
    partes = autor.strip().split(maxsplit=1)
    if len(partes) == 1:
        return partes[0].upper()
    sobrenome, iniciais = partes
    iniciais_formatadas = ". ".join(list(initials := iniciais.upper())) + "."
    return f"{sobrenome.upper()}, {iniciais_formatadas}"


def _formatar_lista_autores_abnt(autores, limite=3):
    if not autores:
        return "AUTORES DESCONHECIDOS"
    lista = [_formatar_autor_abnt(a) for a in autores]
    if len(lista) > limite:
        return "; ".join(lista[:limite]) + ", et al."
    return "; ".join(lista)


def gerar_abnt(dados):
    autores = dados.get("autores") or []
    titulo = (dados.get("titulo") or "Título indisponível").strip()
    revista = (dados.get("revista") or "Periódico não identificado").strip()
    ano = dados.get("ano") or datetime.datetime.now().year
    volume = dados.get("volume")
    numero = dados.get("numero")
    paginas = dados.get("paginas")
    doi = dados.get("doi")

    autores_str = _formatar_lista_autores_abnt(autores)
    if not autores_str.endswith("."):
        autores_str += "."

    referencia = f"{autores_str} {titulo}. {revista}"

    partes = []
    if volume:
        partes.append(f"v. {volume}")
    if numero:
        partes.append(f"n. {numero}")
    if paginas:
        partes.append(f"p. {paginas}")
    partes.append(str(ano))

    referencia += ", " + ", ".join(partes) + "."

    if doi:
        referencia += f" Disponível em: https://doi.org/{doi}."

    return referencia
