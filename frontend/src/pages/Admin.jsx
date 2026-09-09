import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import Skeleton from "../components/ui/Skeleton";
import Pagination from "../components/ui/Pagination";

const PAGE_SIZE = 50;
const LOGS_PAGE_SIZE = 25;

const ROLE_LABELS = {
  owner: "Dono",
  admin: "Administrador",
  agent: "Atendente",
};

const ROLE_OPTIONS = [
  ["agent", "Atendente"],
  ["admin", "Administrador"],
  ["owner", "Dono"],
];

const AUDIT_ACTIONS = [
  "auth.register",
  "auth.login",
  "auth.forgot_password",
  "auth.reset_password",
  "auth.change_password",
  "user.create",
  "user.update",
  "user.delete",
  "config.update",
  "config.update_business_hours",
  "workflow.create",
  "workflow.update",
  "workflow.delete",
  "workflow.run",
  "platform.clear_errors",
  "platform.reset_password",
  "platform.update_provider",
  "platform.update_user_ai_config",
];

const AUDIT_ENTITIES = [
  "auth",
  "company",
  "config",
  "platform",
  "user",
  "workflow",
];

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function detailSummary(raw) {
  if (!raw) return "—";
  let text = raw;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      text = Object.entries(parsed)
        .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
        .join(", ");
    }
  } catch {}
  return text.length > 100 ? text.slice(0, 100) + "…" : text;
}

