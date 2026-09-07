import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

function formatPhone(p) {
  const d = (p || "").replace(/\D/g, "");
  if (d.length === 13) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 9)}-${d.slice(9)}`;
  if (d.length === 12) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 8)}-${d.slice(8)}`;
  return d;
}

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "agora";
  if (diff < 3600) return `${Math.round(diff / 60)}min`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h`;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

const AVATAR_COLORS = ["#4f7cff", "#8b5cf6", "#06b6d4", "#22c55e", "#f59e0b", "#ec4899"];
function avatarColor(seed) {
  let h = 0;
  for (const ch of String(seed || "")) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(new Set());
  const [showBulk, setShowBulk] = useState(false);
  const [bulkText, setBulkText] = useState("");
  const [sending, setSending] = useState(false);
  const [showExport, setShowExport] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await api.getCustomers({ limit: 500 });
        if (!active) return;
        setLeads(res.items || []);
        setTotal(res.total || 0);
        setError("");
      } catch (e) {
        if (active) setError(e.message || "Erro ao carregar leads");
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  const ql = q.trim().toLowerCase();
  const filtered = leads.filter((c) => {
    if (!ql) return true;
    const hay = `${c.name || ""} ${c.phone || ""}`.toLowerCase();
    return hay.includes(ql);
  });

  function toggleSelect(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((c) => c.id)));
    }
  }

  async function remove(id, name) {
    if (!confirm(`Remover lead "${name}"? Isso apagará todas as conversas e mensagens.`)) return;
    try {
      await api.deleteCustomer(id);
      setLeads((prev) => prev.filter((c) => c.id !== id));
      setTotal((prev) => prev - 1);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
    } catch (e) { setError(e.message); }
  }

  function exportLeads(format) {
    api.exportCustomers(format);
    setShowExport(false);
  }

  async function sendBulk() {
    const text = bulkText.trim();
    if (!text) return;
    setSending(true);
    setError("");
    setSuccess("");
    try {
      const ids = selected.size > 0 ? [...selected] : undefined;
      const res = await api.bulkMessageCustomers({
        text,
        ...(ids ? { customer_ids: ids } : { all: true }),
      });
      setSuccess(res.message || "Mensagem enviada");
      setBulkText("");
      setShowBulk(false);
      setSelected(new Set());
    } catch (e) {
      setError(e.message || "Erro ao enviar");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <div>
            <h2>Leads</h2>
            <p className="muted">Todas as pessoas que entraram em contato pelo WhatsApp.</p>
          </div>
          <div className="leads-actions">
            <span className="muted" style={{ fontSize: 13 }}>{total} contatos</span>
            <div className="dropdown-wrap">
              <button className="btn ghost small" onClick={() => setShowExport(!showExport)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Exportar
              </button>
              {showExport && (
                <div className="dropdown-menu">
                  <button onClick={() => exportLeads("json")}>JSON</button>
                  <button onClick={() => exportLeads("xlsx")}>Excel (.xlsx)</button>
                </div>
              )}
            </div>
            {selected.size > 0 && (
              <button className="btn primary small" onClick={() => setShowBulk(true)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
                Enviar para {selected.size}
              </button>
            )}
            <button className="btn primary small" onClick={() => setShowBulk(true)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              Mensagem em massa
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}

        {showBulk && (
          <div className="card" style={{ maxWidth: 600, marginBottom: 16 }}>
            <h3>Mensagem em Massa</h3>
            <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
              {selected.size > 0
                ? `Enviando para ${selected.size} leads selecionados`
                : "Enviando para TODOS os leads"}
            </p>
            <textarea
              className="input"
              rows="4"
              placeholder="Digite a mensagem que deseja enviar..."
              value={bulkText}
              onChange={(e) => setBulkText(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn primary" onClick={sendBulk} disabled={!bulkText.trim() || sending}>
                {sending ? "Enviando..." : "Enviar"}
              </button>
              <button className="btn ghost" onClick={() => { setShowBulk(false); setBulkText(""); }}>Cancelar</button>
            </div>
          </div>
        )}

        <div className="leads-search-row">
          <input
            className="leads-search"
            placeholder="Buscar por nome ou telefone..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {filtered.length > 0 && (
            <label className="leads-select-all">
              <input
                type="checkbox"
                checked={selected.size === filtered.length && filtered.length > 0}
                onChange={selectAll}
              />
              Selecionar todos ({filtered.length})
            </label>
          )}
        </div>

        {loading ? (
          <div className="leads-loading">
            <div className="inbox-spinner" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            <p>{ql ? "Nenhum lead encontrado para esta busca." : "Nenhum lead ainda."}</p>
            <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
              {!ql && "Leads são salvos automaticamente quando enviam mensagem pelo WhatsApp."}
            </p>
          </div>
        ) : (
          <div className="leads-grid">
            {filtered.map((c) => (
              <div key={c.id} className={`lead-card ${selected.has(c.id) ? "lead-card-selected" : ""}`}>
                <div className="lead-card-top">
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={() => toggleSelect(c.id)}
                    className="lead-checkbox"
                  />
                  <div className="lead-avatar" style={{ background: avatarColor(c.name || c.phone) }}>
                    {(c.name || c.phone || "?").slice(0, 1).toUpperCase()}
                  </div>
                  <div className="lead-info">
                    <span className="lead-name">{c.name || "Sem nome"}</span>
                    <span className="lead-phone">{formatPhone(c.phone)}</span>
                  </div>
                </div>
                <div className="lead-card-bottom">
                  <span className="lead-conversations">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    {c.conversation_count} {c.conversation_count === 1 ? "conversa" : "conversas"}
                  </span>
                  <button className="btn danger ghost small" onClick={() => remove(c.id, c.name || c.phone)} title="Remover lead">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
