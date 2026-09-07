import { useEffect, useState } from "react";
import Header from "../components/Header";
import { api } from "../api";

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

  async function load() {
    setError("");
    try {
      const [nextOverview, nextProviders, nextUsers] = await Promise.all([
        api.getPlatformOverview(), api.getPlatformProviders(), api.getPlatformUsers(),
      ]);
      setOverview(nextOverview);
      setProviders(nextProviders);
      setUsers(nextUsers);
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

  return <div className="layout">
    <Header />
    <main className="content platform-admin">
      <div className="content-head">
        <div><h2>Administração da Plataforma</h2><p className="muted">Visão global restrita ao operador. A administração comum continua isolada por empresa.</p></div>
        <button className="btn ghost" onClick={load}>Atualizar dados</button>
      </div>
      {error && <div className="error">{error}</div>}
      {message && <div className="success-msg">{message}</div>}
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
      <section className="ai-config"><h3>Usuários de todas as empresas</h3><p className="muted">Esta lista mostra contas cadastradas; ela não indica sessão ativa, pois o sistema ainda não possui rastreamento confiável de sessões.</p>
        <div className="platform-user-list">{users.map((user) => <div key={user.id} className="platform-user-row"><div><strong>{user.name}</strong><span>{user.email}</span></div><div><strong>{user.company_name}</strong><span>{user.role}{user.is_platform_admin ? " · operador da plataforma" : ""}</span></div></div>)}</div>
      </section>
    </main>
  </div>;
}

function Kpi({ label: title, value }) { return <div className="kpi-card"><div className="kpi-value">{value ?? 0}</div><div className="kpi-label">{title}</div></div>; }