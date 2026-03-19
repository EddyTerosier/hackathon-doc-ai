import { test, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import App from "../App";

vi.mock("../auth/authStorage", () => ({
  authStorage: {
    getAccess: vi.fn(),
    getRole: vi.fn(),
  },
}));

import { authStorage } from "../auth/authStorage";

function renderAt(path) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  authStorage.getAccess.mockReturnValue(null);
  authStorage.getRole.mockReturnValue(null);
});

test("renders main page on /", () => {
  renderAt("/");
  expect(screen.getByRole("heading", { name: /move from document drop-off to finance action in one flow/i })).toBeInTheDocument();
});

test("shows dashboard shortcut on main page when logged in", () => {
  authStorage.getAccess.mockReturnValue("access-token");
  authStorage.getRole.mockReturnValue("Employee");

  renderAt("/");
  expect(screen.getByRole("link", { name: /go to dashboard/i })).toHaveAttribute("href", "/dashboard/employee");
  expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /login/i })).not.toBeInTheDocument();
});

test("renders login page on /login", () => {
  renderAt("/login");
  expect(screen.getByRole("heading", { name: /login/i })).toBeInTheDocument();
});

test("renders register page on /register", () => {
  renderAt("/register");
  expect(screen.getByRole("heading", { name: /register/i })).toBeInTheDocument();
});

test("redirects dashboard access to login when there is no stored role", () => {
  renderAt("/dashboard/employee");
  expect(screen.getByRole("heading", { name: /login/i })).toBeInTheDocument();
});

test("renders employee dashboard when matching role is stored", () => {
  authStorage.getAccess.mockReturnValue("access-token");
  authStorage.getRole.mockReturnValue("Employee");

  renderAt("/dashboard/employee");
  expect(screen.getByRole("heading", { name: /stay on top of every submission/i })).toBeInTheDocument();
});

test("redirects accountant dashboard to employee dashboard for non-accountant users", () => {
  authStorage.getAccess.mockReturnValue("access-token");
  authStorage.getRole.mockReturnValue("Employee");

  renderAt("/dashboard/accountant");
  expect(screen.getByRole("heading", { name: /stay on top of every submission/i })).toBeInTheDocument();
});
