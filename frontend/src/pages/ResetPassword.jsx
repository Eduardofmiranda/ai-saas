import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import Alert from "../components/ui/Alert";

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
      setError("As senhas não conferem");
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
        <div className="auth-brand">
          <div className="logo">Flow<span>AI</span></div>
          <p className="subtitle">Redefinir senha</p>
        </div>

        {!token ? (
          <p className="muted">Link de recuperação inválido ou ausente.</p>
        ) : done ? (
          <>
            <p className="muted">Senha redefinida com sucesso. Faça login com a nova senha.</p>
            <button className="btn primary block" onClick={() => navigate("/login")}>
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
                autoComplete="new-password"
              />
            </label>
            <label className="field">
              <span>Confirmar nova senha</span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            {error && <Alert variant="error">{error}</Alert>}
            <button className="btn primary block" disabled={loading}>
              {loading ? "Aguarde..." : "Redefinir senha"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}