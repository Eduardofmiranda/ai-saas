import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const fields =
    mode === "register"
      ? [
          ["company_name", "Nome da empresa"],
          ["name", "Seu nome"],
          ["email", "Email"],
          ["password", "Senha"],
        ]
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
    setLoading(true);
    try {
      if (mode === "login") {
        await login(form.username, form.password);
      } else {
        await register(form);
      }
      navigate("/");
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
                  onClick={() => { setMode("login"); setError(""); }}>Entrar</button>
          <button className={mode === "register" ? "tab active" : "tab"}
                  onClick={() => { setMode("register"); setError(""); }}>Criar conta</button>
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
          {error && <div className="error">{error}</div>}
          <button className="btn primary" disabled={loading}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
          </button>
        </form>
      </div>
    </div>
  );
}
