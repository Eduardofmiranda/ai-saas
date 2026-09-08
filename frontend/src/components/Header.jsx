import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  ["/fluxos", "Fluxos"],
  ["/conversas", "Conversas"],
  ["/leads", "Leads"],
  ["/ai", "IA"],
  ["/knowledge", "Conhecimento"],
  ["/setores", "Setores"],
  ["/whatsapp", "WhatsApp"],
  ["/admin", "Administração"],
];

export default function Header({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isManager = user?.role === "owner" || user?.role === "admin";
  const nav = [...NAV, ...(user?.is_platform_admin ? [["/plataforma", "Plataforma"]] : [])].filter(([, label]) => !(label === "Administração" && !isManager));

  return (
    <header className="topbar">
      <div className="logo" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        Flow<span>AI</span>
      </div>

      {children || (
        <nav className="topnav">
          <a href="/" className={pathname === "/" ? "active" : ""}>Painel</a>
          {nav.map(([to, label]) => (
            <a
              key={to}
              href={to}
              className={pathname === to || (to === "/fluxos" && pathname.startsWith("/editor")) ? "active" : ""}
            >
              {label}
            </a>
          ))}
        </nav>
      )}

      <div className="topbar-right">
        <span className="user" title={user?.email || user?.name}>
          <span className="user-avatar">{(user?.name || user?.email || "?").charAt(0).toUpperCase()}</span>
          <span className="user-name">{user?.name || user?.email}</span>
          {user?.is_platform_admin && <span className="role-chip role-platform">Plataforma</span>}
          {user?.role && (
            <span className={`role-chip role-${user.role}`}>
              {user.role === "owner" ? "Dono" : user.role === "admin" ? "Admin" : "Atendente"}
            </span>
          )}
        </span>
        <div className="btn-group">
          <button className="btn ghost small" onClick={() => navigate("/conta")}>Senha</button>
          <button className="btn ghost small" onClick={logout}>Sair</button>
        </div>
      </div>
    </header>
  );
}
