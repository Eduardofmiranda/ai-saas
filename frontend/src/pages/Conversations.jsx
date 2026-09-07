import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../api";
import Header from "../components/Header";

const POLL_MS = 5000;

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "agora";
  if (diff < 3600) return `${Math.round(diff / 60)}min`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h`;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function timeHM(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function dateLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 86400000 && d.getDate() === now.getDate()) return "Hoje";
  if (diff < 172800000 && d.getDate() === now.getDate() - 1) return "Ontem";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatPhone(p) {
  const d = (p || "").replace(/\D/g, "");
  if (d.length === 13) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 9)}-${d.slice(9)}`;
  if (d.length === 12) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 8)}-${d.slice(8)}`;
  return d;
}

const COLORS = ["#4f7cff", "#8b5cf6", "#06b6d4", "#22c55e", "#f59e0b", "#ec4899"];
function avatarColor(seed) {
  let h = 0;
  for (const ch of String(seed || "")) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return COLORS[h % COLORS.length];
}

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState(null);
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [composerError, setComposerError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const sendingRef = useRef(false);

  const selectedConv = conversations.find((c) => c.id === selected) || null;

  // Polling: lista de conversas (sempre)
  useEffect(() => {
    let active = true;
    async function tick() {
      try {
        const res = await api.getConversations();
        if (!active) return;
        setConversations(res.items || []);
        setError("");
      } catch (e) {
        if (active) setError(e.message || "Erro ao carregar conversas");
      }
    }
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Polling: mensagens da conversa selecionada
  useEffect(() => {
    if (!selected) { setMessages(null); return; }
    let active = true;
    async function tick() {
      try {
        const msgRes = await api.getConversationMessages(selected);
        if (!active) return;
        setMessages(msgRes.items || []);
      } catch (e) {
        if (active) setError(e.message || "Erro ao carregar mensagens");
      }
    }
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => { active = false; clearInterval(id); };
  }, [selected]);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ block: "end" });
  }, [messages]);

  const select = useCallback((id) => {
    setSelected(id);
    setMessages(null);
    setComposerError("");
  }, []);

  const sendReply = useCallback(async () => {
    const content = draft.trim();
    if (!content || !selected || sendingRef.current) return;
    sendingRef.current = true;
    setComposerError("");

    // Optimistic: adiciona mensagem imediatamente
    const tempId = `temp-${Date.now()}`;
    setMessages((prev) => [...(prev || []), { id: tempId, sender_type: "agent", content, created_at: new Date().toISOString() }]);
    setDraft("");
    inputRef.current?.focus();

    try {
      // Reply é fire-and-forget: retorna instantaneamente
      await api.replyToConversation(selected, content);
      // Nao precisa re-fetch: o optimistic update ja mostrou a mensagem
      // O proximo poll de messages vai buscar a versao real do banco
    } catch (e) {
      // Remove optimistic message em caso de erro
      setMessages((prev) => (prev || []).filter((m) => m.id !== tempId));
      setComposerError(e.message || "Falha ao enviar");
    } finally {
      sendingRef.current = false;
    }
  }, [draft, selected]);

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendReply(); }
  }

  async function toggleStatus() {
    if (!selectedConv) return;
    const next = selectedConv.status === "pending_agent" ? "open" : selectedConv.status === "open" ? "closed" : selectedConv.status === "agent" ? "open" : "open";
    try {
      await api.updateConversation(selectedConv.id, { status: next });
      // Poll vai atualizar
    } catch (e) { setError(e.message); }
  }

  async function assumeConversation() {
    if (!selectedConv) return;
    try {
      await api.assumeConversation(selectedConv.id);
      // Poll vai atualizar
    } catch (e) { setError(e.message); }
  }

  const ql = q.trim().toLowerCase();
  const filtered = conversations.filter((c) => {
    if (tab === "open" && c.status !== "open") return false;
    if (tab === "pending" && c.status !== "pending_agent") return false;
    if (tab === "agent" && c.status !== "agent") return false;
    if (tab === "closed" && c.status !== "closed") return false;
    if (ql) {
      const hay = `${c.customer?.name || ""} ${c.customer?.phone || ""}`.toLowerCase();
      if (!hay.includes(ql)) return false;
    }
    return true;
  });

  const counts = {
    all: conversations.length,
    open: conversations.filter((c) => c.status === "open").length,
    pending: conversations.filter((c) => c.status === "pending_agent").length,
    agent: conversations.filter((c) => c.status === "agent").length,
    closed: conversations.filter((c) => c.status === "closed").length,
  };

  return (
    <div className="layout">
      <Header />
      <main className="content inbox-content">
        {error && <div className="error">{error}</div>}
        <div className="inbox-layout">
          <aside className="inbox-list">
            <div className="inbox-toolbar">
              <input
                className="inbox-search"
                placeholder="Buscar..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <div className="inbox-filters">
                {[["all", "Todas"], ["open", "Abertas"], ["pending", "Aguardando"], ["agent", "Atendendo"], ["closed", "Fechadas"]].map(([key, label]) => (
                  <button
                    key={key}
                    className={`inbox-filter ${tab === key ? "active" : ""}`}
                    onClick={() => setTab(key)}
                  >
                    {label}
                    {counts[key] > 0 && <span className="inbox-filter-count">{counts[key]}</span>}
                  </button>
                ))}
              </div>
            </div>
            <div className="inbox-items">
              {conversations.length === 0 ? (
                <div className="empty-inbox">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  <p>Nenhuma conversa ainda</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="empty-inbox"><p>Nenhuma conversa para este filtro.</p></div>
              ) : (
                filtered.map((c) => {
                  const name = c.customer?.name || c.customer?.phone || `#${c.id}`;
                  return (
                    <div key={c.id} className={`inbox-item ${selected === c.id ? "selected" : ""}`} onClick={() => select(c.id)}>
                      <div className="inbox-avatar" style={{ background: avatarColor(name) }}>{name.slice(0, 1).toUpperCase()}</div>
                      <div className="inbox-item-body">
                        <div className="inbox-item-top">
                          <span className="inbox-item-name">{name}</span>
                          <span className="inbox-item-time">{relativeTime(c.last_message_at || c.updated_at)}</span>
                        </div>
                        <div className="inbox-item-bottom">
                          <span className="inbox-item-preview">{c.last_message || "Sem mensagens"}</span>
                          <span className={`inbox-status-dot inbox-status-dot-${c.status}`} />
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </aside>

          <section className="inbox-thread">
            {selectedConv ? (
              <>
                <header className="inbox-thread-head">
                  <div className="inbox-thread-info">
                    <div className="inbox-thread-avatar" style={{ background: avatarColor(selectedConv.customer?.name) }}>
                      {(selectedConv.customer?.name || "?").slice(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <strong>{selectedConv.customer?.name || selectedConv.customer?.phone || "Conversa"}</strong>
                      <span className="inbox-thread-phone">{formatPhone(selectedConv.customer?.phone)}</span>
                    </div>
                  </div>
                  <div className="inbox-thread-actions">
                    {selectedConv.status === "pending_agent" && (
                      <button className="btn primary small" onClick={assumeConversation}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                        Assumir
                      </button>
                    )}
                    {selectedConv.status === "agent" && (
                      <button className="btn ghost small" onClick={toggleStatus}>Liberar</button>
                    )}
                    <button className="btn ghost small" onClick={toggleStatus}>
                      {selectedConv.status === "closed" ? "Reabrir" : "Fechar"}
                    </button>
                  </div>
                </header>

                <div className="inbox-msgs">
                  {messages === null ? (
                    <div className="inbox-loading"><div className="inbox-spinner" /></div>
                  ) : messages.length === 0 ? (
                    <div className="inbox-empty-thread"><p>Nenhuma mensagem ainda.</p></div>
                  ) : (
                    (() => {
                      let lastDate = "";
                      return messages.map((m, i) => {
                        const msgDate = dateLabel(m.created_at);
                        const showDate = msgDate !== lastDate;
                        lastDate = msgDate;
                        const isCustomer = m.sender_type === "customer";
                        const isBot = m.sender_type === "bot";
                        const bubbleType = isCustomer ? "client" : isBot ? "bot" : "agent";
                        const showLabel = !isCustomer && (i === 0 || messages[i - 1]?.sender_type !== m.sender_type);
                        return (
                          <div key={m.id} className="inbox-msg-group">
                            {showDate && <div className="inbox-date-sep"><span>{msgDate}</span></div>}
                            {showLabel && <div className={`inbox-sender-label inbox-sender-${bubbleType}`}>{isBot ? "Bot" : "Atendente"}</div>}
                            <div className={`bubble ${bubbleType}`}>
                              <div className="bubble-text">{m.content}</div>
                              <div className="bubble-time">{timeHM(m.created_at)}</div>
                            </div>
                          </div>
                        );
                      });
                    })()
                  )}
                  <div ref={endRef} />
                </div>

                <div className="inbox-composer">
                  <textarea
                    ref={inputRef}
                    className="inbox-input"
                    rows="1"
                    placeholder={selectedConv.status === "closed" ? "Conversa fechada..." : "Digite sua resposta..."}
                    value={draft}
                    disabled={selectedConv.status === "closed"}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={onKeyDown}
                  />
                  <button className="btn primary inbox-send-btn" onClick={sendReply} disabled={!draft.trim() || selectedConv.status === "closed"}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                  </button>
                </div>
                {composerError && <div className="error" style={{ margin: "0 12px 8px" }}>{composerError}</div>}
              </>
            ) : (
              <div className="inbox-placeholder">
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h3>Atendimento WhatsApp</h3>
                <p className="muted">Selecione uma conversa para responder.</p>
              </div>
            )}
          </section>

          <aside className="inbox-context">
            {selectedConv ? (
              <>
                <div className="inbox-ctx-section">
                  <div className="inbox-ctx-head">Cliente</div>
                  <div className="inbox-ctx-row"><span className="inbox-ctx-label">Nome</span><span className="inbox-ctx-value">{selectedConv.customer?.name || "—"}</span></div>
                  <div className="inbox-ctx-row"><span className="inbox-ctx-label">Telefone</span><span className="inbox-ctx-value">{formatPhone(selectedConv.customer?.phone)}</span></div>
                </div>
                <div className="inbox-ctx-section">
                  <div className="inbox-ctx-head">Conversa</div>
                  <div className="inbox-ctx-row">
                    <span className="inbox-ctx-label">Status</span>
                    <span className={`inbox-status-pill inbox-status-pill-${selectedConv.status}`}>
                      {selectedConv.status === "open" ? "Aberta" : selectedConv.status === "pending_agent" ? "Aguardando" : selectedConv.status === "agent" ? "Atendendo" : "Fechada"}
                    </span>
                  </div>
                  <div className="inbox-ctx-row"><span className="inbox-ctx-label">Mensagens</span><span className="inbox-ctx-value">{selectedConv.message_count}</span></div>
                  <div className="inbox-ctx-row"><span className="inbox-ctx-label">Início</span><span className="inbox-ctx-value">{dateLabel(selectedConv.created_at)} {timeHM(selectedConv.created_at)}</span></div>
                </div>
                {(selectedConv.transfers || []).length > 0 && (
                  <div className="inbox-ctx-section">
                    <div className="inbox-ctx-head">Histórico</div>
                    {[...(selectedConv.transfers || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).map((t) => (
                      <div key={t.id} className="inbox-ctx-row">
                        <span className="inbox-ctx-value" style={{ fontSize: 12 }}>{t.user_name || "Sistema"} {t.action === "transfer_requested" ? "solicitou humano" : t.action === "assumed" ? "assumiu" : t.action === "transfer_department" ? "encaminhou para setor" : t.action === "released" ? "liberou" : t.action}</span>
                        <span className="inbox-ctx-time">{timeHM(t.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="inbox-placeholder small"><p className="muted">Detalhes da conversa.</p></div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
