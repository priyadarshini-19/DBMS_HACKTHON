const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const getToken = () => localStorage.getItem("tf_token");
export const getUser = () => {
  try { return JSON.parse(localStorage.getItem("tf_user")); } catch { return null; }
};
export const saveAuth = (d) => {
  localStorage.setItem("tf_token", d.access_token);
  localStorage.setItem("tf_user", JSON.stringify(d.user));
};
export const clearAuth = () => { localStorage.removeItem("tf_token"); localStorage.removeItem("tf_user"); };

export async function api(path, method = "GET", body) {
  const token = getToken();
  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Cannot reach the backend. Is it running on http://localhost:8000 ?");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join(", ") : msg;
    } catch { /* ignore */ }
    if (res.status === 401 && token) { clearAuth(); window.location.reload(); }
    throw new Error(msg);
  }
  return res.json();
}

export const login = (email, password, role) => api("/auth/login", "POST", { email, password, role });
export const register = (name, email, password, role) => api("/auth/register", "POST", { name, email, password, role });
