export const authStorage = {
  set(access, refresh, role) {
    localStorage.setItem("access", access);
    localStorage.setItem("refresh", refresh);
    if (role) {
      localStorage.setItem("role", role);
    }
  },

  getAccess() {
    return localStorage.getItem("access");
  },

  getRole() {
    return localStorage.getItem("role");
  },

  clear() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("role");
  },
};
