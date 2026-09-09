// Estado vazio padronizado (icone SVG opcional, titulo, descricao, acao).
// Substitui .empty, .empty-state soltos e os emojis gigantes.

export default function EmptyState({ icon, title, children, action, className = "" }) {
  return (
    <div className={`empty-state ${className}`.trim()}>
      {icon && (
        <div className="empty-icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}
