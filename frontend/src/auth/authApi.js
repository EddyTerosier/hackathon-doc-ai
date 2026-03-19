const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function login(data) {
  const res = await fetch(`${API}/api/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error("Login failed");

  return res.json();
}

export async function register(data) {
  const res = await fetch(`${API}/api/auth/register/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error("Register failed");

  return res.json();
}

export async function getMe(token) {
  const res = await fetch(`${API}/api/auth/me/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return res.json();
}
