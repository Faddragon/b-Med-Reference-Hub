# b-Med Reference Hub

CLI em Python para mapear e formatar referências biomédicas a partir do PubMed (via NCBI Entrez) ou de PDFs locais, com saída nos padrões **Vancouver** e **ABNT NBR 6023**.

## Funcionalidades

- Busca de metadados por **DOI**, **PMID** ou **título** na API do PubMed.
- Busca por **título retorna top-5** com seleção interativa (antes pegava só o 1º).
- **Cache SQLite** local com TTL de 24h para evitar chamadas repetidas à API.
- **Rate limiter** embutido: 3 req/s sem API key, 10 req/s com API key.
- **Retry automático** com backoff exponencial para HTTP 429/5xx e erros de rede.
- Extração de **DOI** a partir de PDF local (PyMuPDF) e lookup automático.
- Formatação de saída em **Vancouver** (estrito, com `doi:`) e **ABNT NBR 6023** (com `SOBRENOME, N.` e `Disponível em:`).
- Arquivamento do PDF em `data/pdfs_armazenados/`.

## Estrutura

```
src/
  main.py                      # CLI com seleção interativa
  config.py                    # caminhos, credenciais Entrez, TTL, retry
  formatador/
    vancouver.py
    abnt.py
  motor_extracao/
    pubmed_api.py              # esearch/efetch + cache + retry + rate limit
    validador_doi.py           # regex para extrair DOI
    pdf_handler.py             # leitura de PDF
    retry.py                   # decorator com_retry, RateLimiter, exceções
  db/
    cache.py                   # SQLite com TTL
  web/
    app.py                     # Flask app (interface web)
    templates/index.html
    static/style.css
    static/app.js
tests/
  test_formatadores.py
  test_pubmed.py               # inclui cache, top-N, PMID
  test_cache.py
  test_retry.py
  test_pdf_handler.py
  test_web.py
data/
  cache.sqlite                 # cache local
  pdfs_armazenados/            # PDFs arquivados
```

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

### Configuração do NCBI Entrez

O NCBI exige um e-mail real e (opcionalmente) uma [API key](https://www.ncbi.nlm.nih.gov/account/settings/) para uso do Entrez. Defina via variáveis de ambiente:

```bash
# Windows PowerShell
$env:BMED_ENTREZ_EMAIL = "voce@instituicao.edu"
$env:BMED_ENTREZ_API_KEY = "sua_api_key_aqui"

# Linux/macOS
export BMED_ENTREZ_EMAIL="voce@instituicao.edu"
export BMED_ENTREZ_API_KEY="sua_api_key_aqui"
```

Sem API key: 3 req/s. Com API key: 10 req/s.

## Uso

```bash
python -m src.main
```

Menu interativo:

```
1. Buscar artigo por DOI         -> 10.1016/S0140-6736(23)00123-4
2. Buscar artigo por Título      -> statins cardiovascular randomized
3. Buscar artigo por PMID         -> 37812345
4. Processar PDF local           -> C:/artigos/meu_paper.pdf
0. Sair
```

Na opção 2, quando há múltiplos resultados, você vê a lista e escolhe:

```
Foram encontrados 5 artigos. Escolha um:
  1. [37812345] Statins in primary prevention - Lancet, 2023
  2. [37123456] Statins and cardiovascular outcomes - NEJM, 2022
  ...
Digite 1-5 (ou 0 para cancelar): >
```

## Interface web

```bash
python -m src.web.app
```

Abre em <http://127.0.0.1:5000> com 4 abas (DOI, PMID, Título, PDF), botões de cópia para cada formato e fallback automático quando o PDF não tem DOI extraível.

## Exemplo de saída

**Vancouver**
```
Doe J, Roe A, et al. A study of mock data. Journal of Tests. 2024;12(3):10-20. doi:10.1234/test.2024.001.
```

**ABNT**
```
DOE, J.; ROE, A., et al. A study of mock data. Journal of Tests, v. 12, n. 3, p. 10-20, 2024. Disponível em: https://doi.org/10.1234/test.2024.001.
```

## Testes

```bash
pytest
```

**66 testes** rodando offline graças a mocks de `Entrez.esearch`, `Entrez.efetch`, `Entrez.read` e banco de cache isolado por `tmp_path`.

## Tratamento de erros

A camada `retry.py` define exceções específicas:

- `PubMedError` — base
- `PubMedRateLimited` — HTTP 429 mesmo após retries
- `PubMedNetworkError` — DNS, timeout, conexão
- `PubMedNotFound` — para uso futuro em chamadas sem resultado

O CLI captura tudo e exibe mensagem amigável; o `com_retry` decorator lida com retries transparentemente (max 3, backoff 1s/2s/4s).

## Limitações conhecidas

- O **local de publicação** exigido pela ABNT para artigos impressos não é retornado pelo PubMed — só incluímos `Disponível em:` quando há DOI.
- A camada `db/` original (placeholder `database.sqlite`) ainda não foi implementada — apenas `cache.sqlite` é usada.
- O PDF handler lê no máximo 3 páginas para extrair DOI (heurística simples).

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `BMED_ENTREZ_EMAIL` | `seu_email_medico@exemplo.com` | E-mail exigido pelo NCBI |
| `BMED_ENTREZ_API_KEY` | `""` | API key do NCBI (opcional, libera 10 req/s) |
