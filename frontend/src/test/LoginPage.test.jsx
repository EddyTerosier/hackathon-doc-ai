import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, test, expect, beforeEach, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { toast } from "react-hot-toast";
import LoginPage from "../pages/LoginPage";
import { login } from "../auth/authApi";
import { authStorage } from "../auth/authStorage";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../auth/authApi", () => ({
  login: vi.fn(),
}));

vi.mock("../auth/authStorage", () => ({
  authStorage: {
    set: vi.fn(),
    getAccess: vi.fn(),
    clear: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

function renderPage() {
  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("shows validation error when fields are empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /login/i }));

    expect(toast.error).toHaveBeenCalledWith("Please fill in all fields");
    expect(login).not.toHaveBeenCalled();
  });

  test("logs in employee and navigates to employee page", async () => {
    const user = userEvent.setup();

    login.mockResolvedValue({
      tokens: {
        access: "access-token",
        refresh: "refresh-token",
      },
      user: {
        role: "Employee",
      },
    });

    renderPage();

    await user.type(screen.getByPlaceholderText(/email/i), "employee@test.com");
    await user.type(screen.getByPlaceholderText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /login/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({
        email: "employee@test.com",
        password: "secret123",
      });
    });

    expect(authStorage.set).toHaveBeenCalledWith("access-token", "refresh-token", "Employee");
    expect(toast.success).toHaveBeenCalledWith("Login successful");
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard/employee");
  });

  test("logs in accountant and navigates to accountant page", async () => {
    const user = userEvent.setup();

    login.mockResolvedValue({
      tokens: {
        access: "access-token",
        refresh: "refresh-token",
      },
      user: {
        role: "Accountant",
      },
    });

    renderPage();

    await user.type(screen.getByPlaceholderText(/email/i), "accountant@test.com");
    await user.type(screen.getByPlaceholderText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /login/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard/accountant");
    });
  });

  test("shows error when login fails", async () => {
    const user = userEvent.setup();

    login.mockRejectedValue(new Error("Login failed"));

    renderPage();

    await user.type(screen.getByPlaceholderText(/email/i), "user@test.com");
    await user.type(screen.getByPlaceholderText(/password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /login/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Login error");
    });

    expect(authStorage.set).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
