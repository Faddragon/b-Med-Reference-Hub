import pytest
from src.formatador.vancouver import gerar_vancouver
from src.formatador.abnt import gerar_abnt


METADADOS_COMPLETOS = {
    "pmid": "12345",
    "titulo": "A randomized trial of statins in cardiovascular disease",
    "autores": ["Silva JA", "Santos RM", "Oliveira P"],
    "ano": "2023",
    "revista": "The Lancet",
    "volume": "401",
    "numero": "10387",
    "paginas": "1234-1245",
    "doi": "10.1016/S0140-6736(23)00123-4",
}


def test_vancouver_completo():
    ref = gerar_vancouver(METADADOS_COMPLETOS)
    assert "Silva JA, Santos RM, Oliveira P." in ref
    assert "A randomized trial of statins in cardiovascular disease." in ref
    assert "The Lancet." in ref
    assert "2023" in ref
    assert ";401(10387):1234-1245." in ref
    assert "doi:10.1016/S0140-6736(23)00123-4." in ref


def test_vancouver_sem_doi():
    dados = {**METADADOS_COMPLETOS, "doi": ""}
    ref = gerar_vancouver(dados)
    assert "doi:" not in ref


def test_vancouver_muitos_autores_trunca_em_seis():
    dados = {
        **METADADOS_COMPLETOS,
        "autores": [f"Author{i} X" for i in range(10)],
    }
    ref = gerar_vancouver(dados)
    assert "et al" in ref
    assert "Author0 X, Author1 X, Author2 X, Author3 X, Author4 X, Author5 X, et al." in ref


def test_vancouver_sem_autores():
    dados = {**METADADOS_COMPLETOS, "autores": []}
    ref = gerar_vancouver(dados)
    assert "Autores desconhecidos." in ref


def test_vancouver_sem_volume():
    dados = {**METADADOS_COMPLETOS, "volume": "", "numero": "", "paginas": ""}
    ref = gerar_vancouver(dados)
    assert ";" not in ref.split("doi:")[0] or ref.split(";")[-1].startswith("doi") or ref.endswith("2023.")


def test_abnt_completo():
    ref = gerar_abnt(METADADOS_COMPLETOS)
    assert "SILVA, J. A." in ref
    assert "SANTOS, R. M." in ref
    assert "OLIVEIRA, P." in ref
    assert "The Lancet" in ref
    assert "v. 401" in ref
    assert "n. 10387" in ref
    assert "p. 1234-1245" in ref
    assert "2023" in ref
    assert "Disponível em: https://doi.org/10.1016/S0140-6736(23)00123-4." in ref


def test_abnt_autor_unico_sem_iniciais():
    dados = {**METADADOS_COMPLETOS, "autores": ["WHO"]}
    ref = gerar_abnt(dados)
    assert "WHO." in ref


def test_abnt_sem_doi():
    dados = {**METADADOS_COMPLETOS, "doi": ""}
    ref = gerar_abnt(dados)
    assert "Disponível em" not in ref


def test_abnt_mais_de_tres_autores_usa_et_al():
    dados = {
        **METADADOS_COMPLETOS,
        "autores": ["Silva JA", "Santos RM", "Oliveira P", "Costa B", "Pereira L"],
    }
    ref = gerar_abnt(dados)
    assert "et al." in ref
    assert "COSTA" not in ref
    assert "PEREIRA" not in ref


def test_abnt_sem_autores():
    dados = {**METADADOS_COMPLETOS, "autores": []}
    ref = gerar_abnt(dados)
    assert "AUTORES DESCONHECIDOS." in ref
