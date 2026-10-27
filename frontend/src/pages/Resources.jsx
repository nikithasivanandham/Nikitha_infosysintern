
import { DoorOpen } from 'lucide-react'

export default function Resources() {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center gap-3">
        <DoorOpen size={28} className="text-sky-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">
            Gates & Resources
          </h2>
          <p className="text-sm text-slate-400">
            Monitor gate availability and resource status.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="font-semibold text-white">
          Resource Availability
        </h3>

        <p className="mt-2 text-sm text-slate-400">
          Gate assignments and resource availability will appear
          here when the resource module is connected.
        </p>

        <p className="mt-3 text-xs text-amber-400">
          Demo status: No resource data connected.
        </p>
      </div>
    </div>
  )
}
