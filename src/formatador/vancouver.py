import datetime


def _formatar_lista_autores_vancouver(autores, limite=6):
    if not autores:
        return "Autores desconhecidos"
    if len(autores) > limite:
        return ", ".join(autores[:limite]) + ", et al"
    return ", ".join(autores)


def gerar_vancouver(dados):
    autores = dados.get("autores") or []
    titulo = (dados.get("titulo") or "Título indisponível").strip()
    revista = (dados.get("revista") or "Periódico não identificado").strip()
    ano = dados.get("ano") or datetime.datetime.now().year
    volume = dados.get("volume")
    numero = dados.get("numero")
    paginas = dados.get("paginas")
    doi = dados.get("doi")

    autores_str = _formatar_lista_autores_vancouver(autores)
    if not autores_str.endswith("."):
        autores_str += "."

    if not titulo.endswith("."):
        titulo += "."

    referencia = f"{autores_str} {titulo} {revista}. {ano}"

    if volume:
        if numero:
            referencia += f";{volume}({numero})"
        else:
            referencia += f";{volume}"
    if paginas:
        referencia += f":{paginas}"
    referencia += "."

    if doi:
        referencia += f" doi:{doi}."

    return referencia
