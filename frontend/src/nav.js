export const NAV_SECTIONS = [
  {
    label: "Operação",
    items: [
      { to: "/", label: "Painel", icon: "home" },
      { to: "/conversas", label: "Conversas", icon: "message-circle" },
      { to: "/leads", label: "Leads", icon: "users" },
    ],
  },
  {
    label: "Automação",
    items: [
      { to: "/fluxos", label: "Fluxos", icon: "workflow" },
      { to: "/whatsapp", label: "WhatsApp", icon: "smartphone" },
      { to: "/agenda", label: "Agenda", icon: "calendar" },
    ],
  },
  {
    label: "Base de Conhecimento",
    items: [
      { to: "/knowledge", label: "Conhecimento", icon: "book-open" },
      { to: "/ai", label: "IA", icon: "cpu" },
      { to: "/setores", label: "Setores", icon: "building" },
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
