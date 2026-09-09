// Modal base acessivel: role="dialog", aria-modal, Escape fecha, overlay com
// verificacao de target. Substitui as 3 implementacoes divergentes do projeto.

import { useEffect } from "react";

export default function Modal({ title, icon, onClose, children, footer, width }) {
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="modal-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        style={width ? { maxWidth: width } : undefined}
      >
        <div className="modal-header">
          <div className="modal-title">
            {icon}
            {title}
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}
