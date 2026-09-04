import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  ["/fluxos", "Fluxos"],
  ["/conversas", "Conversas"],
  ["/ai", "IA"],
  ["/knowledge", "Conhecimento"],
  ["/whatsapp", "WhatsApp"],
  ["/admin", "Administração"],
];

export default function Header({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isManager = user?.role === "owner" || user?.role === "admin";
  const nav = NAV.filter(([, label]) => !(label === "Administração" && !isManager));

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
        <span className="user">
          {user?.name || user?.email}
          {user?.role && (
            <span className={`role-chip role-${user.role}`}>
              {user.role === "owner" ? "Dono" : user.role === "admin" ? "Admin" : "Atendente"}
            </span>
          )}
        </span>
        <button className="btn ghost" onClick={() => navigate("/conta")}>Senha</button>
        <button className="btn ghost" onClick={logout}>Sair</button>
      </div>
    </header>
  );
}
