(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  const state = {
    method: "hybrid",
    hits: [],
    lastPayload: null,
    lastLatency: null,
  };

  const api = async (url, options = {}) => {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
    return data;
  };

  const escapeHtml = (value = "") => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const formatNumber = (value) => {
    if (value === undefined || value === null || Number.isNaN(Number(value))) return "—";
    return Number(value).toLocaleString("en-US");
  };

  const normalizeHit = (hit, index) => {
    const chunk = hit.chunk || hit.document || hit;
    const score = Number(hit.score ?? hit.final_score ?? hit.rerank_score ?? hit.bm25_score ?? chunk.score ?? 0);
    return {
      rank: index + 1,
      chunkId: chunk.chunk_id || hit.chunk_id || `C${index + 1}`,
      title: chunk.title || hit.title || chunk.doc_id || `Evidence ${index + 1}`,
      source: chunk.source_path || hit.source_path || chunk.source || chunk.doc_id || "unknown source",
      section: chunk.section || hit.section || "",
      pageStart: chunk.page_start ?? hit.page_start ?? "",
      pageEnd: chunk.page_end ?? hit.page_end ?? "",
      text: chunk.text || hit.text || hit.snippet || "",
      score: Number.isFinite(score) ? score : 0,
    };
  };

  const currentConfig = () => ({
    query: $("#queryInput").value.trim(),
    method: state.method,
    top_k: Number($("#topK").value),
    candidate_k: Number($("#candidateK").value),
    use_model: $("#useModel").checked,
    model: $("#modelSelect").value,
  });

  const toast = (message) => {
    const node = document.createElement("div");
    node.className = "toast";
    node.textContent = message;
    document.body.appendChild(node);
    setTimeout(() => node.remove(), 2200);
  };

  const setBusy = (busy) => {
    $("#runBtn").disabled = busy;
    $("#rebuildBtn").disabled = busy;
    $("#runBtn").textContent = busy ? "Running…" : "▶ Run";
  };

  const renderProfile = (profile = {}) => {
    $("#fileCount").textContent = formatNumber(profile.file_count ?? profile.files?.length);
    $("#chunkCount").textContent = formatNumber(profile.chunk_count);
    $("#avgChunk").textContent = `Avg. ${formatNumber(profile.avg_chunk_tokens)} tokens`;
    $("#profileUpdated").textContent = profile.chunk_count ? "Index loaded" : "No index yet";
    $("#corpusStatus").textContent = (profile.file_count || profile.files?.length) ? "Corpus Ready" : "No Corpus";
    $("#indexStatus").textContent = profile.chunk_count ? "Index Built" : "Index Empty";
  };

  const renderAnswer = (data = {}) => {
    let answer = data.answer || data.response || data.output || "未返回答案。";
    const showCitations = $("#showCitations").checked;
    let html = escapeHtml(answer);
    if (showCitations) {
      html = html.replace(/\[(C?\d+)\]/g, '<span class="citation">[$1]</span>');
    }
    $("#answerBox").classList.remove("muted-block");
    $("#answerBox").innerHTML = html;
  };

  const renderTrace = (trace = {}, latency = null) => {
    const showTrace = $("#showTrace").checked;
    $("#timelineCard").style.display = showTrace ? "block" : "none";
    $("#debugCard").style.display = showTrace ? "block" : "none";

    const traceObj = trace || {};
    const steps = [
      ["rewrite", traceObj.rewrite_ms ?? traceObj.query_rewrite_ms],
      ["retrieve", traceObj.retrieve_ms ?? traceObj.search_ms ?? traceObj.retrieval_ms],
      ["rerank", traceObj.rerank_ms],
      ["answer", traceObj.answer_ms ?? traceObj.generate_ms],
    ];
    $("#traceChips").innerHTML = steps.map(([name, ms]) =>
      `<span class="chip">${name}<small>${ms === undefined ? "done" : `${Math.round(ms)} ms`}</small></span>`
    ).join("");

    $("#rewriteMs").textContent = steps[0][1] === undefined ? "done" : `${Math.round(steps[0][1])} ms`;
    $("#retrieveMs").textContent = steps[1][1] === undefined ? "done" : `${Math.round(steps[1][1])} ms`;
    $("#rerankMs").textContent = steps[2][1] === undefined ? "done" : `${Math.round(steps[2][1])} ms`;
    $("#answerMs").textContent = steps[3][1] === undefined ? "done" : `${Math.round(steps[3][1])} ms`;
    $("#totalLatency").textContent = latency ? `Total ${Math.round(latency)} ms` : "Total — ms";
    $("#debugTrace").textContent = JSON.stringify(traceObj, null, 2);
  };

  const renderEvidence = (hits = []) => {
    state.hits = hits.map(normalizeHit);
    const keyword = $("#evidenceFilter").value.trim().toLowerCase();
    const filtered = state.hits.filter(h => !keyword || `${h.title} ${h.source} ${h.text}`.toLowerCase().includes(keyword));
    $("#evidenceTitleCount").textContent = `Top ${Math.max(1, Number($("#topK").value))}`;
    $("#evidenceCount").textContent = `${filtered.length} results`;

    if (!filtered.length) {
      $("#evidenceList").className = "evidence-list empty-state";
      $("#evidenceList").textContent = hits.length ? "没有匹配筛选条件的证据。" : "等待检索证据。";
      return;
    }

    const maxScore = Math.max(...filtered.map(h => h.score), 1e-6);
    $("#evidenceList").className = "evidence-list";
    $("#evidenceList").innerHTML = filtered.map((h) => {
      const scoreText = h.score ? h.score.toFixed(3).replace(/0+$/, "").replace(/\.$/, "") : "—";
      const width = Math.max(10, Math.min(100, Math.round((h.score / maxScore) * 100)));
      const pageText = h.pageStart !== "" ? `P.${h.pageStart}${h.pageEnd && h.pageEnd !== h.pageStart ? `-${h.pageEnd}` : ""}` : "Chunk";
      const snippet = escapeHtml(h.text.slice(0, 230)).replaceAll(escapeHtml(currentConfig().query).slice(0, 24), `<mark>${escapeHtml(currentConfig().query).slice(0, 24)}</mark>`);
      return `
        <article class="evidence-item">
          <div class="evidence-top">
            <span class="rank">${h.rank}</span>
            <h3 class="evidence-title">${escapeHtml(h.title)}</h3>
            <span class="score">${scoreText}</span>
          </div>
          <p class="source">${escapeHtml(h.source)} ${h.section ? ` · ${escapeHtml(h.section)}` : ""}</p>
          <p class="snippet">${snippet}${h.text.length > 230 ? "…" : ""}</p>
          <div class="evidence-actions">
            <span class="tag">PDF</span>
            <span class="tag">${escapeHtml(pageText)}</span>
            <span class="tag">${escapeHtml(h.chunkId)}</span>
            <div class="scorebar"><span style="width:${width}%"></span></div>
          </div>
        </article>`;
    }).join("");
  };

  const renderMetrics = (data = {}, latency = null) => {
    const metrics = data.metrics || data.evaluation || {};
    $("#metricLatency").textContent = latency ? Math.round(latency) : "—";
    $("#metricRecall").textContent = metrics.recall_at_5 ?? metrics.recall5 ?? "—";
    $("#metricCitation").textContent = metrics.citation_accuracy ?? metrics.citation_acc ?? "—";
  };

  const loadProfile = async () => {
    try {
      const profile = await api("/api/profile");
      renderProfile(profile);
    } catch (err) {
      renderProfile({});
      console.warn(err);
    }
  };

  const runQuery = async () => {
    const payload = currentConfig();
    if (!payload.query) {
      toast("请先输入问题");
      return;
    }
    state.lastPayload = payload;
    setBusy(true);
    const started = performance.now();
    try {
      const data = await api("/api/query", { method: "POST", body: JSON.stringify(payload) });
      const latency = performance.now() - started;
      state.lastLatency = latency;
      renderAnswer(data);
      renderTrace(data.trace, latency);
      renderEvidence(data.hits || data.evidence || []);
      renderMetrics(data, latency);
    } catch (err) {
      $("#answerBox").classList.add("muted-block");
      $("#answerBox").textContent = `请求失败：${err.message}`;
      toast("查询失败，请看 Debug Trace");
      renderTrace({ error: err.message }, performance.now() - started);
    } finally {
      setBusy(false);
    }
  };

  const rebuildIndex = async () => {
    setBusy(true);
    try {
      const data = await api("/api/rebuild", { method: "POST", body: JSON.stringify({ chunk_size: 900, overlap: 150 }) });
      toast(`索引已重建：${data.chunk_count ?? "—"} chunks`);
      await loadProfile();
    } catch (err) {
      toast(`重建失败：${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  const bindEvents = () => {
    $$("#methodGroup button").forEach(btn => {
      btn.addEventListener("click", () => {
        $$("#methodGroup button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.method = btn.dataset.method;
      });
    });

    [["#topK", "#topKValue"], ["#candidateK", "#candidateKValue"]].forEach(([input, output]) => {
      $(input).addEventListener("input", () => { $(output).textContent = $(input).value; });
    });

    $("#runBtn").addEventListener("click", runQuery);
    $("#queryInput").addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runQuery();
    });
    $("#clearBtn").addEventListener("click", () => { $("#queryInput").value = ""; $("#queryInput").focus(); });
    $("#copyBtn").addEventListener("click", async () => {
      await navigator.clipboard?.writeText($("#answerBox").innerText || "");
      toast("答案已复制");
    });
    $("#rebuildBtn").addEventListener("click", rebuildIndex);
    $("#evidenceFilter").addEventListener("input", () => renderEvidence(state.hits));
    $("#showTrace").addEventListener("change", () => renderTrace(JSON.parse($("#debugTrace").textContent || "{}"), state.lastLatency));
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    loadProfile();
    renderTrace({}, null);
  });
})();
