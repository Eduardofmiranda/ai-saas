// Cabecalho de pagina padrao: <h1> + subtitulo + acoes a direita.
// Substitui os 3 padroes divergentes (.content-head+h2, .page-header aninhado, nenhum).

export default function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header page-header-row">
      <div className="page-header-text">
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {children && <div className="btn-group">{children}</div>}
    </div>
  );
}
