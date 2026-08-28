import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      const data = await api.getWorkflows();
      setWorkflows(data);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function createNew() {
    try {
      const wf = await api.createWorkflow({ name: "Novo Fluxo", data: { nodes: [], edges: [] } });
      navigate(`/editor/${wf.id}`);
    } catch (e) {
      setError("Erro ao criar fluxo: " + e.message);
    }
  }

  async function remove(id, e) {
    e.stopPropagation();
    if (!confirm("Excluir este fluxo?")) return;
    try {
      await api.deleteWorkflow(id);
      load();
    } catch (e) {
      setError("Erro ao excluir: " + e.message);
    }
  }

  async function toggleActive(wf, e) {
    e.stopPropagation();
    try {
      await api.updateWorkflow(wf.id, { active: !wf.active });
      load();
    } catch (e) {
      setError("Erro ao alterar status: " + e.message);
    }
  }

  return (
    <div className="layout">
      <header className="topbar">
        <div className="logo">Flow<span>AI</span></div>
        <div className="topbar-right">
          <a href="/knowledge" className="btn ghost">Conhecimento</a>
          <span className="user">{user?.email}</span>
          <button className="btn ghost" onClick={logout}>Sair</button>
        </div>
      </header>

      <main className="content">
        <div className="content-head">
          <h2>Fluxos de automação</h2>
          <button className="btn primary" onClick={createNew}>+ Novo fluxo</button>
        </div>

        {loading && <p className="muted">Carregando fluxos...</p>}
        {error && <div className="error">{error}</div>}

        {!loading && !error && workflows.length === 0 && (
          <div className="empty">
            <p>Nenhum fluxo ainda.</p>
            <p>Crie o primeiro para começar a automatizar o atendimento.</p>
            <button className="btn primary" onClick={createNew} style={{ marginTop: 12 }}>+ Criar fluxo</button>
          </div>
        )}

        <div className="wf-grid">
          {workflows.map((wf) => (
            <div key={wf.id} className="wf-card" onClick={() => navigate(`/editor/${wf.id}`)}>
              <h3>{wf.name}</h3>
              <p>{wf.description || "Sem descrição"}</p>
              <div className="wf-meta">
                <button
                  className={`btn small ${wf.active ? "ghost" : "secondary"}`}
                  onClick={(e) => toggleActive(wf, e)}
                  title={wf.active ? "Desativar" : "Ativar"}
                >
                  {wf.active ? "Ativo" : "Inativo"}
                </button>
                <button className="btn ghost small danger" onClick={(e) => remove(wf.id, e)}>Excluir</button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
