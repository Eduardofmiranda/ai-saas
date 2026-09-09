// Formatadores e helpers visuais compartilhados (fonte unica).
// Antes duplicados em Conversations.jsx, Leads.jsx, Departments.jsx e PlatformAdmin.jsx.

export function formatPhone(phone) {
  if (!phone) return "";
  const digits = String(phone).replace(/\D/g, "");
  if (digits.length === 13 && digits.startsWith("55")) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`;
  }
  if (digits.length === 12 && digits.startsWith("55")) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 8)}-${digits.slice(8)}`;
  }
  return phone;
}

// Paleta unica de avatares (uma so origem de cor em todo o app).
export const AVATAR_COLORS = ["#4f7cff", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444", "#22d3ee"];

export function avatarColor(seed) {
  const str = String(seed || "?");
  let hash = 0;
  for (let i = 0; i < str.length; i += 1) hash = (hash * 31 + str.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}
