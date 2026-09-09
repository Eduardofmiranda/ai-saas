import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../api";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import Pagination from "../components/ui/Pagination";
import { formatPhone, avatarColor } from "../utils/format";
import { useWebSocket } from "../hooks/useWebSocket";

const POLL_MS = 30000;
const PAGE_SIZE = 50;

const TAB_STATUS = {
  all: undefined,
  open: "open",
  pending: "pending_agent",
  agent: "agent",
  closed: "closed",
};

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

const STATUS_LABEL = {
  open: "Aberta",
  pending_agent: "Aguardando",
  agent: "Atendendo",
  closed: "Fechada",
};

const STATUS_ACTIONS = {
  open: [{ label: "Fechar", target: "closed" }],
  pending_agent: [
    { label: "Assumir", target: "agent" },
    { label: "Fechar", target: "closed" },
  ],
  agent: [
    { label: "Liberar", target: "open" },
    { label: "Fechar", target: "closed" },
  ],
  closed: [{ label: "Reabrir", target: "open" }],
};

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState(null);
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [composerError, setComposerError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const sendingRef = useRef(false);
  const lastSelectedIdRef = useRef(null);
  const justSentRef = useRef(false);

  const selectedConv = conversations.find((c) => c.id === selected) || null;

  const refreshConversations = useCallback(async () => {
    try {
      const res = await api.getConversations({
        status: TAB_STATUS[tab],
        q,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setConversations(res.items || []);
      setTotal(res.total || 0);
      setError("");
    } catch (e) {
      setError(e.message || "Erro ao carregar conversas");
    }
  }, [tab, q, page]);

  const refreshMessages = useCallback(async () => {
    if (!selected) { setMessages(null); return; }
    try {
      const msgRes = await api.getConversationMessages(selected);
      setMessages(msgRes.items || []);
    } catch (e) {
      setError(e.message || "Erro ao carregar mensagens");
    }
  }, [selected]);

  useWebSocket(null, useCallback((event, data) => {
    if (event === "message.new" || event === "message.reply") {
      refreshConversations();
      if (selected && data.conversation_id === selected) {
        refreshMessages();
      }
    }
  }, [refreshConversations, refreshMessages, selected]));

  // Polling reduzido (fallback para WebSocket)
  useEffect(() => {
    let active = true;
    const id = setInterval(() => { if (active) refreshConversations(); }, POLL_MS);
    return () => { active = false; clearInterval(id); };
  }, [refreshConversations]);

  useEffect(() => {
    if (!selected) { setMessages(null); return; }
    let active = true;
    const id = setInterval(() => { if (active) refreshMessages(); }, POLL_MS);
    return () => { active = false; clearInterval(id); };
  }, [refreshMessages, selected]);

  // Carregamento inicial
  useEffect(() => {
    refreshConversations();
  }, []);

  useEffect(() => {
    if (selected) refreshMessages();
  }, [selected]);

  useEffect(() => {
    if (!endRef.current) return;
    const shouldScroll = justSentRef.current || selected !== lastSelectedIdRef.current;
    if (shouldScroll) {
      endRef.current.scrollIntoView({ block: "end" });
      justSentRef.current = false;
      lastSelectedIdRef.current = selected;
    }
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
    justSentRef.current = true;
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

  async function changeStatus(target) {
    if (!selectedConv || actionLoading) return;
    setActionLoading(true);
    try {
      await api.updateConversation(selectedConv.id, { status: target });
      // Poll vai atualizar
    } catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  async function pauseWorkflow() {
    if (!selectedConv || actionLoading) return;
    setActionLoading(true);
    try {
      await api.pauseConversationWorkflow(selectedConv.id);
      // Poll vai atualizar
    } catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content inbox-content">
        <h1 className="sr-only">Conversas</h1>
        {error && <Alert variant="error">{error}</Alert>}
        <div className="inbox-layout">
          <aside className="inbox-list">
            <div className="inbox-toolbar">
              <input
                className="inbox-search"
                placeholder="Buscar por cliente ou telefone..."
                aria-label="Buscar conversas"
                value={q}
                onChange={(e) => { setQ(e.target.value); setPage(0); }}
              />
              <div className="inbox-filters">
                {[["all", "Todas"], ["open", "Abertas"], ["pending", "Aguardando"], ["agent", "Atendendo"], ["closed", "Fechadas"]].map(([key, label]) => (
                  <button
                    key={key}
                    className={`inbox-filter ${tab === key ? "active" : ""}`}
                    onClick={() => { setTab(key); setPage(0); }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="inbox-items">
              {conversations.length === 0 ? (
                <div className="empty-inbox">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  <p>{q || tab !== "all" ? "Nenhuma conversa para este filtro." : "Nenhuma conversa ainda"}</p>
                </div>
              ) : (
                conversations.map((c) => {
                  const name = c.customer?.name || c.customer?.phone || `#${c.id}`;
                  return (
                    <button key={c.id} type="button" className={`inbox-item ${selected === c.id ? "selected" : ""}`} onClick={() => select(c.id)}>
                      <div className="inbox-avatar" style={{ background: avatarColor(name) }}>{name.slice(0, 1).toUpperCase()}</div>
                      <div className="inbox-item-body">
                        <div className="inbox-item-top">
                          <span className="inbox-item-name">{name}</span>
                          <span className="inbox-item-time">{relativeTime(c.last_message_at || c.updated_at)}</span>
                        </div>
                        <div className="inbox-item-bottom">
                          {c.department_name && <span className="inbox-sector-badge">{c.department_name}</span>}
                          <span className="inbox-item-preview">{c.last_message || "Sem mensagens"}</span>
                          <span className={`inbox-status-dot inbox-status-dot-${c.status}`} />
                          <span className="sr-only">{STATUS_LABEL[c.status] || c.status}</span>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
            {total > PAGE_SIZE && (
              <Pagination total={total} page={page} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="conversa(s)" />
            )}
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
                    {selectedConv.has_pending_flow && (
                      <button className="btn warning small" onClick={pauseWorkflow} title="Pausar fluxo e assumir atendimento" disabled={actionLoading}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
                        Pausar fluxo
                      </button>
                    )}
                    {(STATUS_ACTIONS[selectedConv.status] || []).map((action) => (
                      <button
                        key={action.target}
                        className="btn ghost small"
                        onClick={() => changeStatus(action.target)}
                        disabled={actionLoading}
                      >
                        {action.label}
                      </button>
                    ))}
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
                    rows={1}
                    placeholder={selectedConv.status === "closed" ? "Conversa fechada..." : "Digite sua resposta..."}
                    aria-label="Digite sua resposta"
                    value={draft}
                    disabled={selectedConv.status === "closed"}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={onKeyDown}
                  />
                  <button className="btn primary inbox-send-btn" onClick={sendReply} disabled={!draft.trim() || selectedConv.status === "closed"} aria-label="Enviar mensagem">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                  </button>
                </div>
                {composerError && <Alert variant="error">{composerError}</Alert>}
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
                  <div className="inbox-ctx-row"><span className="inbox-ctx-label">Setor</span><span className="inbox-ctx-value">{selectedConv.department_name || "—"}</span></div>
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
