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
  if (form) {
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

export const api = {
  login: (username, password) =>
    request("POST", "/auth/login", undefined, { username, password }),
  register: (body) => request("POST", "/auth/register", body),
  getWorkflows: () => request("GET", "/workflows/"),
  getWorkflow: (id) => request("GET", `/workflows/${id}`),
  createWorkflow: (body) => request("POST", "/workflows/", body),
  updateWorkflow: (id, body) => request("PATCH", `/workflows/${id}`, body),
  deleteWorkflow: (id) => request("DELETE", `/workflows/${id}`),
  getNodeTypes: () => request("GET", "/workflows/node-types"),
  runWorkflow: (id, payload) =>
    request("POST", `/workflows/${id}/run`, { payload, await_result: true }),
  getExecutions: (id) => request("GET", `/workflows/${id}/executions`),
  getConfig: () => request("GET", "/config/"),
  updateConfig: (body) => request("PATCH", "/config/", body),
  getDashboard: () => request("GET", "/dashboard/"),
  getKnowledge: () => request("GET", "/knowledge/"),
  getKnowledgeDetail: (id) => request("GET", `/knowledge/${id}`),
  createKnowledge: (body) => request("POST", "/knowledge/", body),
  updateKnowledge: (id, body) => request("PATCH", `/knowledge/${id}`, body),
  deleteKnowledge: (id) => request("DELETE", `/knowledge/${id}`),
  searchKnowledge: (query, topK = 5) => request("POST", "/knowledge/search", { query, top_k: topK }),
  getTemplates: () => request("GET", "/templates/"),
  getTemplate: (id) => request("GET", `/templates/${id}`),
  useTemplate: (id) => request("POST", `/templates/${id}/use`),
  duplicateWorkflow: (id) => request("POST", `/workflows/${id}/duplicate`),
  // Usuario atual
  getMe: () => request("GET", "/auth/me"),
  // Usuarios / Administracao
  getUsers: () => request("GET", "/users/"),
  createUser: (body) => request("POST", "/users/", body),
  updateUser: (id, body) => request("PATCH", `/users/${id}`, body),
  deleteUser: (id) => request("DELETE", `/users/${id}`),
  // WhatsApp / Evolution
  getWhatsAppStatus: () => request("GET", "/config/whatsapp"),
  testWhatsApp: (body) => request("POST", "/config/whatsapp/test", body),
  connectWhatsApp: () => request("POST", "/config/whatsapp/connect", {}),
  setupWhatsApp: () => request("POST", "/config/whatsapp/setup", {}),
  disconnectWhatsApp: () => request("POST", "/config/whatsapp/disconnect", {}),
};
