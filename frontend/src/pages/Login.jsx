import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Alert, Icon } from "../components/ui";

const FEATURES = [
  ["zap", "Responda no WhatsApp 24h", "Fluxos visuais conectam a IA ao número, com encaminhamento para humanos."],
  ["cpu", "Base de conhecimento própria", "A IA responde usando seus documentos, com contexto real do seu negócio."],
  ["bar-chart", "Painel completo", "Conversas, leads, setores e histórico de execuções em um só lugar."],
];

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  const fields =
    mode === "register"
      ? [
          ["company_name", "Nome da empresa", "text", "organization"],
          ["name", "Seu nome", "text", "name"],
          ["email", "Email", "email", "email"],
          ["password", "Senha", "password", "new-password"],
        ]
      : mode === "forgot"
        ? [["email", "Email", "email", "email"]]
        : [
            ["username", "Email", "email", "username"],
            ["password", "Senha", "password", "current-password"],
          ];

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function switchMode(next) {
    setMode(next);
    setError("");
    setInfo("");
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(form.username, form.password);
        navigate("/");
      } else if (mode === "register") {
        await register(form);
        navigate("/");
      } else {
        await api.forgotPassword(form.email);
        setInfo("Se o email estiver cadastrado, você receberá um link de recuperação.");
        setForm({});
      }
    } catch (err) {
      setError(err.message || "Erro ao autenticar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="auth-brand">
          <div className="auth-logo-badge"><Icon name="bot" size={22} /></div>
          <div className="logo">Flow<span>AI</span></div>
        </div>
        <h1>Automação de atendimento com IA</h1>
        <p className="muted">
          Conecte seu WhatsApp e deixe a IA atender seus clientes com fluxos
          visuais, base de conhecimento e encaminhamento para humanos.
        </p>
        <ul className="auth-features">
          {FEATURES.map(([icon, title, text]) => (
            <li key={title}>
              <span aria-hidden="true"><Icon name={icon} size={18} /></span>
              <div>
                <b>{title}</b>
                <br />
                {text}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="auth-card">
        <div className="auth-brand">
          <div className="logo">Flow<span>AI</span></div>
          <p className="subtitle">
            {mode === "login"
              ? "Entre com sua conta"
              : mode === "register"
                ? "Crie a conta da sua empresa"
                : "Recupere seu acesso"}
          </p>
        </div>

        <div className="tabs">
          <button className={mode === "login" ? "tab active" : "tab"} onClick={() => switchMode("login")}>
            Entrar
          </button>
          <button className={mode === "register" ? "tab active" : "tab"} onClick={() => switchMode("register")}>
            Criar conta
          </button>
        </div>

        <form onSubmit={onSubmit}>
          {fields.map(([key, label, type, autocomplete]) => (
            <label key={key} className="field">
              <span>{label}</span>
              <input
                type={type || "text"}
                value={form[key] || ""}
                onChange={(e) => set(key, e.target.value)}
                autoComplete={autocomplete}
                minLength={key === "password" ? 6 : undefined}
                required
                autoFocus={key === fields[0][0]}
              />
            </label>
          ))}

          {mode === "register" && (
            <p className="field-help">
              A senha deve ter pelo menos 6 caracteres. Depois de criar a conta,
              conecte o WhatsApp na tela seguinte.
            </p>
          )}

          {info && <Alert variant="success">{info}</Alert>}
          {error && <Alert variant="error">{error}</Alert>}

          <button className="btn primary block" disabled={loading}>
            {loading
              ? "Aguarde..."
              : mode === "login"
                ? "Entrar"
                : mode === "forgot"
                  ? "Enviar link"
                  : "Criar conta"}
          </button>

          {mode === "login" && (
            <p className="muted auth-link">
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); switchMode("forgot"); }}
              >
                Esqueci minha senha
              </a>
            </p>
          )}
          {mode === "forgot" && (
            <p className="muted auth-link">
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); switchMode("login"); }}
              >
                Voltar para o login
              </a>
            </p>
          )}
        </form>
      </div>
    </div>
  );
}