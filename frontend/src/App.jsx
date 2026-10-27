
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";
import { useEffect, useState } from "react";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Flights from "./pages/Flights";
import Weather from "./pages/Weather";
import Resources from "./pages/Resources";
import Staff from "./pages/Staff";
import AIDecisions from "./pages/AIDecisions";

function ProtectedLayout() {
  const navigate = useNavigate();
  const [token, setToken] = useState(() =>
    sessionStorage.getItem("airport-access-token")
  );

  useEffect(() => {
    function handleLogout() {
      setToken(null);
      navigate("/login", { replace: true });
    }

    function handleStorageChange() {
      const currentToken = sessionStorage.getItem(
        "airport-access-token"
      );

      setToken(currentToken);

      if (!currentToken) {
        navigate("/login", { replace: true });
      }
    }

    window.addEventListener("airport-logout", handleLogout);
    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("airport-logout", handleLogout);
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [navigate]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="flex">
        <Sidebar />

        <div className="min-w-0 flex-1">
          <Header />

          <main className="p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/flights" element={<Flights />} />
              <Route path="/weather" element={<Weather />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="/staff" element={<Staff />} />
              <Route path="/ai-decisions" element={<AIDecisions />} />
              <Route
                path="*"
                element={<Navigate to="/" replace />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

function LoginRoute() {
  const [token, setToken] = useState(() =>
    sessionStorage.getItem("airport-access-token")
  );

  useEffect(() => {
    function handleLogout() {
      setToken(null);
    }

    function handleLogin() {
      setToken(
        sessionStorage.getItem("airport-access-token")
      );
    }

    window.addEventListener("airport-logout", handleLogout);
    window.addEventListener("airport-login", handleLogin);

    return () => {
      window.removeEventListener("airport-logout", handleLogout);
      window.removeEventListener("airport-login", handleLogin);
    };
  }, []);

  return token ? (
    <Navigate to="/" replace />
  ) : (
    <Login />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </BrowserRouter>
  );
}