export default function Admin() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent" });
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [roleChange, setRoleChange] = useState(null);
  const [changingRole, setChangingRole] = useState(false);
  const [logs, setLogs] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logPage, setLogPage] = useState(0);
  const [logAction, setLogAction] = useState("");
  const [logEntity, setLogEntity] = useState("");
  const [logUser, setLogUser] = useState("");
  const [logsLoading, setLogsLoading] = useState(false);

  const isManager = user?.role === "owner" || user?.role === "admin";

  async function load() {
    try {
      const res = await api.getUsers({ q, limit: PAGE_SIZE, offset: page * PAGE_SIZE });
      setUsers(res.items || []);
      setTotal(res.total || 0);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [q, page]);

  async function loadLogs() {
    setLogsLoading(true);
    try {
      const res = await api.getAuditLogs({
        action: logAction || undefined,
        entity: logEntity || undefined,
        user_id: logUser || undefined,
        limit: LOGS_PAGE_SIZE,
        offset: logPage * LOGS_PAGE_SIZE,
      });
      setLogs(res.items || []);
      setLogsTotal(res.total || 0);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLogsLoading(false);
    }
  }

  useEffect(() => {
    if (isManager) loadLogs();
  }, [logAction, logEntity, logUser, logPage]);

  function userNameFor(entry) {
    if (entry.user_name) return entry.user_name;
    if (entry.user_id) {
      const found = users.find((u) => u.id === entry.user_id);
      if (found) return found.name;
      return `Usuário #${entry.user_id}`;
    }
    return "—";
  }

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.password) {
      setError("Nome, email e senha são obrigatórios");
      return;
    }
    setSaving(true);
    try {
      await api.createUser(form);
      setForm({ name: "", email: "", password: "", role: "agent" });
      setShowForm(false);
      setSuccess("Membro adicionado com sucesso.");
      load();
    } catch (e) {
      setError("Erro ao adicionar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  function askRoleChange(member, role) {
    if (role === member.role) return;
    setRoleChange({ member, role });
  }

  async function confirmRoleChange() {
    if (!roleChange) return;
    setChangingRole(true);
    try {
      await api.updateUser(roleChange.member.id, { role: roleChange.role });
      load();
    } catch (e) {
      setError("Erro ao alterar cargo: " + e.message);
    } finally {
      setChangingRole(false);
      setRoleChange(null);
    }
  }

  async function confirmRemove() {
    if (!confirmTarget) return;
    setRemoving(true);
    try {
      await api.deleteUser(confirmTarget.id);
      load();
    } catch (e) {
      setError("Erro ao remover: " + e.message);
    } finally {
      setRemoving(false);
      setConfirmTarget(null);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader
          title="Administração da Empresa"
          subtitle="Gerencie os membros com acesso a esta empresa."
        >
          {isManager && (
            <button className="btn primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancelar" : "+ Adicionar membro"}
            </button>
          )}
        </PageHeader>

        {error && <Alert variant="error">{error}</Alert>}
        {success && (
          <Alert variant="success" onDismiss={() => setSuccess("")}>
            {success}
          </Alert>
        )}

        {!isManager && (
          <Alert variant="info">
            Apenas administradores (Dono/Administrador) podem alterar a equipe.
          </Alert>
        )}

        {showForm && isManager && (
          <form className="member-form" onSubmit={handleAdd}>
            <label className="field">
              <span>Nome</span>
              <input
                type="text"
                placeholder="Nome"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Senha inicial</span>
              <input
                type="password"
                placeholder="Senha inicial"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            <label className="field">
              <span>Papel</span>
              <select value={form.role} onChange={(e) => set("role", e.target.value)}>
                {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <button className="btn primary" type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Adicionar"}
            </button>
          </form>
        )}

        {loading && <Skeleton variant="cards" cards={4} />}

        {!loading && (
          <div className="list-toolbar">
            <input
              className="list-search"
              placeholder="Filtrar por nome ou email..."
              aria-label="Filtrar membros"
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(0); }}
            />
          </div>
        )}

        {!loading && users.length === 0 && (
          <EmptyState
            icon={<Icon name="users" />}
            title={q ? "Nenhum membro encontrado" : "Nenhum membro na equipe"}
            action={
              q && (
                <button className="btn ghost" onClick={() => { setQ(""); setPage(0); }}>
                  Limpar filtro
                </button>
              )
            }
          >
            {q
              ? "Nenhum membro corresponde ao filtro informado."
              : "Adicione membros para que outras pessoas da empresa possam acessar a plataforma."}
          </EmptyState>
        )}

        <div className="member-list">
          {users.map((u) => (
            <div key={u.id} className="member-row">
              <div className="member-info">
                <strong>{u.name}</strong>
                <span className="muted">{u.email}</span>
              </div>

              {isManager && u.role !== "owner" ? (
                <select
                  className="member-role"
                  value={u.role}
                  onChange={(e) => askRoleChange(u, e.target.value)}
                  aria-label={`Papel de ${u.name}`}
                >
                  {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              ) : (
                <span className="role-badge">{ROLE_LABELS[u.role] || u.role}</span>
              )}

              {isManager && u.id !== user?.id && u.role !== "owner" && (
                <button className="btn ghost small danger" onClick={() => setConfirmTarget(u)}>Remover</button>
              )}
              {u.id === user?.id && <span className="muted">(você)</span>}
            </div>
          ))}
        </div>

        {!loading && total > PAGE_SIZE && (
          <Pagination total={total} page={page} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="membro(s)" />
        )}

        {isManager && (
          <div className="card" style={{ marginTop: 32 }}>
            <h3>Auditoria</h3>
            <p className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
              Registro das ações críticas realizadas na empresa (logins, alterações de configuração,
              membros e workflows).
            </p>

            <div className="audit-filters">
              <select
                aria-label="Filtrar por impressão"
                value={logAction}
                onChange={(e) => { setLogAction(e.target.value); setLogPage(0); }}
              >
                <option value="">Todas as ações</option>
                {AUDIT_ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
              <select
                aria-label="Filtrar por entidade"
                value={logEntity}
                onChange={(e) => { setLogEntity(e.target.value); setLogPage(0); }}
              >
                <option value="">Todas as entidades</option>
                {AUDIT_ENTITIES.map((en) => <option key={en} value={en}>{en}</option>)}
              </select>
              <select
                aria-label="Filtrar por usuário"
                value={logUser}
                onChange={(e) => { setLogUser(e.target.value); setLogPage(0); }}
              >
                <option value="">Todos os usuários</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
              {(logAction || logEntity || logUser) && (
                <button
                  className="btn ghost small"
                  onClick={() => {
                    setLogAction("");
                    setLogEntity("");
                    setLogUser("");
                    setLogPage(0);
                  }}
                >
                  Limpar filtros
                </button>
              )}
            </div>

            {logsLoading ? (
              <Skeleton variant="cards" cards={3} />
            ) : logs.length === 0 ? (
              <EmptyState
                icon={<Icon name="file-text" />}
                title="Nenhum registro de auditoria"
              >
                Ações críticas realizadas na empresa aparecerão aqui.
              </EmptyState>
            ) : (
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ width: 170 }}>Quando</th>
                      <th style={{ width: 190 }}>Usuário</th>
                      <th style={{ width: 220 }}>Ação</th>
                      <th style={{ width: 120 }}>Entidade</th>
                      <th>Detalhes</th>
                      <th style={{ width: 130 }}>IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((entry) => (
                      <tr key={entry.id}>
                        <td className="muted">{formatTime(entry.created_at)}</td>
                        <td>{userNameFor(entry)}</td>
                        <td><code className="audit-code">{entry.action}</code></td>
                        <td className="muted">
                          {entry.entity || "—"}
                          {entry.entity_id != null ? ` #${entry.entity_id}` : ""}
                        </td>
                        <td>
                          <span
                            className="audit-detail"
                            title={entry.details ? `User-Agent: ${entry.user_agent || "n/d"}` : undefined}
                          >
                            {detailSummary(entry.details)}
                          </span>
                        </td>
                        <td className="muted">{entry.ip_address || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!logsLoading && logsTotal > LOGS_PAGE_SIZE && (
              <Pagination
                total={logsTotal}
                page={logPage}
                pageSize={LOGS_PAGE_SIZE}
                onChange={setLogPage}
                itemLabel="registro(s)"
              />
            )}
          </div>
        )}

        {confirmTarget && (
          <ConfirmDialog
            title="Remover membro"
            message={`Remover ${confirmTarget.name} da empresa? Esta ação não pode ser desfeita.`}
            confirmLabel="Remover"
            loading={removing}
            onConfirm={confirmRemove}
            onCancel={() => setConfirmTarget(null)}
          />
        )}

        {roleChange && (
          <ConfirmDialog
            title="Alterar papel"
            message={`Alterar papel de ${roleChange.member.name} de ${ROLE_LABELS[roleChange.member.role] || roleChange.member.role} para ${ROLE_LABELS[roleChange.role] || roleChange.role}?`}
            confirmLabel="Alterar"
            danger={false}
            loading={changingRole}
            onConfirm={confirmRoleChange}
            onCancel={() => setRoleChange(null)}
          />
        )}
      </main>
    </div>
  );
}
