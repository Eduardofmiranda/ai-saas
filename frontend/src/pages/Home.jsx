import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Header from "../components/Header";
import { PageHeader, Alert, Icon, EmptyState, ConfirmDialog, Skeleton, Pagination } from "../components/ui";
import { BarChart, StackedBarChart } from "../components/charts";

const PAGE_SIZE = 100;

export default function Home() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTemplates, setShowTemplates] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [metricsWf, setMetricsWf] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  async function load() {
    try {
      const [wfRes, tplData] = await Promise.all([
        api.getWorkflows({ q, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
        api.getTemplates(),
      ]);
      setWorkflows(wfRes.items || []);
      setTotal(wfRes.total || 0);
      setTemplates(tplData);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [q, page]);

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

  async function openMetrics(wf, e) {
    e.stopPropagation();
    setMetricsWf(wf);
    setMetricsLoading(true);
    setMetricsData(null);
    try {
      const data = await api.getWorkflowMetrics(wf.id);
      setMetricsData(data);
    } catch (err) {
      setError("Erro ao carregar metricas: " + err.message);
      setMetricsWf(null);
    } finally {
      setMetricsLoading(false);
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

        {!loading && !showTemplates && (
          <div className="list-toolbar">
            <input
              className="list-search"
              placeholder="Filtrar fluxos por nome..."
              aria-label="Filtrar fluxos por nome"
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(0); }}
            />
          </div>
        )}

        {!loading && !error && workflows.length === 0 && !showTemplates && (
          <EmptyState
            icon={<Icon name="workflow" size={40} />}
            title={q ? "Nenhum fluxo encontrado" : "Nenhum fluxo ainda"}
            action={
              q ? (
                <button className="btn ghost" onClick={() => { setQ(""); setPage(0); }}>
                  Limpar filtro
                </button>
              ) : (
                <div className="btn-group">
                  <button className="btn secondary" onClick={() => setShowTemplates(true)}>Templates</button>
                  <button className="btn primary" onClick={createNew}>+ Criar fluxo</button>
                </div>
              )
            }
          >
            {q ? "Nenhum fluxo corresponde ao filtro informado." : "Crie o primeiro ou escolha um template."}
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
                  <button className="btn ghost small" onClick={(e) => openMetrics(wf, e)}>Metricas</button>
                  <button className="btn ghost small" onClick={(e) => duplicate(wf.id, e)}>Duplicar</button>
                  <button className="btn ghost small danger" onClick={() => setConfirmDelete(wf)}>Excluir</button>
                </div>
              </button>
            ))}
          </div>
        )}

        {!showTemplates && total > PAGE_SIZE && (
          <Pagination total={total} page={page} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="fluxo(s)" />
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

        {metricsWf && (
          <div className="modal-overlay" onClick={() => { setMetricsWf(null); setMetricsData(null); }}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Metricas — {metricsWf.name}</h2>
                <button className="btn ghost small" onClick={() => { setMetricsWf(null); setMetricsData(null); }}>Fechar</button>
              </div>
              {metricsLoading && <Skeleton variant="lines" />}
              {metricsData && (
                <div className="modal-body wf-metrics">
                  <div className="dash-cards">
                    <div className="kpi">
                      <span className="kpi-label">Execucoes</span>
                      <span className="kpi-value">{metricsData.executions_total}</span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Taxa de sucesso</span>
                      <span className="kpi-value" style={{ color: metricsData.success_rate >= 80 ? "var(--green)" : metricsData.success_rate >= 50 ? "var(--yellow, #eab308)" : "var(--red)" }}>
                        {metricsData.success_rate}%
                      </span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Duracao media</span>
                      <span className="kpi-value">{metricsData.avg_duration_seconds > 0 ? `${metricsData.avg_duration_seconds}s` : "—"}</span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Erros</span>
                      <span className="kpi-value" style={{ color: metricsData.executions_error > 0 ? "var(--red)" : "var(--muted)" }}>{metricsData.executions_error}</span>
                    </div>
                  </div>

                  <h3>Execucoes · ultimos 30 dias</h3>
                  <div className="chart-card chart-wide">
                    <div className="chart-card-body" style={{ display: "block" }}>
                      <StackedBarChart
                        labelEvery={5}
                        height={150}
                        data={(metricsData.executions_last_30_days || []).map((d) => ({
                          key: d.date,
                          label: d.date.split("-").slice(1).reverse().join("/"),
                          success: d.success,
                          error: d.error,
                        }))}
                      />
                    </div>
                  </div>

                  {metricsData.node_usage && metricsData.node_usage.length > 0 && (
                    <>
                      <h3>Uso por node</h3>
                      <div className="dash-list">
                        {metricsData.node_usage.map((n, i) => (
                          <div key={n.node_id} className="dash-list-row">
                            <span className="dash-rank">{i + 1}</span>
                            <span className="dash-name">{n.node_id}</span>
                            <span className="dash-meta">{n.executions} execucoes{n.errors > 0 ? ` · ${n.errors} erros` : ""}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
