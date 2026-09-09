import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Header from "../components/Header";
import { PageHeader, Alert, Icon, EmptyState, ConfirmDialog, Skeleton } from "../components/ui";

export default function Home() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTemplates, setShowTemplates] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    try {
      const [wfRes, tplData] = await Promise.all([
        api.getWorkflows(),
        api.getTemplates(),
      ]);
      setWorkflows(wfRes.items || []);
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

  async function remove(id) {
    setDeleting(true);
    try {
      await api.deleteWorkflow(id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      setError("Erro ao excluir: " + e.message);
      setConfirmDelete(null);
    } finally {
      setDeleting(false);
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

  const activeMessageFlows = workflows.filter((wf) => wf.active && wf.trigger_type === "message");
  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader title="Fluxos de automação" subtitle="Crie, organize e acompanhe seus fluxos de atendimento.">
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setShowTemplates(!showTemplates)}>
              {showTemplates ? "Fechar" : "Templates"}
            </button>
            <button className="btn primary" onClick={createNew}>+ Novo fluxo</button>
          </div>
        </PageHeader>

        {error && <Alert variant="error" onDismiss={() => setError("")}>{error}</Alert>}

        {activeMessageFlows.length > 1 && (
          <div className="notice">
            Existem {activeMessageFlows.length} fluxos de mensagem ativos. Ative o fluxo principal desejado para desativar os demais.
          </div>
        )}

        {showTemplates && (
          <div className="templates-panel">
            <h3>Templates prontos</h3>
            <p className="muted">Escolha um template para começar rápido</p>
            <div className="templates-grid">
              {templates.map((tpl) => (
                <button key={tpl.id} type="button" className="template-card" onClick={() => applyTemplate(tpl.id)}>
                  <h4>{tpl.name}</h4>
                  <p>{tpl.description}</p>
                  <span className="tag">{tpl.category}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && <Skeleton variant="cards" />}

        {!loading && !error && workflows.length === 0 && !showTemplates && (
          <EmptyState
            icon={<Icon name="workflow" size={40} />}
            title="Nenhum fluxo ainda"
            action={
              <div className="btn-group">
                <button className="btn secondary" onClick={() => setShowTemplates(true)}>Templates</button>
                <button className="btn primary" onClick={createNew}>+ Criar fluxo</button>
              </div>
            }
          >
            Crie o primeiro ou escolha um template.
          </EmptyState>
        )}

        {!showTemplates && (
          <div className="wf-grid">
            {workflows.map((wf) => (
              <button
                key={wf.id}
                type="button"
                className="wf-card"
                onClick={() => navigate(`/editor/${wf.id}`)}
              >
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
                  <button className="btn ghost small" onClick={(e) => duplicate(wf.id, e)}>Duplicar</button>
                  <button className="btn ghost small danger" onClick={() => setConfirmDelete(wf)}>Excluir</button>
                </div>
              </button>
            ))}
          </div>
        )}

        {confirmDelete && (
          <ConfirmDialog
            title="Excluir fluxo"
            message={`Excluir o fluxo "${confirmDelete.name}"?`}
            confirmLabel="Excluir"
            loading={deleting}
            onConfirm={() => remove(confirmDelete.id)}
            onCancel={() => setConfirmDelete(null)}
          />
        )}
      </main>
    </div>
  );
}
