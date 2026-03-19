const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);

  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }

  return res.status === 204 ? null : res.json();
}

function authHeaders(token, extra = {}) {
  return {
    Authorization: `Bearer ${token}`,
    ...extra,
  };
}

export function getCompanies(token) {
  return request("/api/companies/", {
    headers: authHeaders(token),
  });
}

export function createCompany(token, data) {
  return request("/api/companies/", {
    method: "POST",
    headers: authHeaders(token, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(data),
  });
}

export function getSuppliers(token) {
  return request("/api/suppliers/", {
    headers: authHeaders(token),
  });
}

export function createSupplier(token, data) {
  return request("/api/suppliers/", {
    method: "POST",
    headers: authHeaders(token, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(data),
  });
}

export function getDocumentGroups(token) {
  return request("/api/document-groups/", {
    headers: authHeaders(token),
  });
}

export function getDocumentDetail(token, documentId) {
  return request(`/api/documents/${documentId}/`, {
    headers: authHeaders(token),
  });
}

export function createDocumentGroup(token, data) {
  return request("/api/document-groups/", {
    method: "POST",
    headers: authHeaders(token, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(data),
  });
}

export function uploadDocumentToGroup(token, groupId, file) {
  const formData = new FormData();
  formData.append("file", file);

  return request(`/api/document-groups/${groupId}/documents/`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  });
}
