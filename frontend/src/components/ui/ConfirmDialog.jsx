// Confirmacao destrutiva padronizada — substitui todos os confirm() nativos.
// danger=true usa btn solid-danger (acao irreversivel); danger=false usa primary.

import Modal from "./Modal";

export default function ConfirmDialog({
  title,
  message,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className="btn ghost" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? "btn solid-danger" : "btn primary"}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Aguarde..." : confirmLabel}
          </button>
        </>
      }
    >
      {typeof message === "string" ? <p className="confirm-message">{message}</p> : message}
    </Modal>
  );
}
