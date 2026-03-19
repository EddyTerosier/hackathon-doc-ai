import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, test, expect, beforeEach, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { toast } from "react-hot-toast";
import RegisterPage from "../pages/RegisterPage";
import { register } from "../auth/authApi";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../auth/authApi", () => ({
  register: vi.fn(),
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
      <RegisterPage />
    </MemoryRouter>
  );
}

async function fillValidForm(user) {
  await user.type(screen.getByPlaceholderText(/^nom$/i), "Doe");
  await user.type(screen.getByPlaceholderText(/^prenom$/i), "John");
  await user.type(screen.getByPlaceholderText(/^email$/i), "john@test.com");
  await user.type(screen.getByPlaceholderText(/^password$/i), "secret123");
  await user.type(screen.getByPlaceholderText(/^retype password$/i), "secret123");
}

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("shows validation error when fields are empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /register/i }));

    expect(toast.error).toHaveBeenCalledWith("Please fill in all fields");
    expect(register).not.toHaveBeenCalled();
  });

  test("shows validation error for invalid email", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/^nom$/i), "Doe");
    await user.type(screen.getByPlaceholderText(/^prenom$/i), "John");
    await user.type(screen.getByPlaceholderText(/^email$/i), "john@test");
    await user.type(screen.getByPlaceholderText(/^password$/i), "secret123");
    await user.type(screen.getByPlaceholderText(/retype password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /register/i }));

    expect(toast.error).toHaveBeenCalledWith("Please enter a valid email");
    expect(register).not.toHaveBeenCalled();
  });

  test("shows validation error when passwords do not match", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/^nom$/i), "Doe");
    await user.type(screen.getByPlaceholderText(/^prenom$/i), "John");
    await user.type(screen.getByPlaceholderText(/^email$/i), "john@test.com");
    await user.type(screen.getByPlaceholderText(/^password$/i), "secret123");
    await user.type(screen.getByPlaceholderText(/retype password/i), "different123");
    await user.click(screen.getByRole("button", { name: /register/i }));

    expect(toast.error).toHaveBeenCalledWith("Passwords do not match");
    expect(register).not.toHaveBeenCalled();
  });

  test("submits valid form and navigates to login", async () => {
    const user = userEvent.setup();
    register.mockResolvedValue({ id: 1 });

    renderPage();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() => {
      expect(register).toHaveBeenCalledWith({
        last_name: "Doe",
        first_name: "John",
        role: "Employee",
        email: "john@test.com",
        password: "secret123",
      });
    });

    expect(toast.success).toHaveBeenCalledWith("Account created");
    expect(mockNavigate).toHaveBeenCalledWith("/login");
  });

  test("shows error when register request fails", async () => {
    const user = userEvent.setup();
    register.mockRejectedValue(new Error("Register failed"));

    renderPage();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Register error");
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
