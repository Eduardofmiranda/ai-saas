export const NAV_SECTIONS = [
  {
    label: "Operação",
    items: [
      { to: "/", label: "Painel", icon: "🏠" },
      { to: "/conversas", label: "Conversas", icon: "💬" },
      { to: "/leads", label: "Leads", icon: "👥" },
    ],
  },
  {
    label: "Automação",
    items: [
      { to: "/fluxos", label: "Fluxos", icon: "⚙️" },
      { to: "/whatsapp", label: "WhatsApp", icon: "📱" },
      { to: "/agenda", label: "Agenda", icon: "📅" },
    ],
  },
  {
    label: "Base de Conhecimento",
    items: [
      { to: "/knowledge", label: "Conhecimento", icon: "📚" },
      { to: "/ai", label: "IA", icon: "🧠" },
      { to: "/setores", label: "Setores", icon: "🏢" },
    ],
  },
  {
    label: "Administração",
    items: [
      { to: "/admin", label: "Administração", icon: "🛠️", roles: ["owner", "admin"] },
      { to: "/plataforma", label: "Plataforma", icon: "🌐", roles: ["platform_admin"] },
    ],
  },
];