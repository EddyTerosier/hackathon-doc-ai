/* eslint-disable no-unused-vars */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../auth/authApi";
import { toast } from "react-hot-toast";

export default function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    last_name: "",
    first_name: "",
    role: "Employee",
    email: "",
    password: "",
    confirmPassword: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!form.last_name.trim() || !form.first_name.trim() || !form.email.trim() || !form.password.trim() || !form.confirmPassword.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    if (!emailRegex.test(form.email)) {
      toast.error("Please enter a valid email");
      return;
    }

    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }

    if (form.password !== form.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    try {
      const payload = {
        last_name: form.last_name,
        first_name: form.first_name,
        role: form.role,
        email: form.email,
        password: form.password,
      };

      await register(payload);

      toast.success("Account created");
      navigate("/login");
    } catch (err) {
      toast.error("Register error");
    }
  }

  return (
    <div className="input-box">
      <h1>Register</h1>

      <form onSubmit={handleSubmit} className="custom-form">
        <input
          name="last_name"
          placeholder="Nom"
          value={form.last_name}
          onChange={handleChange}
          className="custom-input"
        />

        <input
          name="first_name"
          placeholder="Prenom"
          value={form.first_name}
          onChange={handleChange}
          className="custom-input"
        />

        <input
          name="email"
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={handleChange}
          className="custom-input"
        />

        <input
          name="password"
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={handleChange}
          className="custom-input"
        />

        <input
          name="confirmPassword"
          type="password"
          placeholder="Retype password"
          value={form.confirmPassword}
          onChange={handleChange}
          className="custom-input"
        />

        <button type="submit" className="custom-button">
          Register
        </button>
      </form>

      <Link to="/" className="custom-link">
        Back to main page
      </Link>
    </div>
  );
}
