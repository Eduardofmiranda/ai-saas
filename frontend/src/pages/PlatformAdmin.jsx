import { useEffect, useState } from "react";
import Header from "../components/Header";
import { api } from "../api";

const PROVIDERS = [
  { value: "groq", label: "Groq" },
  { value: "openai", label: "OpenAI" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "mistral", label: "Mistral" },
  { value: "ollama", label: "Ollama" },
  { value: "mock", label: "Demonstração" },
];

const MODELS = {
  groq: ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "qwen/qwen3.8-27b"],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
  deepseek: ["deepseek-v4-flash", "deepseek-v4-pro"],
  mistral: ["mistral-large-latest", "mistral-small-latest"],
  ollama: ["llama3.1", "mistral", "codellama"],
  mock: ["mock-response"],
};

const label = (value) => ({ groq: "Groq", openai: "OpenAI", deepseek: "DeepSeek", mistral: "Mistral", ollama: "Ollama", mock: "Demonstração" }[value] || value);

export default function PlatformAdmin() {
  const [overview, setOverview] = useState(null);
  const [providers, setProviders] = useState([]);
  const [users, setUsers] = useState([]);
  const [forms, setForms] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState("");
  const [balances, setBalances] = useState({});
  // Politica de IA por usuario
  const [userConfigs, setUserConfigs] = useState([]);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({ allowed_providers: [], default_provider: "", default_model: "" });
  // Painel de erros
  const [errors, setErrors] = useState([]);
  const [errorsTotal, setErrorsTotal] = useState(0);
  const [errorsLoading, setErrorsLoading] = useState(false);
  const [errorsPage, setErrorsPage] = useState(0);
  const ERRORS_PAGE = 20;
  const [tab, setTab] = useState("overview");

  async function load() {
    setError("");
    try {
      const [nextOverview, nextProviders, nextUsers, nextUserConfigs] = await Promise.all([
        api.getPlatformOverview(), api.getPlatformProviders(), api.getPlatformUsers(),
        api.getUserAIConfigs(),
      ]);
      setOverview(nextOverview);
      setProviders(nextProviders);
      setUsers(nextUsers);
      setUserConfigs(nextUserConfigs);
      setForms(Object.fromEntries(nextProviders.map((item) => [item.provider, {
        model: item.model || "", base_url: item.base_url || "", enabled: item.enabled, api_key: "",
      }])));
    } catch (err) {
      setError(err.message || "Não foi possível carregar a administração da plataforma.");
    }
  }

  useEffect(() => { load(); }, []);

  function set(provider, field, value) {
    setForms((current) => ({ ...current, [provider]: { ...current[provider], [field]: value, ...(field === "api_key" && value.trim() ? { enabled: true } : {}) } }));
  }

  async function saveProvider(provider) {
    setSaving(provider); setMessage(""); setError("");
    try {
      await api.updatePlatformProvider(provider, forms[provider]);
      setMessage(`${label(provider)} salvo. A chave não é exibida nem enviada de volta ao navegador.`);
      await load();
    } catch (err) { setError(err.message); }
    finally { setSaving(""); }
  }

  async function checkBalance(provider) {
    setError("");
    try {
      const result = await api.getPlatformProviderBalance(provider);
      setBalances((current) => ({ ...current, [provider]: result }));
    } catch (err) { setError(err.message); }
  }

  // --- Politica de IA por usuario ---
  function openUserConfig(user) {
    const existing = userConfigs.find((c) => c.user_id === user.id);
    setEditingUser(user);
    setUserForm({
      allowed_providers: existing?.allowed_providers || [],
      default_provider: existing?.default_provider || "",
      default_model: existing?.default_model || "",
    });
  }

  function toggleProvider(provider) {
    setUserForm((f) => {
      const allowed = f.allowed_providers.includes(provider)
        ? f.allowed_providers.filter((p) => p !== provider)
        : [...f.allowed_providers, provider];
      const default_provider = allowed.includes(f.default_provider) ? f.default_provider : (allowed[0] || "");
      const modelsForDefault = MODELS[default_provider] || [];
      const default_model = modelsForDefault.includes(f.default_model) ? f.default_model : (modelsForDefault[0] || "");
      return { ...f, allowed_providers: allowed, default_provider, default_model };
    });
  }

  async function saveUserConfig() {
    if (!editingUser) return;
    setSaving("user-" + editingUser.id); setMessage(""); setError("");
    try {
      await api.saveUserAIConfig(editingUser.id, userForm);
      setMessage(`Política de IA de ${editingUser.name} salva.`);
      setEditingUser(null);
      await load();
    } catch (err) { setError(err.message); }
    finally { setSaving(""); }
  }

  function getUserConfig(user) {
    return userConfigs.find((c) => c.user_id === user.id);
  }

  async function loadErrors(page = 0) {
    setErrorsLoading(true);
    try {
      const res = await api.getPlatformErrors({ limit: ERRORS_PAGE, offset: page * ERRORS_PAGE });
      setErrors(res.items);
      setErrorsTotal(res.total);
      setErrorsPage(page);
    } catch (err) {
      setError(err.message);
    } finally {
      setErrorsLoading(false);
    }
  }

  async function clearErrors() {
    if (!confirm("Tem certeza que deseja apagar TODOS os erros?")) return;
    setErrorsLoading(true);
    try {
      const res = await api.clearPlatformErrors();
      setMessage(`${res.deleted} erro(s) removido(s).`);
      setErrors([]);
      setErrorsTotal(0);
    } catch (err) {
      setError(err.message);
    } finally {
      setErrorsLoading(false);
    }
  }

  return <div className="layout">
    <Header />
    <main className="content platform-admin">
      <div className="content-head">
        <div><h2>Administração da Plataforma</h2><p className="muted">Visão global restrita ao operador. A administração comum continua isolada por empresa.</p></div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select value={tab} onChange={(e) => setTab(e.target.value)} style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13 }}>
            <option value="overview">Visão geral</option>
            <option value="errors">Painel de Erros</option>
          </select>
          <button className="btn ghost" onClick={load}>Atualizar</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {message && <div className="success-msg">{message}</div>}

      {tab === "overview" && <>
        {!overview ? <p className="muted">Carregando visão geral...</p> : <>
          <div className="kpi-grid">
            <Kpi label="Empresas" value={overview.companies} />
            <Kpi label="Usuários cadastrados" value={overview.users} />
            <Kpi label="Workflows" value={overview.workflows} />
            <Kpi label="Execuções com erro" value={overview.executions_error} />
          </div>
          <div className="ai-config"><h3>Uso e sessões</h3>
            <p className="muted">Tokens consumidos pela aplicação e sessões ativas ainda não são rastreados pelo sistema atual. O painel não exibirá estimativas inventadas: o saldo do DeepSeek é consultado na fonte oficial e os demais provedores dependem de APIs próprias.</p>
          </div>
        </>}
        <section className="ai-config"><h3>Credenciais globais de IA</h3>
          <p className="muted">Cadastre uma chave por provedor. Empresas que escolherem esse provedor usam essa chave, salvo se possuírem uma chave própria legada. A chave fica cifrada no banco e não pode ser lida pela tela.</p>
          <div className="platform-provider-grid">{providers.map((provider) => {
            const form = forms[provider.provider] || {};
            const balance = balances[provider.provider];
            return <div className="platform-provider" key={provider.provider}>
              <div className="platform-provider-head"><strong>{label(provider.provider)}</strong><span className={provider.has_api_key ? "state-pill open" : "state-pill closed"}>{provider.has_api_key ? "Chave cadastrada" : "Sem chave"}</span></div>
              <label className="field"><span>Modelo padrão</span><input value={form.model || ""} onChange={(e) => set(provider.provider, "model", e.target.value)} /></label>
              <label className="field"><span>URL base (opcional)</span><input value={form.base_url || ""} onChange={(e) => set(provider.provider, "base_url", e.target.value)} placeholder="Use a URL oficial se vazio" /></label>
              <label className="field"><span>Nova chave de API</span><input type="password" value={form.api_key || ""} onChange={(e) => set(provider.provider, "api_key", e.target.value)} placeholder={provider.has_api_key ? "Deixe vazio para manter a atual" : "Cole a chave aqui"} /></label>
              <label className="toggle"><input type="checkbox" checked={Boolean(form.enabled)} onChange={(e) => set(provider.provider, "enabled", e.target.checked)} /><span>Disponível para empresas</span></label>
              <div className="btn-group"><button className="btn primary" disabled={saving === provider.provider} onClick={() => saveProvider(provider.provider)}>{saving === provider.provider ? "Salvando..." : "Salvar"}</button>{provider.provider === "deepseek" && provider.has_api_key && <button className="btn ghost" onClick={() => checkBalance(provider.provider)}>Consultar saldo</button>}</div>
              {balance && <p className="field-help">{balance.balances ? balance.balances.map((item) => `${item.total_balance} ${item.currency}`).join(" · ") : balance.detail}</p>}
            </div>;
          })}</div>
        </section>
        <section className="ai-config"><h3>Política de IA por usuário</h3>
          <p className="muted">Defina quais provedores e modelos cada usuário pode utilizar. O usuário comum só visualiza as opções liberadas.</p>
          {editingUser && <div className="platform-provider" style={{ marginBottom: 16 }}>
            <div className="platform-provider-head"><strong>Editar: {editingUser.name}</strong><span>{editingUser.email}</span></div>
            <label className="field"><span>Provedores liberados</span>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                {PROVIDERS.map((p) => (
                  <label key={p.value} className="toggle" style={{ fontSize: 13 }}>
                    <input type="checkbox" checked={userForm.allowed_providers.includes(p.value)} onChange={() => toggleProvider(p.value)} />
                    <span>{p.label}</span>
                  </label>
                ))}
              </div>
            </label>
            {userForm.allowed_providers.length > 0 && <>
              <label className="field"><span>Provedor padrão</span>
                <select value={userForm.default_provider} onChange={(e) => {
                  const dp = e.target.value;
                  const models = MODELS[dp] || [];
                  setUserForm((f) => ({ ...f, default_provider: dp, default_model: models[0] || "" }));
                }}>
                  {userForm.allowed_providers.map((p) => <option key={p} value={p}>{label(p)}</option>)}
                </select>
              </label>
              <label className="field"><span>Modelo padrão</span>
                <select value={userForm.default_model} onChange={(e) => setUserForm((f) => ({ ...f, default_model: e.target.value }))}>
                  {(MODELS[userForm.default_provider] || []).map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </label>
            </>}
            <div className="btn-group">
              <button className="btn primary" disabled={saving === "user-" + editingUser.id} onClick={saveUserConfig}>
                {saving === "user-" + editingUser.id ? "Salvando..." : "Salvar política"}
              </button>
              <button className="btn ghost" onClick={() => setEditingUser(null)}>Cancelar</button>
            </div>
          </div>}
          <div className="platform-user-list">{users.map((user) => {
            const cfg = getUserConfig(user);
            return <div key={user.id} className="platform-user-row">
              <div><strong>{user.name}</strong><span>{user.email}</span></div>
              <div>
                {cfg && cfg.allowed_providers.length > 0
                  ? <span>{cfg.allowed_providers.map(label).join(", ")} · padrão: {label(cfg.default_provider)}/{cfg.default_model}</span>
                  : <span className="muted">Sem política (usa empresa/.env)</span>}
                <button className="btn ghost" style={{ marginLeft: 8, fontSize: 12 }} onClick={() => openUserConfig(user)}>Editar</button>
              </div>
            </div>;
          })}</div>
        </section>
        <section className="ai-config"><h3>Usuários de todas as empresas</h3><p className="muted">Esta lista mostra contas cadastradas; ela não indica sessão ativa, pois o sistema ainda não possui rastreamento confiável de sessões.</p>
          <div className="platform-user-list">{users.map((user) => <div key={user.id} className="platform-user-row"><div><strong>{user.name}</strong><span>{user.email}</span></div><div><strong>{user.company_name}</strong><span>{user.role}{user.is_platform_admin ? " · operador da plataforma" : ""}</span></div></div>)}</div>
        </section>
      </>}

      {tab === "errors" && <section className="ai-config">
        <h3>Painel de Erros</h3>
        <p className="muted">Execuções que falharam. Mostra o erro, workflow, empresa e data/hora.</p>
        <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
          <button className="btn ghost" onClick={() => loadErrors(0)} disabled={errorsLoading}>
            {errorsLoading ? "Carregando..." : errors.length > 0 ? "Atualizar" : "Carregar erros"}
          </button>
          {errorsTotal > 0 && <button className="btn ghost" style={{ color: "#dc2626" }} onClick={clearErrors} disabled={errorsLoading}>
            Limpar todos os erros
          </button>}
        </div>
        {errors.length > 0 && <>
          <p className="muted" style={{ marginBottom: 8 }}>{errorsTotal} erro{errorsTotal !== 1 ? "s" : ""} no total</p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                  <th style={{ padding: "8px 6px" }}>ID</th>
                  <th style={{ padding: "8px 6px" }}>Empresa</th>
                  <th style={{ padding: "8px 6px" }}>Workflow</th>
                  <th style={{ padding: "8px 6px" }}>Erro</th>
                  <th style={{ padding: "8px 6px" }}>Quando</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((e) => (
                  <tr key={e.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                    <td style={{ padding: "6px", fontFamily: "monospace" }}>#{e.id}</td>
                    <td style={{ padding: "6px" }}>{e.company_name}</td>
                    <td style={{ padding: "6px" }}>{e.workflow_name}</td>
                    <td style={{ padding: "6px", maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={e.error}>{e.error}</td>
                    <td style={{ padding: "6px", whiteSpace: "nowrap" }}>{e.created_at ? new Date(e.created_at).toLocaleString("pt-BR") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn ghost" disabled={errorsPage === 0 || errorsLoading} onClick={() => loadErrors(errorsPage - 1)}>Anterior</button>
            <span className="muted">Página {errorsPage + 1} de {Math.ceil(errorsTotal / ERRORS_PAGE)}</span>
            <button className="btn ghost" disabled={(errorsPage + 1) * ERRORS_PAGE >= errorsTotal || errorsLoading} onClick={() => loadErrors(errorsPage + 1)}>Próxima</button>
          </div>
        </>}
        {errors.length === 0 && !errorsLoading && <p className="muted">Nenhum erro registrado. Clique em "Carregar erros" para buscar.</p>}
      </section>}
    </main>
  </div>;
}

function Kpi({ label: title, value }) { return <div className="kpi-card"><div className="kpi-value">{value ?? 0}</div><div className="kpi-label">{title}</div></div>; }