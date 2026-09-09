import { useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import PageHeader from "../components/ui/PageHeader";

export default function Account() {
  const [form, setForm] = useState({ current_password: "", new_password: "", confirm: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (form.new_password.length < 6) {
      setError("A nova senha deve ter pelo menos 6 caracteres");
      return;
    }
    if (form.new_password !== form.confirm) {
      setError("As senhas não conferem");
      return;
    }
    setLoading(true);
    try {
      await api.changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setMessage("Senha alterada com sucesso.");
      setForm({ current_password: "", new_password: "", confirm: "" });
    } catch (err) {
      setError(err.message || "Falha ao alterar a senha");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader title="Minha Conta" subtitle="Altere sua senha de acesso." />

        {message && (
          <Alert variant="success" onDismiss={() => setMessage("")}>
            {message}
          </Alert>
        )}

        <div className="card narrow">
          <form onSubmit={onSubmit}>
            <div className="stack">
              <label className="field">
                <span>Senha atual</span>
                <input
                  type="password"
                  value={form.current_password}
                  onChange={(e) => set("current_password", e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </label>
              <label className="field">
                <span>Nova senha</span>
                <input
                  type="password"
                  value={form.new_password}
                  onChange={(e) => set("new_password", e.target.value)}
                  required
                  autoComplete="new-password"
                />
              </label>
              <label className="field">
                <span>Confirmar nova senha</span>
                <input
                  type="password"
                  value={form.confirm}
                  onChange={(e) => set("confirm", e.target.value)}
                  required
                  autoComplete="new-password"
                />
              </label>
              {error && <Alert variant="error">{error}</Alert>}
              <button className="btn primary block" disabled={loading}>
                {loading ? "Salvando..." : "Alterar senha"}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}