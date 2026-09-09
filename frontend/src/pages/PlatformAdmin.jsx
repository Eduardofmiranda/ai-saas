import { useEffect, useState } from "react";
import Header from "../components/Header";
import { api } from "../api";
import Alert from "../components/ui/Alert";
import Modal from "../components/ui/Modal";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import PageHeader from "../components/ui/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import Skeleton from "../components/ui/Skeleton";
import { avatarColor } from "../utils/format";

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

const ROLE_LABELS = { owner: "Dono", admin: "Admin", agent: "Atendente" };

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
  const [errorsLoaded, setErrorsLoaded] = useState(false);
  const [errorsPage, setErrorsPage] = useState(0);
  const [confirmClearErrors, setConfirmClearErrors] = useState(false);
  const ERRORS_PAGE = 20;
  const [tab, setTab] = useState("overview");
  // Redefinicao de senha (operador)
  const [resetTarget, setResetTarget] = useState(null);
  const [resetResult, setResetResult] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [copied, setCopied] = useState(false);

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

  useEffect(() => {
    if (tab === "errors" && !errorsLoaded && !errorsLoading) loadErrors(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

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
      setErrorsLoaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setErrorsLoading(false);
    }
  }

  async function clearErrors() {
    setErrorsLoading(true);
    try {
      const res = await api.clearPlatformErrors();
      setMessage(`${res.deleted} erro(s) removido(s).`);
      setErrors([]);
      setErrorsTotal(0);
      setConfirmClearErrors(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setErrorsLoading(false);
    }
  }

  // --- Redefinicao de senha de usuario ---
  function openResetPassword(user) {
    setResetTarget(user);
    setResetResult(null);
    setCopied(false);
    setError("");
  }

  function closeResetModal() {
    if (resetLoading) return;
    setResetTarget(null);
    setResetResult(null);
    setCopied(false);
  }

  async function generateNewPassword() {
    if (!resetTarget || resetLoading) return;
    setResetLoading(true);
    setError("");
    try {
      const res = await api.resetUserPassword(resetTarget.id);
      setResetResult(res);
      setMessage("");
    } catch (err) {
      setError(err.message);
    } finally {
      setResetLoading(false);
    }
  }

  async function copyTemporaryPassword() {
    if (!resetResult?.temporary_password) return;
    const text = resetResult.temporary_password;
    setError("");
    try {
      const copied = copyToClipboard(text);
      if (!copied) throw new Error("copy unavailable");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError("Não foi possível copiar automaticamente. Selecione a senha e copie manualmente.");
    }
  }

  const providerCards = providers.length
    ? providers.map((provider) => {
        const form = forms[provider.provider] || {};
        const balance = balances[provider.provider];
        return (
          <div className="platform-provider" key={provider.provider}>
            <div className="platform-provider-head">
              <strong>{label(provider.provider)}</strong>
              <span className={provider.has_api_key ? "state-pill open" : "state-pill closed"}>
                {provider.has_api_key ? "Chave cadastrada" : "Sem chave"}
              </span>
            </div>

            <label className="field">
              <span>Modelo padrão</span>
              <input className="input" value={form.model || ""} onChange={(e) => set(provider.provider, "model", e.target.value)} placeholder="ex.: gpt-4o-mini" />
            </label>
            <label className="field">
              <span>URL base (opcional)</span>
              <input className="input" value={form.base_url || ""} onChange={(e) => set(provider.provider, "base_url", e.target.value)} placeholder="Use a URL oficial se vazio" />
            </label>
            <label className="field">
              <span>Nova chave de API</span>
              <input className="input" type="password" value={form.api_key || ""} onChange={(e) => set(provider.provider, "api_key", e.target.value)} placeholder={provider.has_api_key ? "Deixe vazio para manter a atual" : "Cole a chave aqui"} />
            </label>
            <label className="toggle">
              <input type="checkbox" checked={Boolean(form.enabled)} onChange={(e) => set(provider.provider, "enabled", e.target.checked)} />
              <span>Disponível para empresas</span>
            </label>

            <div className="btn-group">
              <button className="btn primary" disabled={saving === provider.provider} onClick={() => saveProvider(provider.provider)}>
                {saving === provider.provider ? "Salvando..." : "Salvar"}
              </button>
              {provider.provider === "deepseek" && provider.has_api_key && (
                <button className="btn ghost small" disabled={saving !== ""} onClick={() => checkBalance(provider.provider)}>Consultar saldo</button>
              )}
            </div>
            {balance && (
              <p className="field-help">
                {balance.balances ? balance.balances.map((item) => `${item.total_balance} ${item.currency}`).join(" · ") : balance.detail}
              </p>
            )}
          </div>
        );
      })
    : null;

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader
          title="Administração da Plataforma"
          subtitle="Visão global restrita ao operador. A administração comum continua isolada por empresa."
        >
          <button className="btn ghost" onClick={load}>Atualizar dados</button>
        </PageHeader>

        <div className="seg-tabs">
          <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>Visão geral</button>
          <button className={tab === "errors" ? "active" : ""} onClick={() => setTab("errors")}>Painel de Erros</button>
        </div>

        {error && <Alert variant="error">{error}</Alert>}
        {message && (
          <Alert variant="success" onDismiss={() => setMessage("")}>
            {message}
          </Alert>
        )}

        {tab === "overview" && (
          <>
            {!overview ? (
              <div className="card"><Skeleton /></div>
            ) : (
              <>
                <div className="stat-grid">
                  <StatCard icon="building" value={overview.companies} label="Empresas" />
                  <StatCard icon="users" value={overview.users} label="Usuários cadastrados" />
                  <StatCard icon="workflow" value={overview.workflows} label="Workflows" />
                  <StatCard icon="x-circle" value={overview.executions_error} label="Execuções com erro" tone="red" />
                </div>

                <section className="ai-config">
                  <h3>Uso e sessões</h3>
                  <p className="muted">
                    Tokens consumidos pela aplicação e sessões ativas ainda não são rastreados pelo sistema atual.
                    O painel não exibirá estimativas inventadas: o saldo do DeepSeek é consultado na fonte oficial
                    e os demais provedores dependem de APIs próprias.
                  </p>
                </section>
              </>
            )}

            <section className="ai-config">
              <h3>Credenciais globais de IA</h3>
              <p className="muted">
                Cadastre uma chave por provedor. Empresas que escolherem esse provedor usam essa chave, salvo se
                possuírem uma chave própria legada. A chave fica cifrada no banco e não pode ser lida pela tela.
              </p>
              <div className="platform-provider-grid">
                {providerCards || <Skeleton />}
              </div>
            </section>

            <section className="ai-config">
              <h3>Política de IA por usuário</h3>
              <p className="muted">Defina quais provedores e modelos cada usuário pode utilizar. O usuário comum só visualiza as opções liberadas.</p>

              {editingUser && (
                <div className="platform-form-card">
                  <div className="platform-provider-head">
                    <strong>Editar: {editingUser.name}</strong>
                    <span className="muted">{editingUser.email}</span>
                  </div>
                  <label className="field">
                    <span>Provedores liberados</span>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                      {PROVIDERS.map((p) => (
                        <button
                          key={p.value}
                          type="button"
                          style={{ font: "inherit" }}
                          className={`provider-chip ${userForm.allowed_providers.includes(p.value) ? "on" : ""}`}
                          onClick={() => toggleProvider(p.value)}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </label>
                  {userForm.allowed_providers.length > 0 && (
                    <>
                      <label className="field">
                        <span>Provedor padrão</span>
                        <select value={userForm.default_provider} onChange={(e) => {
                          const dp = e.target.value;
                          const models = MODELS[dp] || [];
                          setUserForm((f) => ({ ...f, default_provider: dp, default_model: models[0] || "" }));
                        }}>
                          {userForm.allowed_providers.map((p) => <option key={p} value={p}>{label(p)}</option>)}
                        </select>
                      </label>
                      <label className="field">
                        <span>Modelo padrão</span>
                        <select value={userForm.default_model} onChange={(e) => setUserForm((f) => ({ ...f, default_model: e.target.value }))}>
                          {(MODELS[userForm.default_provider] || []).map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </label>
                    </>
                  )}
                  <div className="btn-group">
                    <button className="btn primary" disabled={saving === "user-" + editingUser.id} onClick={saveUserConfig}>
                      {saving === "user-" + editingUser.id ? "Salvando..." : "Salvar política"}
                    </button>
                    <button className="btn ghost" onClick={() => setEditingUser(null)}>Cancelar</button>
                  </div>
                </div>
              )}

              <div className="platform-user-list">
                {users.length === 0 && <Skeleton variant="cards" cards={3} />}
                {users.map((user) => {
                  const cfg = getUserConfig(user);
                  return (
                    <div key={"policy-" + user.id} className="platform-user-row">
                      <div className="user-main">
                        <span className="avatar-sm" style={{ background: avatarColor(user.name) }}>{(user.name || "?").charAt(0).toUpperCase()}</span>
                        <div>
                          <strong>{user.name}</strong>
                          <span>{user.email}</span>
                        </div>
                      </div>
                      <div className="user-meta">
                        {cfg && cfg.allowed_providers.length > 0
                          ? <span>{cfg.allowed_providers.map(label).join(", ")} · padrão {label(cfg.default_provider)}/{cfg.default_model}</span>
                          : <span>Sem política (usa empresa/.env)</span>}
                        <button className="btn ghost small" onClick={() => openUserConfig(user)}>Editar</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="ai-config">
              <h3>Usuários de todas as empresas</h3>
              <p className="muted">
                Esta lista mostra contas cadastradas; ela não indica sessão ativa, pois o sistema ainda não possui
                rastreamento confiável de sessões.
              </p>
              <div className="platform-user-list">
                {users.map((user) => (
                  <div key={"all-" + user.id} className="platform-user-row">
                    <div className="user-main">
                      <span className="avatar-sm" style={{ background: avatarColor(user.name) }}>{(user.name || "?").charAt(0).toUpperCase()}</span>
                      <div>
                        <strong>{user.name}</strong>
                        <span>{user.email}</span>
                      </div>
                    </div>
                    <div className="user-meta">
                      <strong>{user.company_name}</strong>
                      <span className={`role-chip role-${user.role}`}>{ROLE_LABELS[user.role] || user.role}</span>
                      {user.is_platform_admin && <span className="role-chip role-platform">Plataforma</span>}
                      <button className="btn ghost small" onClick={() => openResetPassword(user)}>
                        Redefinir senha
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {tab === "errors" && (
          <section className="ai-config">
            <div className="platform-provider-head">
              <div>
                <h3 style={{ margin: 0 }}>Painel de Erros</h3>
                <p className="muted" style={{ margin: "4px 0 0" }}>Execuções que falharam: erro, workflow, empresa e data/hora.</p>
              </div>
              <div className="btn-group">
                <button className="btn ghost" onClick={() => loadErrors(0)} disabled={errorsLoading}>
                  {errorsLoading ? "Carregando..." : "Atualizar"}
                </button>
                {errorsTotal > 0 && (
                  <button className="btn ghost danger" onClick={() => setConfirmClearErrors(true)} disabled={errorsLoading}>
                    Limpar todos os erros
                  </button>
                )}
              </div>
            </div>

            {errorsLoading && <p className="muted" style={{ marginTop: 12 }}>Carregando erros...</p>}

            {!errorsLoading && errors.length === 0 && (
              <EmptyState
                icon={<Icon name="check-circle" size={40} />}
                title="Nenhum erro registrado"
              >
                Quando uma execução falhar, ela aparecerá aqui com detalhes para diagnóstico.
              </EmptyState>
            )}

            {errors.length > 0 && (
              <>
                <div className="card" style={{ padding: 0, overflow: "hidden", marginTop: 14 }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th style={{ width: 70 }}>ID</th>
                        <th>Empresa</th>
                        <th>Workflow</th>
                        <th>Erro</th>
                        <th style={{ width: 150 }}>Quando</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errors.map((e) => (
                        <tr key={e.id}>
                          <td className="u-mono">#{e.id}</td>
                          <td>{e.company_name}</td>
                          <td>{e.workflow_name}</td>
                          <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={e.error}>{e.error}</td>
                          <td>{e.created_at ? new Date(e.created_at).toLocaleString("pt-BR") : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <span className="pageno">{errorsTotal} erro{errorsTotal !== 1 ? "s" : ""} no total</span>
                  <div className="btn-group">
                    <button className="btn ghost small" disabled={errorsPage === 0 || errorsLoading} onClick={() => loadErrors(errorsPage - 1)}>Anterior</button>
                    <span className="pageno">Página {errorsPage + 1} de {Math.ceil(errorsTotal / ERRORS_PAGE)}</span>
                    <button className="btn ghost small" disabled={(errorsPage + 1) * ERRORS_PAGE >= errorsTotal || errorsLoading} onClick={() => loadErrors(errorsPage + 1)}>Próxima</button>
                  </div>
                </div>
              </>
            )}
          </section>
        )}
      </main>

      {confirmClearErrors && (
        <ConfirmDialog
          title="Limpar erros"
          confirmLabel="Apagar tudo"
          loading={errorsLoading}
          onConfirm={clearErrors}
          onCancel={() => setConfirmClearErrors(false)}
          message={
            <>
              <p style={{ margin: 0, lineHeight: 1.5 }}>
                Tem certeza que deseja apagar <strong>TODOS os erros ({errorsTotal})</strong>?
              </p>
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>Esta ação não pode ser desfeita.</p>
            </>
          }
        />
      )}

      {resetTarget && (
        <Modal
          title={resetResult ? "Senha redefinida" : "Redefinir senha"}
          onClose={closeResetModal}
          footer={
            resetResult ? (
              <button className="btn primary" onClick={closeResetModal}>Fechar</button>
            ) : (
              <>
                <button className="btn ghost" onClick={closeResetModal}>Cancelar</button>
                <button className="btn primary" onClick={generateNewPassword} disabled={resetLoading}>
                  {resetLoading ? "Gerando..." : "Gerar nova senha"}
                </button>
              </>
            )
          }
        >
          {resetResult ? (
            <>
              <p style={{ margin: 0, lineHeight: 1.5 }}>
                A senha provisória de <strong>{resetResult.name}</strong> é:
              </p>
              <div className="temp-password-box">
                <code>{resetResult.temporary_password}</code>
                <button className="btn ghost small" onClick={copyTemporaryPassword}>
                  <Icon name="copy" size={14} /> {copied ? "Copiada!" : "Copiar"}
                </button>
              </div>
              <p className="muted" style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>
                Esta senha é exibida apenas agora. Envie ao usuário com segurança —
                ele pode trocá-la em <strong>Conta</strong> após o login.
              </p>
            </>
          ) : (
            <>
              <p style={{ margin: 0, lineHeight: 1.5 }}>
                Gerar uma nova senha provisória para <strong>{resetTarget.name}</strong>{" "}
                ({resetTarget.email})?
              </p>
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>
                A senha atual deixará de funcionar imediatamente para o acesso
                pelo login.
              </p>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}

function StatCard({ icon, value, label: title, tone = "" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <span className="stat-icon"><Icon name={icon} size={21} /></span>
      <div>
        <div className="stat-value">{value ?? 0}</div>
        <div className="stat-label">{title}</div>
      </div>
    </div>
  );
}

function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).catch(() => {});
    return true;
  }
  try {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.top = "-9999px";
    el.style.opacity = "0";
    document.body.appendChild(el);
    const range = document.createRange();
    range.selectNodeContents(el);
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch (err) {
    return false;
  }
}