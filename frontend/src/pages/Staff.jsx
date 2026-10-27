
import { Users } from 'lucide-react'

export default function Staff() {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center gap-3">
        <Users size={28} className="text-sky-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">
            Staff Allocation
          </h2>
          <p className="text-sm text-slate-400">
            Monitor staff availability and assignments.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="font-semibold text-white">
          Staff Availability
        </h3>

        <p className="mt-2 text-sm text-slate-400">
          Staff assignments and availability will appear here
          when the resource module is connected.
        </p>

        <p className="mt-3 text-xs text-amber-400">
          Demo status: No staff data connected.
        </p>
      </div>
    </div>
  )
}
