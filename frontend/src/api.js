// API_BASE:
// - Em PRODUCAO (nginx) usamos o prefixo "/api": o nginx tem
//   `location /api/ { proxy_pass http://backend:8000/; }` que descarta o
//   "/api" e entrega ao backend. Isso SEPARA as chamadas de API das rotas do
//   SPA (ex.: /knowledge, /workflows), evitando que navegacao do frontend caia
//   no backend sem token (bug de "Not authenticated").
// - Em dev pode ser sobrescrito por VITE_API_BASE (ver vite.config.js proxy).
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

let token = localStorage.getItem("token") || "";
let onUnauthorized = null;

export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export function setToken(t) {
  token = t || "";
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

export function getToken() {
  return token;
}

async function request(method, path, body, form) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let options = { method, headers };
  if (body instanceof FormData) {
    options.body = body;
  } else if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    options.body = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, options);
  if (res.status === 401 && onUnauthorized) {
    onUnauthorized();
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function qs(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  login: (username, password) =>
    request("POST", "/auth/login", undefined, { username, password }),
  register: (body) => request("POST", "/auth/register", body),
  getMe: () => request("GET", "/auth/me"),
  changePassword: (body) => request("POST", "/auth/change-password", body),
  refreshToken: (refreshToken) =>
    request("POST", "/auth/refresh", { refresh_token: refreshToken }),
  forgotPassword: (email) => request("POST", "/auth/forgot-password", { email }),
  resetPassword: (token, newPassword) =>
    request("POST", "/auth/reset-password", { token, new_password: newPassword }),
  getWorkflows: (params = {}) => request("GET", `/workflows/${qs(params)}`),
  getWorkflow: (id) => request("GET", `/workflows/${id}`),
  createWorkflow: (body) => request("POST", "/workflows/", body),
  updateWorkflow: (id, body) => request("PATCH", `/workflows/${id}`, body),
  deleteWorkflow: (id) => request("DELETE", `/workflows/${id}`),
  getNodeTypes: () => request("GET", "/workflows/node-types"),
  runWorkflow: (id, payload, dryRun = true) =>
    request("POST", `/workflows/${id}/run`, { payload, await_result: true, dry_run: dryRun }),
  getExecutions: (id) => request("GET", `/workflows/${id}/executions`),
  getConfig: () => request("GET", "/config/"),
  updateConfig: (body) => request("PATCH", "/config/", body),
  testAI: (body = {}) => request("POST", "/config/ai/test", body),
  getDashboard: () => request("GET", "/dashboard/"),
  getWorkflowMetrics: (id) => request("GET", `/dashboard/workflows/${id}/metrics`),
  getKnowledge: (params = {}) => request("GET", `/knowledge/${qs(params)}`),
  getKnowledgeDetail: (id) => request("GET", `/knowledge/${id}`),
  createKnowledge: (body) => request("POST", "/knowledge/", body),
  uploadKnowledge: (file, name = "", description = "") => {
    const fd = new FormData();
    fd.append("file", file);
    if (name) fd.append("name", name);
    if (description) fd.append("description", description);
    return request("POST", "/knowledge/upload", fd, true);
  },
  updateKnowledge: (id, body) => request("PATCH", `/knowledge/${id}`, body),
  deleteKnowledge: (id) => request("DELETE", `/knowledge/${id}`),
  searchKnowledge: (query, topK = 5) => request("POST", "/knowledge/search", { query, top_k: topK }),
  getTemplates: () => request("GET", "/templates/"),
  getTemplate: (id) => request("GET", `/templates/${id}`),
  useTemplate: (id) => request("POST", `/templates/${id}/use`),
  duplicateWorkflow: (id) => request("POST", `/workflows/${id}/duplicate`),
  // Usuarios / Administracao
  getUsers: (params = {}) => request("GET", `/users/${qs(params)}`),
  createUser: (body) => request("POST", "/users/", body),
  updateUser: (id, body) => request("PATCH", `/users/${id}`, body),
  deleteUser: (id) => request("DELETE", `/users/${id}`),
  // Auditoria
  getAuditLogs: (params = {}) => request("GET", `/audit-logs/${qs(params)}`),
  // Administração global da plataforma (somente operador autorizado)
  getPlatformOverview: () => request("GET", "/platform-admin/overview"),
  getPlatformUsers: () => request("GET", "/platform-admin/users"),
  resetUserPassword: (userId) => request("POST", `/platform-admin/users/${userId}/reset-password`),
  getPlatformProviders: () => request("GET", "/platform-admin/providers"),
  updatePlatformProvider: (provider, body) => request("PUT", `/platform-admin/providers/${provider}`, body),
  getPlatformProviderBalance: (provider) => request("POST", `/platform-admin/providers/${provider}/balance`, {}),
  // Politica de IA por usuario (superadmin)
  getUserAIConfigs: () => request("GET", "/platform-admin/user-ai-config"),
  getUserAIConfig: (userId) => request("GET", `/platform-admin/user-ai-config/${userId}`),
  saveUserAIConfig: (userId, body) => request("PUT", `/platform-admin/user-ai-config/${userId}`, body),
  // Erros (superadmin)
  getPlatformErrors: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.limit) qs.set("limit", params.limit);
    if (params.offset) qs.set("offset", params.offset);
    if (params.company_id) qs.set("company_id", params.company_id);
    if (params.workflow_id) qs.set("workflow_id", params.workflow_id);
    return request("GET", `/platform-admin/errors?${qs.toString()}`);
  },
  clearPlatformErrors: () => request("DELETE", "/platform-admin/errors"),
  // AI — allowed / effective (usuario comum)
  getAllowedAI: () => request("GET", "/config/ai/allowed"),
  getEffectiveAI: () => request("GET", "/config/ai/effective"),
    // WhatsApp / Evolution
  getWhatsAppStatus: () => request("GET", "/config/whatsapp"),
  testWhatsApp: (body) => request("POST", "/config/whatsapp/test", body),
  connectWhatsApp: () => request("POST", "/config/whatsapp/connect", {}),
  setupWhatsApp: () => request("POST", "/config/whatsapp/setup", {}),
  disconnectWhatsApp: () => request("POST", "/config/whatsapp/disconnect", {}),
  // Horario de atendimento
  getBusinessHours: () => request("GET", "/config/business-hours"),
  updateBusinessHours: (body) => request("PUT", "/config/business-hours", body),
  // Inbox / Conversas
  getConversations: (params = {}) => request("GET", `/conversations/${qs(params)}`),
  getConversation: (id) => request("GET", `/conversations/${id}`),
  updateConversation: (id, body) => request("PATCH", `/conversations/${id}`, body),
  getConversationMessages: (id) => request("GET", `/messages/conversation/${id}`),
  replyToConversation: (conversationId, content) =>
    request("POST", `/messages/conversation/${conversationId}/reply`, { content }),
  assumeConversation: (conversationId) =>
    request("POST", `/conversations/${conversationId}/assume`),
  pauseConversationWorkflow: (conversationId) =>
    request("POST", `/conversations/${conversationId}/pause-workflow`),
  // Leads / Clientes
  getCustomers: (params = {}) => request("GET", `/customers/${qs(params)}`),
  deleteCustomer: (id) => request("DELETE", `/customers/${id}`),
  exportCustomersJson: () => {
    const token = localStorage.getItem("token");
    return fetch(`${API_BASE}/customers/export`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erro ao exportar (${r.status})`);
        return r.blob();
      })
      .then((blob) => downloadBlob(blob, "leads.json"));
  },
  exportCustomersXlsx: () => {
    const token = localStorage.getItem("token");
    return fetch(`${API_BASE}/customers/export/xlsx`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erro ao exportar (${r.status})`);
        return r.blob();
      })
      .then((blob) => downloadBlob(blob, "leads.xlsx"));
  },
  bulkMessageCustomers: (body) => request("POST", "/customers/bulk-message", body),
  // Setores
  getDepartments: () => request("GET", "/departments/"),
  createDepartment: (body) => request("POST", "/departments/", body),
  updateDepartment: (id, body) => request("PATCH", `/departments/${id}`, body),
  deleteDepartment: (id) => request("DELETE", `/departments/${id}`),
  // Agenda / Secretaria IA
  getAgendaConfig: () => request("GET", "/agenda/config"),
  updateAgendaConfig: (body) => request("PUT", "/agenda/config", body),
  getAgendaAvailability: (date) => request("GET", `/agenda/availability?date=${date}`),
  getAgendaAppointments: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.date_from) qs.set("date_from", params.date_from);
    if (params.date_to) qs.set("date_to", params.date_to);
    if (params.skip) qs.set("skip", params.skip);
    if (params.limit) qs.set("limit", params.limit);
    return request("GET", `/agenda/appointments?${qs.toString()}`);
  },
  createAgendaAppointment: (body) => request("POST", "/agenda/appointments", body),
  cancelAgendaAppointment: (id) => request("DELETE", `/agenda/appointments/${id}`),
};

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}
