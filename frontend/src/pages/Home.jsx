import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTemplates, setShowTemplates] = useState(false);

  async function load() {
    try {
      const [wfData, tplData] = await Promise.all([
        api.getWorkflows(),
        api.getTemplates(),
      ]);
      setWorkflows(wfData);
      setTemplates(tplData);
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

  async function applyTemplate(templateId) {
    try {
      const wf = await api.useTemplate(templateId);
      setShowTemplates(false);
      navigate(`/editor/${wf.id}`);
    } catch (e) {
      setError("Erro ao usar template: " + e.message);
    }
  }

  async function duplicate(id, e) {
    e.stopPropagation();
    try {
      await api.duplicateWorkflow(id);
      load();
    } catch (e) {
      setError("Erro ao duplicar: " + e.message);
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
        <nav className="topnav">
          <a href="/" className="active">Fluxos</a>
          <a href="/knowledge">Conhecimento</a>
          <a href="/whatsapp">WhatsApp</a>
          {(user?.role === "owner" || user?.role === "admin") && <a href="/admin">Administração</a>}
        </nav>
        <div className="topbar-right">
          <span className="user">{user?.email}</span>
          <button className="btn ghost" onClick={logout}>Sair</button>
        </div>
      </header>

      <main className="content">
        <div className="content-head">
          <h2>Fluxos de automacao</h2>
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setShowTemplates(!showTemplates)}>
              {showTemplates ? "Fechar" : "Templates"}
            </button>
            <button className="btn primary" onClick={createNew}>+ Novo fluxo</button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {showTemplates && (
          <div className="templates-panel">
            <h3>Templates prontos</h3>
            <p className="muted">Escolha um template para comecar rapido</p>
            <div className="templates-grid">
              {templates.map((tpl) => (
                <div key={tpl.id} className="template-card" onClick={() => applyTemplate(tpl.id)}>
                  <h4>{tpl.name}</h4>
                  <p>{tpl.description}</p>
                  <span className="tag">{tpl.category}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {loading && <p className="muted">Carregando fluxos...</p>}

        {!loading && !error && workflows.length === 0 && !showTemplates && (
          <div className="empty">
            <p>Nenhum fluxo ainda.</p>
            <p>Crie o primeiro ou escolha um template.</p>
            <div className="btn-group" style={{ marginTop: 12 }}>
              <button className="btn secondary" onClick={() => setShowTemplates(true)}>Templates</button>
              <button className="btn primary" onClick={createNew}>+ Criar fluxo</button>
            </div>
          </div>
        )}

        {!showTemplates && (
          <div className="wf-grid">
            {workflows.map((wf) => (
              <div key={wf.id} className="wf-card" onClick={() => navigate(`/editor/${wf.id}`)}>
                <h3>{wf.name}</h3>
                <p>{wf.description || "Sem descricao"}</p>
                <div className="wf-meta">
                  <button
                    className={`btn small ${wf.active ? "ghost" : "secondary"}`}
                    onClick={(e) => toggleActive(wf, e)}
                    title={wf.active ? "Desativar" : "Ativar"}
                  >
                    {wf.active ? "Ativo" : "Inativo"}
                  </button>
                  <button className="btn ghost small" onClick={(e) => duplicate(wf.id, e)}>Duplicar</button>
                  <button className="btn ghost small danger" onClick={(e) => remove(wf.id, e)}>Excluir</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
