// Feedback padronizado (erro/sucesso/info) — substitui .error, .success, .success-msg e .bh-ok.
// role="alert" (erro) anuncia imediatamente; role="status" (success/info) e polite.

export default function Alert({ variant = "info", children, onDismiss, className = "" }) {
  return (
    <div
      className={`alert alert-${variant} ${className}`.trim()}
      role={variant === "error" ? "alert" : "status"}
    >
      <span className="alert-body">{children}</span>
      {onDismiss && (
        <button type="button" className="alert-close" onClick={onDismiss} aria-label="Dispensar aviso">
          ×
        </button>
      )}
    </div>
  );
}
