# b-Med Reference Hub 🧬

![Banner b-Med Reference Hub](imagem%20github.png)

![GitHub repo size](https://img.shields.io/github/repo-size/Faddragon/b-Med-Reference-Hub)
![GitHub top language](https://img.shields.io/github/languages/top/Faddragon/b-Med-Reference-Hub)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> **Uma plataforma moderna (Web & CLI) para mapear e extrair referências biomédicas de PDFs e da API do PubMed, entregando citações prontas nos padrões Vancouver estrito e ABNT NBR 6023.**

O **b-Med Reference Hub** foi projetado para economizar horas de formatação manual de médicos, pesquisadores e acadêmicos. Ele automatiza a extração de metadados e oferece uma interface web premium, rica e interativa, baseada nos conceitos de *Glassmorphism*.

---

## ✨ Principais Funcionalidades

- **Múltiplas Formas de Busca:** Pesquise artigos instantaneamente através de DOI, PMID ou até mesmo Título (com suporte a busca top-5 interativa).
- **Extração Inteligente de PDFs:** Envie um PDF local e a ferramenta usará o `PyMuPDF` para escanear as primeiras páginas, identificar o DOI de forma autônoma e cruzar com os dados oficiais do PubMed.
- **Saídas Precisas (ABNT & Vancouver):** Formata os autores (incluindo caixa alta para ABNT), periódicos e inclusão automática de links rastreáveis do DOI.
- **Interface Premium (Web App):** Desenhada em Vanilla CSS moderno com paletas em HSL, tipografia Google Fonts (Inter e Outfit) e micro-interações dinâmicas.
- **Resiliência e Cache:** Rate limiter inteligente (até 10 req/s), cache em SQLite (TTL 24h) e sistema embutido de _Retry_ (Backoff Exponencial) para evitar bloqueios temporários.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.10+, Flask, SQLite (para Cache/DB).
- **Processamento:** BioPython (Entrez API) e PyMuPDF (Manipulação de Arquivos).
- **Frontend Web:** HTML5 Semântico, Vanilla CSS (Glassmorphism), Vanilla JavaScript (Fetch API).
- **Integrações Oficiais:** NCBI Entrez / PubMed API.

---

## 🚀 Como Rodar Localmente

Certifique-se de ter o Python instalado na sua máquina.

**1. Clone o repositório:**
```bash
git clone https://github.com/Faddragon/b-Med-Reference-Hub.git
cd b-Med-Reference-Hub
```

**2. Crie e ative o ambiente virtual (Recomendado):**
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

**3. Instale as dependências:**
```bash
pip install -r requirements.txt
```

**4. Inicie o Servidor Web Premium:**
```bash
python -m src.web.app
```
Após executar, abra o navegador e acesse: `http://127.0.0.1:5000`

> **Nota:** Se preferir a experiência "Raiz" em linha de comando, basta rodar `python -m src.main`.

---

## ☁️ Como Hospedar (Deploy)

Como o projeto utiliza bancos de dados locais (SQLite) e armazena PDFs no disco, recomenda-se hospedar em plataformas que suportem volumes persistentes.

- **[Render](https://render.com/) (Recomendado):** Super fácil de conectar com o GitHub e suporta discos persistentes em planos pagos (o plano gratuito funciona perfeitamente para testes de front-end).
- **[PythonAnywhere](https://www.pythonanywhere.com/):** A melhor opção para hospedar gratuitamente um script Python + SQLite de forma persistente.
- **[Railway](https://railway.app/) ou [Fly.io](https://fly.io/):** Ideais para deploys modernos via Docker.

---

## ⚙️ Configurações (Opcional, mas recomendado)

O PubMed exige um E-mail real para requisições seguras à API. Você pode exportar variáveis de ambiente para o terminal antes de rodar o app:

```bash
# Windows PowerShell
$env:BMED_ENTREZ_EMAIL = "seu.email@instituicao.edu"
$env:BMED_ENTREZ_API_KEY = "sua_api_key_do_pubmed"

# Linux / MacOS
export BMED_ENTREZ_EMAIL="seu.email@instituicao.edu"
export BMED_ENTREZ_API_KEY="sua_api_key_do_pubmed"
```
*(Se você fornecer uma API Key do NCBI, seu limite sobe de 3 para 10 requisições por segundo).*

---

## 🧪 Rodando os Testes

A aplicação possui excelente cobertura de testes (_offline mocking_) cobrindo formatadores, cache e limites de requisição.

```bash
pytest
```

---
*Feito para simplificar a pesquisa médica.* 🩺
