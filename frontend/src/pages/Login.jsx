
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plane, LockKeyhole, Mail } from "lucide-react";
import api from "../api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function handleLogin(event) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/auth/login", {
        username: email.trim(),
        password,
      });

      const token = response.data?.access_token;

      if (typeof token !== "string" || !token.trim()) {
        throw new Error(
          "Login succeeded, but the backend did not return a valid access token."
        );
      }

      // Store the JWT token.
      sessionStorage.setItem("airport-access-token", token);

      // Confirm that the token was stored.
      if (!sessionStorage.getItem("airport-access-token")) {
        throw new Error("Unable to store the authentication token.");
      }

      // Remove the old mock-login flag.
      sessionStorage.removeItem("airport-demo-login");

      // Notify App.jsx that login succeeded.
      window.dispatchEvent(new Event("airport-login"));

      // Navigate to the protected dashboard.
      navigate("/", { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : err.message ||
            "Login failed. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
        <div className="mb-6 flex justify-center">
          <div className="rounded-2xl bg-cyan-400/10 p-4">
            <Plane size={36} className="text-cyan-400" />
          </div>
        </div>

        <h1 className="text-center text-2xl font-bold">
          Airport Operations
        </h1>

        <p className="mt-2 text-center text-sm text-slate-400">
          Coordination Engine
        </p>

        <form onSubmit={handleLogin} className="mt-8 space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm text-slate-300"
            >
              Email / Username
            </label>

            <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3">
              <Mail size={18} className="text-slate-400" />

              <input
                id="email"
                type="text"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setError("");
                }}
                placeholder="Enter your username"
                autoComplete="username"
                className="w-full bg-transparent py-3 text-white outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm text-slate-300"
            >
              Password
            </label>

            <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3">
              <LockKeyhole size={18} className="text-slate-400" />

              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setError("");
                }}
                placeholder="Enter your password"
                autoComplete="current-password"
                className="w-full bg-transparent py-3 text-white outline-none"
                required
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-cyan-400 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500">
          Airport Operations Coordination Engine
        </p>
      </div>
    </div>
  );
}
