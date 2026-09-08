import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

const AVATAR_COLORS = ["#4f7cff", "#6ea8ff", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#14b8a6"];

function hashColor(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 997;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

export default function Departments() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [query, setQuery] = useState("");

  const [modal, setModal] = useState(null); // { mode: "create" | "edit", id, name, description, saving }
  const [confirmDelete, setConfirmDelete] = useState(null); // { id, name, saving }

  async function load() {
    try {
      const res = await api.getDepartments();
      setDepartments(Array.isArray(res) ? res : []);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") {
        setModal(null);
        setConfirmDelete(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return departments;
    return departments.filter(
      (d) =>
        d.name?.toLowerCase().includes(q) ||
        d.description?.toLowerCase().includes(q)
    );
  }, [departments, query]);

  const withDesc = departments.filter((d) => d.description?.trim()).length;

  function openCreate() {
    setModal({ mode: "create", id: null, name: "", description: "", saving: false });
  }

  function openEdit(d) {
    setModal({ mode: "edit", id: d.id, name: d.name || "", description: d.description || "", saving: false });
  }

  async function saveModal(e) {
    e.preventDefault();
    if (!modal.name.trim() || modal.saving) return;
    setModal({ ...modal, saving: true });
    setError("");
    try {
      if (modal.mode === "create") {
        await api.createDepartment({ name: modal.name.trim(), description: modal.description.trim() });
        setOk("Setor criado com sucesso.");
      } else {
        await api.updateDepartment(modal.id, { name: modal.name.trim(), description: modal.description.trim() });
        setOk("Setor atualizado com sucesso.");
      }
      setModal(null);
      await load();
    } catch (e) {
      setModal({ ...modal, saving: false });
      setError(e.message);
    }
  }

  async function confirmRemove() {
    if (!confirmDelete || confirmDelete.saving) return;
    setConfirmDelete({ ...confirmDelete, saving: true });
    setError("");
    try {
      await api.deleteDepartment(confirmDelete.id);
      setOk("Setor removido.");
      setConfirmDelete(null);
      await load();
    } catch (e) {
      setConfirmDelete({ ...confirmDelete, saving: false });
      setError(e.message);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="page-header page-header-row">
          <div className="page-header">
            <h1>Setores</h1>
            <p className="muted">
              Organize o atendimento em setores para direcionar conversas e mensagens.
            </p>
          </div>
          <button className="btn primary" onClick={openCreate}>+ Novo setor</button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {ok && (
          <div className="alert alert-success" role="status">
            {ok}
            <button
              aria-label="Fechar aviso"
              style={{ marginLeft: "auto", background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 14 }}
              onClick={() => setOk("")}
            >✕</button>
          </div>
        )}

        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-icon">🗂️</span>
            <div>
              <div className="stat-value">{departments.length}</div>
              <div className="stat-label">Setores cadastrados</div>
            </div>
          </div>
          <div className="stat-card green">
            <span className="stat-icon">📝</span>
            <div>
              <div className="stat-value">{withDesc}</div>
              <div className="stat-label">Com descrição</div>
            </div>
          </div>
          <div className="stat-card amber">
            <span className="stat-icon">💬</span>
            <div>
              <div className="stat-value">{departments.length ? departments.length : "—"}</div>
              <div className="stat-label">Disponíveis no encaminhamento</div>
            </div>
          </div>
        </div>

        <div className="toolbar">
          <div className="search-box grow">
            <span className="search-icon">🔎</span>
            <input
              className="input"
              placeholder="Buscar setor por nome ou descrição..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <span className="count-pill">
            {filtered.length} de <b>{departments.length}</b>
          </span>
        </div>

        {loading ? (
          <div className="card">
            <p className="muted">Carregando setores...</p>
          </div>
        ) : departments.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🗂️</div>
            <h3>Nenhum setor configurado</h3>
            <p>
              Crie o primeiro setor para usar no encaminhamento de atendimento
              entre agentes e equipes.
            </p>
            <button className="btn primary" onClick={openCreate}>+ Criar setor</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔎</div>
            <h3>Nada encontrado</h3>
            <p>Nenhum setor corresponde à busca "{query}".</p>
            <button className="btn ghost" onClick={() => setQuery("")}>Limpar busca</button>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 220 }}>Setor</th>
                  <th>Descrição</th>
                  <th style={{ width: 130 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span
                          className="avatar-sm"
                          style={{ background: hashColor(d.name || "?") }}
                        >
                          {(d.name || "?").charAt(0).toUpperCase()}
                        </span>
                        <span className="cell-strong">{d.name}</span>
                      </div>
                    </td>
                    <td className="muted">{d.description || "Sem descrição"}</td>
                    <td>
                      <div className="row-actions">
                        <button className="btn ghost small" onClick={() => openEdit(d)}>Editar</button>
                        <button
                          className="btn ghost small danger"
                          onClick={() => setConfirmDelete({ id: d.id, name: d.name, saving: false })}
                        >
                          Remover
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {modal && (
        <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !modal.saving) setModal(null); }}>
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-title">
                {modal.mode === "create" ? "Novo setor" : "Editar setor"}
              </div>
              <button className="modal-close" onClick={() => setModal(null)} aria-label="Fechar">✕</button>
            </div>
            <form onSubmit={saveModal}>
              <div className="modal-body">
                <div className="stack">
                  <label className="field">
                    <span>Nome do setor</span>
                    <input
                      className="input"
                      placeholder="Ex.: Suporte, Vendas, Financeiro"
                      value={modal.name}
                      onChange={(e) => setModal({ ...modal, name: e.target.value })}
                      autoFocus
                      maxLength={80}
                    />
                  </label>
                  <label className="field">
                    <span>Descrição (opcional)</span>
                    <textarea
                      className="input"
                      rows="3"
                      placeholder="Para que serve este setor?"
                      value={modal.description}
                      onChange={(e) => setModal({ ...modal, description: e.target.value })}
                      maxLength={300}
                    />
                  </label>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn ghost" onClick={() => setModal(null)} disabled={modal.saving}>
                  Cancelar
                </button>
                <button type="submit" className="btn primary" disabled={!modal.name.trim() || modal.saving}>
                  {modal.saving ? "Salvando..." : modal.mode === "create" ? "Criar setor" : "Salvar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmDelete && (
        <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !confirmDelete.saving) setConfirmDelete(null); }}>
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-title">Remover setor</div>
              <button className="modal-close" onClick={() => setConfirmDelete(null)} aria-label="Fechar">✕</button>
            </div>
            <div className="modal-body">
              <p style={{ margin: "0 0 6px", lineHeight: 1.5 }}>
                Tem certeza que deseja remover o setor <strong>{confirmDelete.name}</strong>?
              </p>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                Esta ação não pode ser desfeita.
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn ghost" onClick={() => setConfirmDelete(null)} disabled={confirmDelete.saving}>
                Cancelar
              </button>
              <button className="btn solid-danger" onClick={confirmRemove} disabled={confirmDelete.saving}>
                {confirmDelete.saving ? "Removendo..." : "Remover"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}