import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

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

export default function Admin() {
  const { user, logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent" });

  const isManager = user?.role === "owner" || user?.role === "admin";

  async function load() {
    try {
      const data = await api.getUsers();
      setUsers(data);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.password) {
      setError("Nome, email e senha sao obrigatorios");
      return;
    }
    setSaving(true);
    try {
      await api.createUser(form);
      setForm({ name: "", email: "", password: "", role: "agent" });
      setShowForm(false);
      load();
    } catch (e) {
      setError("Erro ao adicionar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function changeRole(id, role) {
    try {
      await api.updateUser(id, { role });
      load();
    } catch (e) {
      setError("Erro ao alterar cargo: " + e.message);
    }
  }

  async function remove(id) {
    if (!confirm("Remover este membro da empresa?")) return;
    try {
      await api.deleteUser(id);
      load();
    } catch (e) {
      setError("Erro ao remover: " + e.message);
    }
  }

  return (
    <div className="layout">
      <header className="topbar">
        <div className="logo">Flow<span>AI</span></div>
        <nav className="topnav">
          <a href="/">Fluxos</a>
          <a href="/knowledge">Conhecimento</a>
          <a href="/whatsapp">WhatsApp</a>
          {isManager && <a href="/admin" className="active">Administração</a>}
        </nav>
        <div className="topbar-right">
          <span className="user">{user?.email}</span>
          <button className="btn ghost" onClick={logout}>Sair</button>
        </div>
      </header>

      <main className="content">
        <div className="content-head">
          <div>
            <h2>Administração da Empresa</h2>
            <p className="muted">Gerencie os membros com acesso a esta empresa.</p>
          </div>
          {isManager && (
            <button className="btn primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancelar" : "+ Adicionar membro"}
            </button>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        {!isManager && (
          <div className="notice">
            Apenas administradores (Dono/Administrador) podem alterar a equipe.
          </div>
        )}

        {showForm && isManager && (
          <form className="member-form" onSubmit={handleAdd}>
            <input
              type="text"
              placeholder="Nome"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Senha inicial"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              required
            />
            <select value={form.role} onChange={(e) => set("role", e.target.value)}>
              {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <button className="btn primary" type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Adicionar"}
            </button>
          </form>
        )}

        {loading && <p className="muted">Carregando equipe...</p>}

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
                  onChange={(e) => changeRole(u.id, e.target.value)}
                >
                  {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              ) : (
                <span className="role-badge">{ROLE_LABELS[u.role] || u.role}</span>
              )}

              {isManager && u.id !== user?.id && u.role !== "owner" && (
                <button className="btn ghost small danger" onClick={() => remove(u.id)}>Remover</button>
              )}
              {u.id === user?.id && <span className="muted">(você)</span>}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
