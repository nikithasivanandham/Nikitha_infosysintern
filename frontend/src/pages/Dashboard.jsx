
import { useEffect, useState } from "react";
import {
  Plane,
  CloudSun,
  DoorOpen,
  Users,
  BrainCircuit,
  ArrowUpRight,
  Activity,
  ShieldCheck,
  AlertCircle,
  LoaderCircle,
} from "lucide-react";

import api from "../api";

const modules = [
  {
    title: "Flight Operations",
    description: "Flight status and delays",
    icon: Plane,
    status: "Flight module",
  },
  {
    title: "Weather & Alerts",
    description: "Alerts and disruptions",
    icon: CloudSun,
    status: "Weather module",
  },
  {
    title: "Gates & Resources",
    description: "Resource availability",
    icon: DoorOpen,
    status: "Resource module",
  },
  {
    title: "Staff Allocation",
    description: "Staff planning and allocation",
    icon: Users,
    status: "Staff module",
  },
  {
    title: "AI Agent Activity",
    description: "Research, analysis and planning",
    icon: BrainCircuit,
    status: "AI module",
  },
];

function SummaryCard({ title, value, description, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        <Icon size={20} className="text-sky-400" />
      </div>

      <p className="mt-4 text-3xl font-bold text-white">{value}</p>

      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}

function BackendAuthStatus() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function verifyBackendAuthorization() {
      setLoading(true);
      setError("");

      try {
        // The api.js interceptor attaches the JWT automatically.
        const response = await api.get("/auth/me");

        if (active) {
          setProfile(response.data);
        }
      } catch (err) {
        if (!active) return;

        setProfile(null);

        const status = err.response?.status;

        if (status === 401) {
          setError(
            "Unauthorized: the backend rejected your token. Please sign in again."
          );
        } else if (status === 403) {
          setError(
            "Forbidden: your account does not have permission for this request."
          );
        } else {
          setError(
            "Unable to verify backend authorization. Check that FastAPI is running and the /auth/me endpoint is available."
          );
        }

        console.error(
          "Backend authorization check failed:",
          err.response?.data || err.message
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    verifyBackendAuthorization();

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-sky-400/10 p-3">
          {loading ? (
            <LoaderCircle
              size={24}
              className="animate-spin text-sky-400"
            />
          ) : error ? (
            <AlertCircle size={24} className="text-red-400" />
          ) : (
            <ShieldCheck size={24} className="text-emerald-400" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <h2 className="font-bold text-white">
            Backend Authentication Status
          </h2>

          {loading ? (
            <p className="mt-2 text-sm text-sky-300">
              Verifying your access token with FastAPI...
            </p>
          ) : error ? (
            <p role="alert" className="mt-2 text-sm leading-6 text-red-400">
              {error}
            </p>
          ) : (
            <>
              <p className="mt-2 text-sm font-semibold text-emerald-400">
                Authorized — backend verification successful
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg bg-slate-950 p-3">
                  <p className="text-xs text-slate-500">Username</p>
                  <p className="mt-1 break-words text-sm text-white">
                    {profile?.username || "Not provided"}
                  </p>
                </div>

                <div className="rounded-lg bg-slate-950 p-3">
                  <p className="text-xs text-slate-500">User ID</p>
                  <p className="mt-1 break-all font-mono text-xs text-white">
                    {profile?.user_id || "Not provided"}
                  </p>
                </div>

                <div className="rounded-lg bg-slate-950 p-3">
                  <p className="text-xs text-slate-500">Role</p>
                  <p className="mt-1 break-words text-sm text-white">
                    {profile?.role || "Not provided"}
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default function Dashboard() {
  return (
    <div className="space-y-6 p-6">
      <section>
        <p className="text-sm text-slate-400">
          Welcome to the operations centre
        </p>

        <h2 className="mt-1 text-xl font-bold text-white">
          Operations at a glance
        </h2>
      </section>

      {/* Verify the current user's token with the backend. */}
      <BackendAuthStatus />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="Flight Status"
          value="--"
          description="Awaiting flight data"
          icon={Plane}
        />

        <SummaryCard
          title="Weather Alerts"
          value="--"
          description="Awaiting weather data"
          icon={CloudSun}
        />

        <SummaryCard
          title="Resource Availability"
          value="--"
          description="Awaiting resource data"
          icon={DoorOpen}
        />

        <SummaryCard
          title="AI Recommendations"
          value="--"
          description="Awaiting decision data"
          icon={BrainCircuit}
        />
      </section>

      <section>
        <div className="mb-4 flex items-center gap-2">
          <Activity size={20} className="text-sky-400" />

          <h2 className="text-lg font-bold text-white">
            Operations Modules
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map(({ title, description, icon: Icon, status }) => (
            <article
              key={title}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-sky-500/60"
            >
              <div className="flex items-start justify-between">
                <div className="rounded-lg bg-sky-500/10 p-3">
                  <Icon size={24} className="text-sky-400" />
                </div>

                <ArrowUpRight size={18} className="text-slate-500" />
              </div>

              <h3 className="mt-4 font-semibold text-white">
                {title}
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                {description}
              </p>

              <p className="mt-4 text-xs text-slate-500">
                {status}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="font-bold text-white">Recommended Action</h2>

        <p className="mt-2 text-sm text-slate-400">
          Recommended plans, reasons, risk levels and human approval
          decisions will appear here when connected to the backend.
        </p>

        <p className="mt-3 text-xs text-amber-400">
          No live recommendations connected yet.
        </p>
      </section>
    </div>
  );
}
