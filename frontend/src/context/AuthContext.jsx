import { createContext, useContext, useState, useEffect } from "react";
import { api, setToken, getToken, setUnauthorizedHandler } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Qualquer 401 (token expirado/inválido) desloga automaticamente.
    setUnauthorizedHandler(() => {
      setToken("");
      setUser(null);
    });
    // token ja salvo -> assume logado (o backend valida nas chamadas)
    setReady(true);
    if (getToken()) {
      setUser({ token: getToken() });
    }
  }, []);

  async function login(username, password) {
    const data = await api.login(username, password);
    setToken(data.access_token);
    setUser({
      token: data.access_token,
      name: data.name,
      email: data.email,
      company_id: data.company_id,
      role: data.role,
    });
    return data;
  }

  async function register(body) {
    const data = await api.register(body);
    setToken(data.access_token);
    setUser({
      token: data.access_token,
      name: data.name,
      email: data.email,
      company_id: data.company_id,
      role: data.role,
    });
    return data;
  }

  function logout() {
    setToken("");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
