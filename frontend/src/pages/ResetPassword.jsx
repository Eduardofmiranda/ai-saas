import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("A nova senha deve ter pelo menos 6 caracteres");
      return;
    }
    if (password !== confirm) {
      setError("As senhas nao conferem");
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message || "Falha ao redefinir a senha");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1 className="logo">Flow<span>AI</span></h1>
        <p className="subtitle">Redefinir senha</p>

        {!token ? (
          <p className="muted">Link de recuperacao invalido ou ausente.</p>
        ) : done ? (
          <>
            <p className="muted">Senha redefinida com sucesso. Faca login com a nova senha.</p>
            <button className="btn primary" onClick={() => navigate("/login")}>
              Ir para o login
            </button>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <label className="field">
              <span>Nova senha</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Confirmar nova senha</span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </label>
            {error && <div className="error">{error}</div>}
            <button className="btn primary" disabled={loading}>
              {loading ? "Aguarde..." : "Redefinir senha"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}