(function () {
  "use strict";

  const $ = (sel, raiz = document) => raiz.querySelector(sel);
  const $$ = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));

  const painelResultado = $("#resultado");
  const painelStatus = $("#status");

  function mostrarStatus(msg, tipo = "carregando") {
    painelStatus.hidden = !msg;
    painelStatus.className = "status " + tipo;
    painelStatus.textContent = msg;
  }

  function limparStatus() {
    painelStatus.hidden = true;
    painelStatus.textContent = "";
  }

  function mostrarResultado(html) {
    painelResultado.hidden = false;
    painelResultado.innerHTML = html;
  }

  function limparResultado() {
    painelResultado.hidden = true;
    painelResultado.innerHTML = "";
  }

  function copiarTexto(texto, botao) {
    if (!navigator.clipboard) {
      const ta = document.createElement("textarea");
      ta.value = texto;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (_) {}
      document.body.removeChild(ta);
    } else {
      navigator.clipboard.writeText(texto);
    }
    if (botao) {
      const original = botao.textContent;
      botao.textContent = "Copiado!";
      botao.classList.add("copiado");
      setTimeout(() => {
        botao.textContent = original;
        botao.classList.remove("copiado");
      }, 1500);
    }
  }

  function blocoRef(titulo, texto) {
    return `
      <div class="bloco-ref">
        <div class="cabecalho">
          <span>${titulo}</span>
          <button class="botao-copiar" data-copiar>Copiar</button>
        </div>
        <div class="conteudo">${escapeHtml(texto)}</div>
      </div>
    `;
  }

  function detalhesJson(meta) {
    return `
      <details class="detalhes">
        <summary>Metadados estruturados (JSON)</summary>
        <pre>${escapeHtml(JSON.stringify(meta, null, 2))}</pre>
      </details>
    `;
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderArtigoUnico(meta, vancouver, abnt, rotulo) {
    mostrarResultado(`
      <h2>${escapeHtml(rotulo || "Artigo encontrado")}</h2>
      <p class="doi-info">PMID ${escapeHtml(meta.pmid || "?")} &middot; ${escapeHtml(meta.revista || "")}, ${escapeHtml(meta.ano || "")}</p>
      <p><strong>${escapeHtml(meta.titulo || "")}</strong></p>
      ${blocoRef("Vancouver", vancouver)}
      ${blocoRef("ABNT NBR 6023", abnt)}
      ${detalhesJson(meta)}
    `);
    $$("#resultado [data-copiar]").forEach((b) => {
      b.addEventListener("click", () => {
        const texto = b.closest(".bloco-ref").querySelector(".conteudo").textContent;
        copiarTexto(texto, b);
      });
    });
  }

  async function buscarJson(url, body) {
    limparResultado();
    mostrarStatus("Buscando no PubMed...");
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) {
        mostrarStatus(data.erro || "Erro desconhecido.", "erro");
        return null;
      }
      limparStatus();
      return data;
    } catch (e) {
      mostrarStatus("Falha de rede: " + e.message, "erro");
      return null;
    }
  }

  async function buscarDoi() {
    const doi = $("#input-doi").value.trim();
    if (!doi) { mostrarStatus("Informe um DOI.", "aviso"); return; }
    const data = await buscarJson("/api/buscar/doi", { doi });
    if (data) {
      renderArtigoUnico(data.metadados, data.vancouver, data.abnt, `DOI: ${doi}`);
    }
  }

  async function buscarPmid() {
    const pmid = $("#input-pmid").value.trim();
    if (!pmid) { mostrarStatus("Informe um PMID.", "aviso"); return; }
    const data = await buscarJson("/api/buscar/pmid", { pmid });
    if (data) {
      renderArtigoUnico(data.metadados, data.vancouver, data.abnt, `PMID: ${pmid}`);
    }
  }

  async function buscarTitulo() {
    const titulo = $("#input-titulo").value.trim();
    if (!titulo) { mostrarStatus("Informe um título.", "aviso"); return; }
    const lista = $("#lista-titulo");
    lista.hidden = true;
    lista.innerHTML = "";
    const data = await buscarJson("/api/buscar/titulo", { titulo });
    if (!data) return;
    if (!data.resultados || data.resultados.length === 0) {
      mostrarStatus(`Nenhum artigo encontrado para '${titulo}'.`, "aviso");
      return;
    }
    mostrarStatus(`${data.resultados.length} resultado(s). Escolha um:`, "sucesso");
    lista.hidden = false;
    data.resultados.forEach((r, idx) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="pmid">[${escapeHtml(r.pmid || "?")}]</div>
        <div class="titulo">${escapeHtml(r.titulo || "(sem título)")}</div>
        <div class="revista">${escapeHtml(r.revista || "")}, ${escapeHtml(r.ano || "")}</div>
      `;
      li.addEventListener("click", () => {
        renderArtigoUnico(r, r.vancouver, r.abnt, `Selecionado: ${r.titulo}`);
        lista.hidden = true;
      });
      lista.appendChild(li);
    });
    if (data.resultados.length === 1) {
      const r = data.resultados[0];
      renderArtigoUnico(r, r.vancouver, r.abnt, `Selecionado: ${r.titulo}`);
      lista.hidden = true;
    }
  }

  async function enviarPdf() {
    const input = $("#input-pdf");
    const arquivo = input.files[0];
    if (!arquivo) { mostrarStatus("Selecione um PDF.", "aviso"); return; }

    const fd = new FormData();
    fd.append("pdf", arquivo);
    limparResultado();
    mostrarStatus("Processando PDF...");

    try {
      const resp = await fetch("/api/upload", { method: "POST", body: fd });
      const data = await resp.json();
      if (resp.ok) {
        renderArtigoUnico(data.metadados, data.vancouver, data.abnt, `DOI extraído: ${data.doi_extraido}`);
        return;
      }
      if (resp.status === 422 && data.sugestoes) {
        mostrarResultado(`
          <h2>PDF processado</h2>
          <p><strong>${escapeHtml(data.info_pdf?.nome || "")}</strong> (${escapeHtml(String(data.info_pdf?.tamanho_kb || ""))} KB, ${escapeHtml(String(data.info_pdf?.paginas_total || ""))} páginas)</p>
          <p><strong>Preview:</strong> ${escapeHtml(data.preview || "(vazio)")}</p>
          <p class="status aviso">${escapeHtml(data.aviso || "Não foi possível extrair DOI.")}</p>
          <p>Informe manualmente:</p>
          <div class="linha">
            <input id="fallback-doi" type="text" placeholder="DOI (ex: 10.1234/abc)" />
            <button class="primario" id="fallback-doi-btn">Buscar por DOI</button>
          </div>
          <div class="linha" style="margin-top:8px">
            <input id="fallback-pmid" type="text" placeholder="PMID" />
            <button id="fallback-pmid-btn">Buscar por PMID</button>
          </div>
        `);
        limparStatus();
        $("#fallback-doi-btn").addEventListener("click", () => {
          $("#input-doi").value = $("#fallback-doi").value;
          $("#input-pmid").value = "";
          $$(".aba").forEach((b) => b.classList.remove("ativa"));
          $$('.aba[data-aba="doi"]')[0].classList.add("ativa");
          $$(".painel").forEach((p) => p.classList.remove("ativo"));
          $$('.painel[data-painel="doi"]')[0].classList.add("ativo");
          window.scrollTo({ top: 0 });
          buscarDoi();
        });
        $("#fallback-pmid-btn").addEventListener("click", () => {
          $("#input-pmid").value = $("#fallback-pmid").value;
          $$(".aba").forEach((b) => b.classList.remove("ativa"));
          $$('.aba[data-aba="pmid"]')[0].classList.add("ativa");
          $$(".painel").forEach((p) => p.classList.remove("ativo"));
          $$('.painel[data-painel="pmid"]')[0].classList.add("ativo");
          window.scrollTo({ top: 0 });
          buscarPmid();
        });
        return;
      }
      mostrarStatus(data.erro || "Erro desconhecido.", "erro");
    } catch (e) {
      mostrarStatus("Falha de rede: " + e.message, "erro");
    }
  }

  function trocarAba(aba) {
    $$(".aba").forEach((b) => b.classList.toggle("ativa", b.dataset.aba === aba));
    $$(".painel").forEach((p) => p.classList.toggle("ativo", p.dataset.painel === aba));
    limparStatus();
  }

  function configurarUpload() {
    const area = $("#area-upload");
    const input = $("#input-pdf");
    const preview = $("#preview-pdf");
    const botao = $('[data-acao="enviar-pdf"]');

    function handleArquivo(file) {
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        mostrarStatus("O arquivo precisa ter extensão .pdf.", "erro");
        botao.disabled = true;
        return;
      }
      const tamanhoKb = (file.size / 1024).toFixed(1);
      preview.hidden = false;
      preview.textContent = `${file.name} (${tamanhoKb} KB)`;
      botao.disabled = false;
    }

    input.addEventListener("change", () => handleArquivo(input.files[0]));
    area.addEventListener("click", (e) => {
      if (e.target === input || e.target === area || e.target.classList.contains("dica")) {
        input.click();
      }
    });
    area.addEventListener("dragover", (e) => { e.preventDefault(); area.classList.add("dragover"); });
    area.addEventListener("dragleave", () => area.classList.remove("dragover"));
    area.addEventListener("drop", (e) => {
      e.preventDefault();
      area.classList.remove("dragover");
      const f = e.dataTransfer.files[0];
      if (f) {
        const dt = new DataTransfer();
        dt.items.add(f);
        input.files = dt.files;
        handleArquivo(f);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    $$(".aba").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.aba)));
    $('[data-acao="buscar-doi"]').addEventListener("click", buscarDoi);
    $('[data-acao="buscar-pmid"]').addEventListener("click", buscarPmid);
    $('[data-acao="buscar-titulo"]').addEventListener("click", buscarTitulo);
    $('[data-acao="enviar-pdf"]').addEventListener("click", enviarPdf);
    $("#input-doi").addEventListener("keydown", (e) => { if (e.key === "Enter") buscarDoi(); });
    $("#input-pmid").addEventListener("keydown", (e) => { if (e.key === "Enter") buscarPmid(); });
    $("#input-titulo").addEventListener("keydown", (e) => { if (e.key === "Enter") buscarTitulo(); });
    configurarUpload();
  });
})();
