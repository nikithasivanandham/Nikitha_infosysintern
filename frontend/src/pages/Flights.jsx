
import { Plane } from 'lucide-react'

export default function Flights() {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center gap-3">
        <Plane size={28} className="text-sky-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">
            Flight Operations
          </h2>
          <p className="text-sm text-slate-400">
            Monitor flight status, delays and risk levels.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="font-semibold text-white">Flight Information</h3>
        <p className="mt-2 text-sm text-slate-400">
          Flight data will appear here when the flight module
          and backend API are connected.
        </p>
        <p className="mt-3 text-xs text-amber-400">
          Demo status: No flight data connected.
        </p>
      </div>
    </div>
  )
}
