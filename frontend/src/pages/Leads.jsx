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
  const [q, setQ] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await api.getCustomers({ limit: 200 });
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

  async function remove(id, name) {
    if (!confirm(`Remover lead "${name}"? Isso apagará todas as conversas e mensagens.`)) return;
    try {
      await api.deleteCustomer(id);
      setLeads((prev) => prev.filter((c) => c.id !== id));
      setTotal((prev) => prev - 1);
    } catch (e) { setError(e.message); }
  }

  const ql = q.trim().toLowerCase();
  const filtered = leads.filter((c) => {
    if (!ql) return true;
    const hay = `${c.name || ""} ${c.phone || ""}`.toLowerCase();
    return hay.includes(ql);
  });

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <div>
            <h2>Leads</h2>
            <p className="muted">Todas as pessoas que entraram em contato pelo WhatsApp.</p>
          </div>
          <span className="muted" style={{ fontSize: 13 }}>{total} contatos</span>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="leads-search-row">
          <input
            className="leads-search"
            placeholder="Buscar por nome ou telefone..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
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
              <div key={c.id} className="lead-card">
                <div className="lead-card-top">
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
