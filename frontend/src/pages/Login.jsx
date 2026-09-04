import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

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
          ["company_name", "Nome da empresa"],
          ["name", "Seu nome"],
          ["email", "Email"],
          ["password", "Senha"],
        ]
      : mode === "forgot"
        ? [["email", "Email"]]
        : [
            ["username", "Email"],
            ["password", "Senha"],
          ];

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
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
        setInfo("Se o email estiver cadastrado, voce recebera um link de recuperacao.");
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
      <div className="auth-card">
        <h1 className="logo">Flow<span>AI</span></h1>
        <p className="subtitle">Automação de atendimento com IA</p>

        <div className="tabs">
          <button className={mode === "login" ? "tab active" : "tab"}
                  onClick={() => { setMode("login"); setError(""); setInfo(""); }}>Entrar</button>
          <button className={mode === "register" ? "tab active" : "tab"}
                  onClick={() => { setMode("register"); setError(""); setInfo(""); }}>Criar conta</button>
        </div>

        <form onSubmit={onSubmit}>
          {fields.map(([key, label]) => (
            <label key={key} className="field">
              <span>{label}</span>
              <input
                type={key === "password" ? "password" : "text"}
                value={form[key] || ""}
                onChange={(e) => set(key, e.target.value)}
                required
              />
            </label>
          ))}
          {info && <div className="notice" style={{ marginBottom: 12 }}>{info}</div>}
          {error && <div className="error">{error}</div>}
          <button className="btn primary" disabled={loading}>
            {loading
              ? "Aguarde..."
              : mode === "login"
                ? "Entrar"
                : mode === "forgot"
                  ? "Enviar link"
                  : "Criar conta"}
          </button>
          {mode === "login" && (
            <p className="muted" style={{ textAlign: "center", marginTop: 12, fontSize: 13 }}>
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); setMode("forgot"); setError(""); setInfo(""); }}
              >
                Esqueci minha senha
              </a>
            </p>
          )}
          {mode === "forgot" && (
            <p className="muted" style={{ textAlign: "center", marginTop: 12, fontSize: 13 }}>
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); setMode("login"); setError(""); setInfo(""); }}
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
