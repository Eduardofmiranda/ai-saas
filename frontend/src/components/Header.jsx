import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NAV_SECTIONS } from "../nav";
import Icon from "./ui/Icon";

function isNavActive(pathname, to) {
  return pathname === to || (to === "/fluxos" && pathname.startsWith("/editor"));
}

export default function Header({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(() => typeof localStorage !== "undefined" && localStorage.getItem("flowai.sb") === "1");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("sb-collapsed", collapsed);
    if (typeof localStorage !== "undefined") localStorage.setItem("flowai.sb", collapsed ? "1" : "0");
    return () => document.body.classList.remove("sb-collapsed");
  }, [collapsed]);

  function itemVisible(item) {
    if (!item.roles) return true;
    if (item.roles.includes("platform_admin")) return Boolean(user?.is_platform_admin);
    return item.roles.includes(user?.role);
  }

  const topRight = (
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
        <button className="btn ghost small" onClick={() => navigate("/conta")}>
          <Icon name="key" size={14} /> Senha
        </button>
        <button className="btn ghost small" onClick={logout}>
          <Icon name="log-out" size={14} /> Sair
        </button>
      </div>
    </div>
  );

  if (children) {
    return (
      <header className="topbar">
        <div
          className="logo"
          role="button"
          tabIndex={0}
          onClick={() => navigate("/")}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate("/"); } }}
          aria-label="Ir para o painel"
        >
          Flow<span>AI</span>
        </div>
        {children}
        {topRight}
      </header>
    );
  }

  const go = (to) => (e) => {
    e.preventDefault();
    navigate(to);
    setMobileOpen(false);
  };

  return (
    <>
      <div className={`app-backdrop ${mobileOpen ? "show" : ""}`} onClick={() => setMobileOpen(false)} />
      <aside className={`sidebar ${collapsed ? "collapsed" : ""} ${mobileOpen ? "open" : ""}`}>
        <div
          className="sidebar-brand"
          role="button"
          tabIndex={0}
          onClick={() => navigate("/")}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate("/"); } }}
          aria-label="FlowAI — Ir para o painel"
        >
          <span className="sidebar-brand-icon"><Icon name="sparkles" size={18} /></span>
          <span className="sidebar-brand-text">Flow<span>AI</span></span>
        </div>
        <nav className="sidebar-nav" aria-label="Menu principal">
          {NAV_SECTIONS.map((section) => (
            <div className="sidebar-group" key={section.label}>
              <div className="sidebar-group-label">{section.label}</div>
              {section.items.filter(itemVisible).map((item) => (
                <a
                  key={item.to}
                  href={item.to}
                  title={item.label}
                  className={`sidebar-link ${isNavActive(pathname, item.to) ? "active" : ""}`}
                  onClick={go(item.to)}
                >
                  <span className="sidebar-link-icon"><Icon name={item.icon} size={16} /></span>
                  <span className="sidebar-link-label">{item.label}</span>
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="sidebar-collapse" onClick={() => setCollapsed((c) => !c)} aria-label={collapsed ? "Expandir menu" : "Recolher menu"}>
            <Icon name={collapsed ? "chevrons-right" : "chevrons-left"} size={14} />
          </button>
        </div>
      </aside>
      <header className="topbar">
        <button className="btn ghost small topbar-menu" onClick={() => setMobileOpen(true)} aria-label="Abrir menu">
          <Icon name="menu" size={16} />
        </button>
        <div className="topbar-spacer" />
        {topRight}
      </header>
    </>
  );
}
