export const NAV_SECTIONS = [
  {
    label: "Operação",
    items: [
      { to: "/", label: "Painel", icon: "home" },
      { to: "/conversas", label: "Conversas", icon: "message-circle" },
      { to: "/leads", label: "Leads", icon: "users", roles: ["owner", "admin"] },
    ],
  },
  {
    label: "Automação",
    items: [
      { to: "/fluxos", label: "Fluxos", icon: "workflow", roles: ["owner", "admin"] },
      { to: "/whatsapp", label: "WhatsApp", icon: "smartphone", roles: ["owner", "admin"] },
      { to: "/agenda", label: "Agenda", icon: "calendar" },
    ],
  },
  {
    label: "Base de Conhecimento",
    items: [
      { to: "/knowledge", label: "Conhecimento", icon: "book-open", roles: ["owner", "admin"] },
      { to: "/ai", label: "IA", icon: "cpu", roles: ["owner", "admin"] },
      { to: "/setores", label: "Setores", icon: "building", roles: ["owner", "admin"] },
    ],
  },
  {
    label: "Administração",
    items: [
      { to: "/admin", label: "Administração", icon: "wrench", roles: ["owner", "admin"] },
      { to: "/plataforma", label: "Plataforma", icon: "globe", roles: ["platform_admin"] },
    ],
  },
];
