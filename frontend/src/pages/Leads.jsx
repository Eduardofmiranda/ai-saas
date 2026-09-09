import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "../api";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import PageHeader from "../components/ui/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import Modal from "../components/ui/Modal";
import Icon from "../components/ui/Icon";
import { formatPhone, avatarColor } from "../utils/format";

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
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmAll, setConfirmAll] = useState(false);

  const exportRef = useRef(null);

  const handleExportOutside = useCallback((e) => {
    if (exportRef.current && !exportRef.current.contains(e.target)) {
      setShowExportMenu(false);
    }
  }, []);

  const handleExportKey = useCallback((e) => {
    if (e.key === "Escape") setShowExportMenu(false);
  }, []);

  useEffect(() => {
    if (showExportMenu) {
      document.addEventListener("mousedown", handleExportOutside);
      document.addEventListener("keydown", handleExportKey);
    }
    return () => {
      document.removeEventListener("mousedown", handleExportOutside);
      document.removeEventListener("keydown", handleExportKey);
    };
  }, [showExportMenu, handleExportOutside, handleExportKey]);

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

  async function confirmRemoveLead() {
    const { id } = confirmDelete;
    setConfirmDelete(null);
    try {
      await api.deleteCustomer(id);
      setLeads((prev) => prev.filter((c) => c.id !== id));
      setTotal((prev) => prev - 1);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
    } catch (e) { setError(e.message); }
  }

  function exportJson() {
    setShowExportMenu(false);
    setError("");
    api.exportCustomersJson().catch((e) => setError(e.message || "Erro ao exportar JSON"));
  }

  function exportXlsx() {
    setShowExportMenu(false);
    setError("");
    api.exportCustomersXlsx().catch((e) => setError(e.message || "Erro ao exportar Excel"));
  }

  async function sendBulk() {
    const text = bulkText.trim();
    if (!text) return;
    if (selected.size === 0 && !confirmAll) {
      setConfirmAll(true);
      return;
    }
    setSending(true);
    setError("");
    setSuccess("");
    try {
      const ids = selected.size > 0 ? [...selected] : undefined;
      const res = await api.bulkMessageCustomers({
        text,
        ...(ids ? { customer_ids: ids } : { all: true }),
      });
      setSuccess(res.message || "Mensagem enviada com sucesso!");
      setBulkText("");
      setShowBulk(false);
      setSelected(new Set());
      setConfirmAll(false);
    } catch (e) {
      setError(e.message || "Erro ao enviar");
    } finally {
      setSending(false);
    }
  }

  function closeBulk() {
    setShowBulk(false);
    setBulkText("");
    setConfirmAll(false);
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader
          title="Leads"
          subtitle={`${total} contatos no sistema`}
        >
          <div className="dropdown-wrap" ref={exportRef}>
            <button
              className="btn ghost"
              onClick={() => setShowExportMenu(!showExportMenu)}
              aria-haspopup="true"
              aria-expanded={showExportMenu}
            >
              <Icon name="download" size={16} />
              Exportar
            </button>
            {showExportMenu && (
              <div className="dropdown-menu">
                <button onClick={exportJson}>
                  <Icon name="file-text" size={14} />
                  JSON
                </button>
                <button onClick={exportXlsx}>
                  <Icon name="file-text" size={14} />
                  Excel (.xlsx)
                </button>
              </div>
            )}
          </div>
          <button className="btn primary" onClick={() => setShowBulk(true)}>
            <Icon name="send" size={16} />
            Mensagem em massa
          </button>
        </PageHeader>

        {error && <Alert variant="error" onDismiss={() => setError("")}>{error}</Alert>}
        {success && <Alert variant="success" onDismiss={() => setSuccess("")}>{success}</Alert>}

        <div className="leads-search-row">
          <input
            className="leads-search"
            placeholder="Buscar por nome ou telefone..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Buscar leads"
          />
          {filtered.length > 0 && (
            <label className="leads-select-all">
              <input
                type="checkbox"
                checked={selected.size === filtered.length && filtered.length > 0}
                onChange={selectAll}
              />
              {selected.size > 0 ? `${selected.size} selecionados` : `Todos (${filtered.length})`}
            </label>
          )}
        </div>

        {loading ? (
          <div className="leads-loading" role="status">
            <div className="inbox-spinner" />
            <span className="sr-only">Carregando...</span>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Icon name="users" size={40} />}
            title={ql ? "Nenhum lead encontrado para esta busca." : "Nenhum lead ainda."}
          >
            {!ql && "Leads sao salvos automaticamente quando enviam mensagem pelo WhatsApp."}
          </EmptyState>
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
                  <div className="lead-meta">
                    {c.email && (
                      <span className="lead-extra">
                        <Icon name="mail" size={13} />
                        {c.email}
                      </span>
                    )}
                    {c.company && (
                      <span className="lead-extra">
                        <Icon name="building" size={13} />
                        {c.company}
                      </span>
                    )}
                    {c.city && (
                      <span className="lead-extra">
                        <Icon name="globe" size={13} />
                        {c.city}
                      </span>
                    )}
                  </div>
                  <div className="lead-card-ops">
                    <span className="lead-conversations">
                      <Icon name="message-circle" size={14} />
                      {c.conversation_count} {c.conversation_count === 1 ? "conversa" : "conversas"}
                    </span>
                    <button className="btn danger ghost small" onClick={() => setConfirmDelete({ id: c.id, name: c.name || c.phone })} aria-label="Remover lead">
                      <Icon name="trash" size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {confirmDelete && (
        <ConfirmDialog
          title="Remover lead"
          message={`Remover lead "${confirmDelete.name}"? Isso apagara todas as conversas e mensagens.`}
          confirmLabel="Remover"
          onConfirm={confirmRemoveLead}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {showBulk && (
        <Modal
          title="Mensagem em Massa"
          icon={<Icon name="send" size={20} />}
          onClose={closeBulk}
          footer={
            <>
              <button className="btn ghost" onClick={closeBulk} disabled={sending}>
                Cancelar
              </button>
              <button
                className={confirmAll ? "btn solid-danger" : "btn primary"}
                onClick={sendBulk}
                disabled={!bulkText.trim() || sending}
              >
                {sending ? "Enviando..." : confirmAll ? "Confirmar envio para todos" : "Enviar"}
              </button>
            </>
          }
        >
          <div className="bulk-target">
            <Icon name="users" size={16} />
            <span>
              {selected.size > 0
                ? `${selected.size} lead${selected.size > 1 ? "s" : ""} selecionado${selected.size > 1 ? "s" : ""}`
                : `Todos os ${leads.length} leads`}
            </span>
          </div>

          {confirmAll && selected.size === 0 && (
            <Alert variant="error">
              A mensagem sera enviada para <strong>TODOS os {leads.length} contatos</strong>.
              Esta acao e irreversivel.
            </Alert>
          )}

          <textarea
            className="bulk-textarea"
            rows="5"
            placeholder="Digite a mensagem que deseja enviar para seus leads..."
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            aria-label="Mensagem em massa"
          />

          <div className="bulk-preview">
            <span className="bulk-preview-label">Pre-visualizacao</span>
            <div className="bulk-preview-box">
              {bulkText || "Sua mensagem aparecera aqui..."}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
