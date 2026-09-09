import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import Modal from "../components/ui/Modal";
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

const LEVEL_LABELS = {
  view: "Ver",
  attend: "Atender",
  manage: "Gerenciar",
};

const LEVEL_OPTIONS = [
  ["view", "Ver"],
  ["attend", "Atender"],
  ["manage", "Gerenciar"],
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

function setSectorLevel(sectors, deptId, level) {
  return { ...(sectors || {}), [deptId]: level };
}

function SectorLinks({ departments, sectors, onChange }) {
  const [pickId, setPickId] = useState("");
  const [pickLevel, setPickLevel] = useState("attend");
  const linked = sectors || {};
  const linkedIds = Object.keys(linked).map(Number);
  const available = departments.filter((d) => !linkedIds.includes(d.id));

  if (!departments || departments.length === 0) {
    return (
      <div className="member-sectors">
        <span className="member-sectors-label">Setores</span>
        <p className="muted" style={{ fontSize: 12, margin: 0 }}>
          Crie setores na página <strong>/setores</strong> para vincular membros a eles.
        </p>
      </div>
    );
  }

  function handleLink(e) {
    e.preventDefault();
    if (!pickId) return;
    onChange({ ...linked, [Number(pickId)]: pickLevel });
    setPickId("");
    setPickLevel("attend");
  }

  function handleRemove(id) {
    const next = { ...linked };
    delete next[id];
    onChange(next);
  }

  return (
    <div className="member-sectors">
      <span className="member-sectors-label">Setores</span>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 10px" }}>
        Vincule o membro aos setores que ele atende. Sem setor, ele continua vendo todas as conversas.
      </p>
      <div className="member-sector-add">
        <select value={pickId} onChange={(e) => setPickId(e.target.value)} aria-label="Setor a vincular">
          <option value="">Selecionar setor…</option>
          {available.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={pickLevel} onChange={(e) => setPickLevel(e.target.value)} aria-label="Nível de acesso">
          {LEVEL_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <button type="button" className="btn primary small" onClick={handleLink} disabled={!pickId}>
          Vincular
        </button>
      </div>
      {linkedIds.length > 0 ? (
        <div className="member-sector-links">
          {linkedIds.map((id) => {
            const dept = departments.find((d) => d.id === id);
            return (
              <div key={id} className="member-sector-link">
                <span className="member-sector-name">{dept ? dept.name : `Setor #${id}`}</span>
                <select
                  value={linked[id]}
                  onChange={(e) => onChange(setSectorLevel(linked, id, e.target.value))}
                  aria-label={`Nível no setor ${dept ? dept.name : id}`}
                >
                  {LEVEL_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <button
                  type="button"
                  className="member-sector-remove"
                  onClick={() => handleRemove(id)}
                  aria-label={`Remover setor ${dept ? dept.name : id}`}
                  title="Remover setor"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>Nenhum setor vinculado.</p>
      )}
    </div>
  );
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
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent", sectors: {} });
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [roleChange, setRoleChange] = useState(null);
  const [changingRole, setChangingRole] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [editTarget, setEditTarget] = useState(null);
  const [editRole, setEditRole] = useState("agent");
  const [editSectors, setEditSectors] = useState({});
  const [editPassword, setEditPassword] = useState("");
  const [editSaving, setEditSaving] = useState(false);
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

  useEffect(() => {
    api.getDepartments()
      .then(setDepartments)
      .catch(() => {});
  }, []);

  const deptById = Object.fromEntries(departments.map((d) => [d.id, d.name]));

  function departmentsPayload(sectors) {
    return Object.entries(sectors || {}).map(([id, level]) => ({
      department_id: Number(id),
      level,
    }));
  }

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
      await api.createUser({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
        departments: departmentsPayload(form.sectors),
      });
      setForm({ name: "", email: "", password: "", role: "agent", sectors: {} });
      setShowForm(false);
      setSuccess("Membro adicionado com sucesso.");
      load();
    } catch (e) {
      setError("Erro ao adicionar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  function openEdit(member) {
    const sectors = {};
    (member.departments || []).forEach((d) => { sectors[d.department_id] = d.level; });
    setEditTarget(member);
    setEditRole(member.role);
    setEditSectors(sectors);
    setEditPassword("");
  }

  async function saveEdit() {
    if (!editTarget) return;
    setEditSaving(true);
    setError("");
    try {
      await api.updateUser(editTarget.id, {
        role: editRole,
        password: editPassword || undefined,
        departments: departmentsPayload(editSectors),
      });
      setSuccess(`Membro ${editTarget.name} atualizado.`);
      setEditTarget(null);
      setEditPassword("");
      load();
    } catch (e) {
      setError("Erro ao atualizar: " + e.message);
    } finally {
      setEditSaving(false);
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
            <SectorLinks departments={departments} sectors={form.sectors} onChange={(s) => set("sectors", s)} />
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
                {u.departments && u.departments.length > 0 && (
                  <div className="member-sector-badges">
                    {u.departments.map((sd) => (
                      <span
                        key={sd.department_id}
                        className="sector-badge"
                        title={`Nível: ${LEVEL_LABELS[sd.level] || sd.level}`}
                      >
                        {deptById[sd.department_id] || `Setor #${sd.department_id}`} · {LEVEL_LABELS[sd.level] || sd.level}
                      </span>
                    ))}
                  </div>
                )}
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
                <>
                  <button className="btn ghost small" onClick={() => openEdit(u)}>Editar</button>
                  <button className="btn ghost small danger" onClick={() => setConfirmTarget(u)}>Remover</button>
                </>
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

        {editTarget && (
          <Modal
            title={`Editar ${editTarget.name}`}
            icon={<Icon name="pencil" />}
            onClose={() => setEditTarget(null)}
            footer={
              <>
                <button className="btn ghost" onClick={() => setEditTarget(null)}>Cancelar</button>
                <button className="btn primary" onClick={saveEdit} disabled={editSaving}>
                  {editSaving ? "Salvando..." : "Salvar"}
                </button>
              </>
            }
          >
            <div className="member-form">
              <label className="field">
                <span>Email</span>
                <input type="text" value={editTarget.email} disabled />
              </label>
              <label className="field">
                <span>Papel</span>
                <select value={editRole} onChange={(e) => setEditRole(e.target.value)}>
                  {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Nova senha (opcional)</span>
                <input
                  type="password"
                  placeholder="Deixe em branco para manter"
                  value={editPassword}
                  onChange={(e) => setEditPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <SectorLinks departments={departments} sectors={editSectors} onChange={setEditSectors} />
            </div>
          </Modal>
        )}
      </main>
    </div>
  );
}
