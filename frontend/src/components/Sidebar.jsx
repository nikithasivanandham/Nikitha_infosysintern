
import {
  LayoutDashboard,
  Plane,
  CloudSun,
  DoorOpen,
  Users,
  BrainCircuit,
  Settings,
} from "lucide-react";

import { NavLink } from "react-router-dom";

const menuItems = [
  { label: "Overview", icon: LayoutDashboard, path: "/" },
  { label: "Flights", icon: Plane, path: "/flights" },
  { label: "Weather & Alerts", icon: CloudSun, path: "/weather" },
  { label: "Gates & Resources", icon: DoorOpen, path: "/resources" },
  { label: "Staff Allocation", icon: Users, path: "/staff" },
  { label: "AI Decisions", icon: BrainCircuit, path: "/ai-decisions" },
];

export default function Sidebar() {
  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 p-5 text-white">
      <div className="mb-10">
        <div className="mb-2 flex items-center gap-3">
          <Plane className="text-sky-400" size={28} />
          <span className="text-lg font-bold">AirportOps</span>
        </div>

        <p className="text-xs text-slate-400">
          Operations Coordination Engine
        </p>
      </div>

      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        Main Menu
      </p>

      <nav className="flex flex-col gap-2">
        {menuItems.map(({ label, icon: Icon, path }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-3 text-left text-sm transition ${
                isActive
                  ? "bg-sky-500/15 text-sky-400"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`
            }
          >
            <Icon size={19} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-slate-800 pt-4">
        <button
          type="button"
          onClick={() => {
            sessionStorage.removeItem("airport-demo-login");
            window.location.assign("/login");
          }}
          className="flex w-full items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-white"
        >
          <Settings size={19} />
          Sign Out
        </button>

        <p className="mt-4 text-xs text-slate-600">
          Airport Operations v1.0
        </p>
      </div>
    </aside>
  );
}
