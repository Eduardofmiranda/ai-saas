import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import Modal from "../components/ui/Modal";
import PageHeader from "../components/ui/PageHeader";
import Skeleton from "../components/ui/Skeleton";
import { avatarColor } from "../utils/format";

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
        <PageHeader
          title="Setores"
          subtitle="Organize o atendimento em setores para direcionar conversas e mensagens."
        >
          <button className="btn primary" onClick={openCreate}>+ Novo setor</button>
        </PageHeader>

        {error && <Alert variant="error">{error}</Alert>}
        {ok && <Alert variant="success" onDismiss={() => setOk("")}>{ok}</Alert>}

        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-icon"><Icon name="folder" size={21} /></span>
            <div>
              <div className="stat-value">{departments.length}</div>
              <div className="stat-label">Setores cadastrados</div>
            </div>
          </div>
          <div className="stat-card green">
            <span className="stat-icon"><Icon name="file-text" size={21} /></span>
            <div>
              <div className="stat-value">{withDesc}</div>
              <div className="stat-label">Com descrição</div>
            </div>
          </div>
          <div className="stat-card amber">
            <span className="stat-icon"><Icon name="message-circle" size={21} /></span>
            <div>
              <div className="stat-value">{departments.length ? departments.length : "—"}</div>
              <div className="stat-label">Disponíveis no encaminhamento</div>
            </div>
          </div>
        </div>

        <div className="toolbar">
          <div className="search-box grow">
            <span className="search-icon"><Icon name="search" size={14} /></span>
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
            <Skeleton />
          </div>
        ) : departments.length === 0 ? (
          <EmptyState
            icon={<Icon name="folder" size={40} />}
            title="Nenhum setor configurado"
            action={<button className="btn primary" onClick={openCreate}>+ Criar setor</button>}
          >
            Crie o primeiro setor para usar no encaminhamento de atendimento entre agentes e equipes.
          </EmptyState>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Icon name="search" size={40} />}
            title="Nada encontrado"
            action={<button className="btn ghost" onClick={() => setQuery("")}>Limpar busca</button>}
          >
            Nenhum setor corresponde à busca "{query}".
          </EmptyState>
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
                          style={{ background: avatarColor(d.name || "?") }}
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
        <Modal
          title={modal.mode === "create" ? "Novo setor" : "Editar setor"}
          onClose={() => { if (!modal.saving) setModal(null); }}
          footer={
            <>
              <button type="button" className="btn ghost" onClick={() => { if (!modal.saving) setModal(null); }} disabled={modal.saving}>
                Cancelar
              </button>
              <button type="submit" form="dept-form" className="btn primary" disabled={!modal.name.trim() || modal.saving}>
                {modal.saving ? "Salvando..." : modal.mode === "create" ? "Criar setor" : "Salvar"}
              </button>
            </>
          }
        >
          <form id="dept-form" onSubmit={saveModal}>
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
          </form>
        </Modal>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Remover setor"
          message={
            <>
              <p style={{ margin: "0 0 6px", lineHeight: 1.5 }}>
                Tem certeza que deseja remover o setor <strong>{confirmDelete.name}</strong>?
              </p>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                Esta ação não pode ser desfeita.
              </p>
            </>
          }
          confirmLabel="Remover"
          loading={confirmDelete.saving}
          onConfirm={confirmRemove}
          onCancel={() => { if (!confirmDelete.saving) setConfirmDelete(null); }}
        />
      )}
    </div>
  );
}