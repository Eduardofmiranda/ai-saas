import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import BusinessHoursPanel from "../components/BusinessHoursPanel";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import PageHeader from "../components/ui/PageHeader";

const STATE_LABELS = {
  not_configured: "Não configurado",
  needs_config: "Falta configurar",
  open: "Conectado",
  close: "Desconectado",
  connecting: "Conectando",
  unknown: "Desconhecido",
  error: "Erro",
  unreachable: "Sem conexão",
  instance_not_found: "Instância não encontrada",
};

export default function WhatsApp() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [qrBase64, setQrBase64] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  async function loadStatus() {
    try {
      const st = await api.getWhatsAppStatus();
      setStatus(st);
      setError("");
      // Se conectou, limpa o QR para a UI trocar para tela de conectado
      if (st?.state === "open") setQrBase64(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadStatus(); }, []);

  // Poll: 3s quando QR visivel (escaneando), 10s caso contrario
  useEffect(() => {
    if (loading) return;
    const ms = qrBase64 ? 3000 : 10000;
    const id = setInterval(loadStatus, ms);
    return () => clearInterval(id);
  }, [loading, qrBase64]);

  async function handleSetup() {
    setConnecting(true);
    setError("");
    setQrBase64(null);
    try {
      const res = await api.setupWhatsApp();
      if (res.connected) {
        await loadStatus();
        return;
      }
      setQrBase64(res.qr_base64);
    } catch (e) {
      setError(e.message || "Erro ao gerar QR Code");
      await loadStatus();
    } finally {
      setConnecting(false);
    }
  }

  async function handleDisconnectConfirm() {
    setDisconnecting(true);
    setError("");
    try {
      await api.disconnectWhatsApp();
      setQrBase64(null);
      setConfirmOpen(false);
      await loadStatus();
    } catch (e) {
      setError("Erro ao desconectar: " + e.message);
    } finally {
      setDisconnecting(false);
    }
  }

  const state = status?.state || "not_configured";
  const isOpen = state === "open";

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader title="WhatsApp" subtitle="Conecte seu WhatsApp para atender automaticamente com IA." />

        {error && <Alert variant="error">{error}</Alert>}

        {loading && <p className="muted">Verificando status...</p>}

        {!loading && (
          <div className="wa-status-card">
            <div className="wa-status-header">
              <span className={`state-pill ${state}`}>
                {STATE_LABELS[state] || state}
                {isOpen && <span className="state-dot" />}
              </span>
              {status?.instance && (
                <span className="muted">Instância: {status.instance}</span>
              )}
            </div>

            {isOpen ? (
              <div className="wa-connected">
                <p>Seu WhatsApp está conectado e recebendo mensagens.</p>
                <p className="muted">As mensagens são processadas automaticamente pela IA conforme seus fluxos.</p>
                <button
                  className="btn ghost"
                  onClick={() => setConfirmOpen(true)}
                  disabled={disconnecting}
                >
                  {disconnecting ? "Desconectando..." : "Desconectar WhatsApp"}
                </button>
              </div>
            ) : (
              <div className="wa-connect">
                <p>Para conectar, escaneie o QR Code com o WhatsApp do seu celular.</p>
                <p className="muted">
                  Abra o WhatsApp → Aparelhos conectados → Conectar aparelho
                </p>

                {!qrBase64 && (
                  <button
                    className="btn primary"
                    onClick={handleSetup}
                    disabled={connecting}
                  >
                    {connecting ? "Preparando QR..." : "Conectar WhatsApp"}
                  </button>
                )}

                {qrBase64 && (
                  <div className="qr-section">
                    <div className="qr-box">
                      <img src={`data:image/png;base64,${qrBase64}`} alt="QR Code para conectar o WhatsApp" />
                    </div>
                    <p className="muted">Escaneie com o WhatsApp do seu celular.</p>
                    <p className="muted qr-expire">O QR expira em breve. Gere um novo código se necessário.</p>
                    <button
                      className="btn ghost"
                      onClick={handleSetup}
                      disabled={connecting}
                    >
                      Gerar novo QR
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <BusinessHoursPanel />
      </main>

      {confirmOpen && (
        <ConfirmDialog
          title="Desconectar WhatsApp"
          message="Desconectar o WhatsApp?"
          confirmLabel="Desconectar"
          onConfirm={handleDisconnectConfirm}
          onCancel={() => setConfirmOpen(false)}
          loading={disconnecting}
        />
      )}
    </div>
  );
}
