
import { Activity, Bell, Plane, LogOut } from "lucide-react";

export default function Header() {
  function handleSignOut() {
    sessionStorage.removeItem("airport-access-token");
    sessionStorage.removeItem("airport-demo-login");

    // Notify App.jsx that the user has signed out.
    window.dispatchEvent(new Event("airport-logout"));
  }

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 bg-slate-950 px-6 py-5 text-white">
      <div>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-sky-400">
          <Plane size={15} />
          Airport Operations Coordination Engine
        </div>

        <h1 className="text-2xl font-bold">
          Live Operations Overview
        </h1>

        <p className="mt-1 text-sm text-slate-400">
          Monitor flights, resources and AI-assisted decisions.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-emerald-800 bg-emerald-950/40 px-3 py-2 sm:flex">
          <Activity size={16} className="text-emerald-400" />
          <span className="text-sm text-emerald-400">
            Operations Dashboard
          </span>
        </div>

        <button
          type="button"
          aria-label="Notifications"
          title="Notifications"
          className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800"
        >
          <Bell size={19} />
        </button>

        <button
          type="button"
          onClick={handleSignOut}
          className="flex items-center gap-2 rounded-lg border border-red-800 px-3 py-2 text-sm font-medium text-red-400 transition hover:bg-red-950"
        >
          <LogOut size={17} />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  );
}
