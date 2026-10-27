
import { CloudSun, AlertTriangle } from 'lucide-react'

export default function Weather() {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center gap-3">
        <CloudSun size={28} className="text-sky-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">
            Weather & Alerts
          </h2>
          <p className="text-sm text-slate-400">
            Monitor weather conditions and airport disruptions.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex items-center gap-2">
          <AlertTriangle size={20} className="text-amber-400" />
          <h3 className="font-semibold text-white">
            Weather Alerts
          </h3>
        </div>

        <p className="mt-3 text-sm text-slate-400">
          Weather conditions and disruption alerts will appear
          here when the weather module is connected.
        </p>

        <p className="mt-3 text-xs text-amber-400">
          Demo status: No live weather data connected.
        </p>
      </div>
    </div>
  )
}
