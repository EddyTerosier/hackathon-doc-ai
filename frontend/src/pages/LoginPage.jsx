import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import { login } from "../auth/authApi";
import { authStorage } from "../auth/authStorage";

export default function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();

    if (!email.trim() || !password.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      const response = await login({ email, password });
      const { tokens, user } = response;
      authStorage.set(tokens.access, tokens.refresh, user.role);

      toast.success("Login successful");

      if (user.role === "Employee") navigate("/dashboard/employee");
      else navigate("/dashboard/accountant");
    } catch {
      toast.error("Login error");
    }
  }

  return (
    <div className="input-box">
      <h1>Login</h1>

      <form onSubmit={handleSubmit} className="custom-form">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="custom-input"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="custom-input"
        />

        <button type="submit" className="custom-button">
          LOGIN
        </button>
      </form>

      <p>
        No account?{" "}
        <Link to="/register" className="custom-link">
          Register here
        </Link>
      </p>

      <Link to="/" className="custom-link">
        Back to main page
      </Link>
    </div>
  );
}
