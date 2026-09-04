import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

const STATUS_LABELS = { open: "Aberta", pending_agent: "Aguardando humano", closed: "Fechada" };
const TRANSFER_LABELS = {
  transfer_requested: "Atendimento humano solicitado",
  assumed: "assumiu a conversa",
  closed: "fechou a conversa",
  reopened: "reabriu a conversa",
};
const POLL_MS = 8000;

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

function dateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function formatPhone(p) {
  const d = (p || "").replace(/\D/g, "");
  if (d.length === 13) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 9)}-${d.slice(9)}`;
  if (d.length === 12) return `+${d.slice(0, 2)} (${d.slice(2, 4)}) ${d.slice(4, 8)}-${d.slice(8)}`;
  return d;
}

const AVATAR_COLORS = ["#4f7cff", "#8b5cf6", "#06b6d4", "#22c55e", "#f59e0b", "#ec4899"];
function avatarColor(seed) {
  let h = 0;
  for (const ch of String(seed || "")) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState(null);
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [composerError, setComposerError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const selectedConv = conversations.find((c) => c.id === selected) || null;

  useEffect(() => {
    let active = true;
    async function tick() {
      try {
        const list = await api.getConversations();
        if (!active) return;
        setConversations(list);
        setError("");
        if (selected && list.some((c) => c.id === selected)) {
          const msgs = await api.getConversationMessages(selected);
          if (active) setMessages(msgs);
        }
      } catch (e) {
        if (active) setError(e.message || "Erro ao atualizar conversas");
      }
    }
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [selected]);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ block: "end" });
  }, [messages]);

  function select(id) {
    setSelected(id);
    setMessages(null);
    setComposerError("");
  }

  async function sendReply() {
    const content = draft.trim();
    if (!content || !selected || sending) return;
    setSending(true);
    setComposerError("");
    try {
      await api.replyToConversation(selected, content);
      setDraft("");
      const [msgs, list] = await Promise.all([
        api.getConversationMessages(selected),
        api.getConversations(),
      ]);
      setMessages(msgs);
      setConversations(list);
    } catch (e) {
      setComposerError(e.message || "Falha ao enviar resposta");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendReply();
    }
  }

  async function toggleStatus() {
    if (!selectedConv) return;
    const next =
      selectedConv.status === "pending_agent"
        ? "open"
        : selectedConv.status === "open"
          ? "closed"
          : "open";
    try {
      await api.updateConversation(selectedConv.id, { status: next });
      const list = await api.getConversations();
      setConversations(list);
    } catch (e) {
      setError(e.message || "Erro ao atualizar status");
    }
  }

  const ql = q.trim().toLowerCase();
  const filtered = conversations.filter((c) => {
    if (tab === "open" && c.status !== "open") return false;
    if (tab === "pending" && c.status !== "pending_agent") return false;
    if (tab === "closed" && c.status !== "closed") return false;
    if (ql) {
      const hay = `${c.customer?.name || ""} ${c.customer?.phone || ""}`.toLowerCase();
      if (!hay.includes(ql)) return false;
    }
    return true;
  });
  const openCount = conversations.filter((c) => c.status === "open").length;
  const pendingCount = conversations.filter((c) => c.status === "pending_agent").length;
  const closedCount = conversations.filter((c) => c.status === "closed").length;

  return (
    <div className="layout">
      <Header />
      <main className="content inbox-content">
        <div className="content-head">
          <div>
            <h2>Conversas</h2>
            <p className="muted">Atendimento: acompanhe a thread e responda manualmente quando precisar.</p>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="inbox-layout">
          {/* Painel 1: lista de conversas */}
          <aside className="inbox-list">
            <input
              className="inbox-search"
              placeholder="Buscar por nome ou telefone..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="inbox-tabs">
              <button className={`inbox-tab ${tab === "all" ? "active" : ""}`} onClick={() => setTab("all")}>
                Todas ({conversations.length})
              </button>
              <button className={`inbox-tab ${tab === "open" ? "active" : ""}`} onClick={() => setTab("open")}>
                Abertas ({openCount})
              </button>
              <button className={`inbox-tab ${tab === "pending" ? "active" : ""}`} onClick={() => setTab("pending")}>
                Aguardando ({pendingCount})
              </button>
              <button className={`inbox-tab ${tab === "closed" ? "active" : ""}`} onClick={() => setTab("closed")}>
                Fechadas ({closedCount})
              </button>
            </div>
            <div className="inbox-items">
              {conversations.length === 0 ? (
                <div className="empty-inbox">
                  <p>Nenhuma conversa ainda.</p>
                  <p className="muted">Novas conversas aparecerão aqui quando o WhatsApp receber mensagens.</p>
                </div>
              ) : filtered.length === 0 ? (
                <div className="empty-inbox">
                  <p className="muted">Nenhuma conversa para este filtro.</p>
                </div>
              ) : (
                filtered.map((c) => (
                  <div
                    key={c.id}
                    className={`inbox-item ${selected === c.id ? "selected" : ""}`}
                    onClick={() => select(c.id)}
                  >
                    <div className="inbox-avatar" style={{ background: avatarColor(c.customer?.name || c.customer?.phone) }}>
                      {(c.customer?.name || "?").slice(0, 1).toUpperCase()}
                    </div>
                    <div className="inbox-item-body">
                      <div className="inbox-item-top">
                        <strong>{c.customer?.name || c.customer?.phone || `Cliente ${c.id}`}</strong>
                        <span className="inbox-time">{relativeTime(c.last_message_at || c.updated_at)}</span>
                      </div>
                      <div className="inbox-item-meta">
                        <span className={`inbox-status inbox-status-${c.status}`}>
                          {STATUS_LABELS[c.status] || c.status}
                        </span>
                        {c.last_message ? (
                          <span className="inbox-preview">{c.last_message}</span>
                        ) : (
                          <span className="inbox-preview muted">Sem mensagens</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </aside>

          {/* Painel 2: thread + resposta */}
          <section className="inbox-thread">
            {selectedConv ? (
              <>
                <header className="inbox-thread-head">
                  <div>
                    <strong>{selectedConv.customer?.name || selectedConv.customer?.phone || "Conversa"}</strong>
                    <span className="muted">{formatPhone(selectedConv.customer?.phone)}</span>
                  </div>
                  <button className="btn ghost small" onClick={toggleStatus}>
                    {selectedConv.status === "pending_agent"
                      ? "Assumir conversa"
                      : selectedConv.status === "open"
                        ? "Fechar conversa"
                        : "Reabrir conversa"}
                  </button>
                </header>

                <div className="inbox-msgs">
                  {messages === null ? (
                    <p className="muted">Carregando mensagens...</p>
                  ) : messages.length === 0 ? (
                    <p className="muted">Nenhuma mensagem neste chat.</p>
                  ) : (
                    messages.map((m) => (
                      <div key={m.id} className={`bubble ${m.sender_type === "customer" ? "client" : m.sender_type === "bot" ? "bot" : "agent"}`}>
                        <div className="bubble-text">{m.content}</div>
                        <div className="bubble-time">{timeHM(m.created_at)}</div>
                      </div>
                    ))
                  )}
                  <div ref={endRef} />
                </div>

                <div className="inbox-composer">
                  <textarea
                    ref={inputRef}
                    className="inbox-input"
                    rows="1"
                    placeholder="Escreva sua resposta... (Enter envia, Shift+Enter quebra linha)"
                    value={draft}
                    disabled={sending}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={onKeyDown}
                  />
                  <button className="btn primary" onClick={sendReply} disabled={sending || !draft.trim()}>
                    {sending ? "Enviando..." : "Enviar"}
                  </button>
                </div>
                {composerError && <div className="error" style={{ margin: "0 12px 8px" }}>{composerError}</div>}
              </>
            ) : (
              <div className="inbox-placeholder">
                <h3>Selecione uma conversa</h3>
                <p className="muted">Escolha uma conversa à esquerda para ver as mensagens e responder.</p>
              </div>
            )}
          </section>

          {/* Painel 3: contexto do cliente */}
          <aside className="inbox-context">
            {selectedConv ? (
              <>
                <div className="inbox-ctx-head">Cliente</div>
                <div className="inbox-ctx-row">
                  <span className="muted">Nome</span>
                  <span>{selectedConv.customer?.name || "—"}</span>
                </div>
                <div className="inbox-ctx-row">
                  <span className="muted">Telefone</span>
                  <span>{formatPhone(selectedConv.customer?.phone)}</span>
                </div>
                <div className="inbox-ctx-row">
                  <span className="muted">Status</span>
                  <span>{STATUS_LABELS[selectedConv.status] || selectedConv.status}</span>
                </div>
                <div className="inbox-ctx-row">
                  <span className="muted">Início</span>
                  <span>{dateTime(selectedConv.created_at)}</span>
                </div>
                <div className="inbox-ctx-row">
                  <span className="muted">Mensagens</span>
                  <span>{selectedConv.message_count}</span>
                </div>
                <div className="inbox-ctx-head">Histórico de transferências</div>
                {(selectedConv.transfers || []).length === 0 ? (
                  <p className="muted" style={{ fontSize: 12, padding: "4px 12px 8px" }}>
                    Sem registros de transferência.
                  </p>
                ) : (
                  <div className="inbox-ctx-transfers">
                    {[...(selectedConv.transfers || [])]
                      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                      .map((t) => (
                        <div key={t.id} className="inbox-ctx-row">
                          <span className="muted">
                            {t.action === "transfer_requested"
                              ? "Atendimento humano solicitado"
                              : `${t.user_name || "Atendente"} ${TRANSFER_LABELS[t.action] || t.action}`}
                          </span>
                          <span>{dateTime(t.created_at)}</span>
                        </div>
                      ))}
                  </div>
                )}
              </>
            ) : (
              <div className="inbox-placeholder small">
                <p className="muted">Detalhes da conversa aparecem aqui.</p>
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}