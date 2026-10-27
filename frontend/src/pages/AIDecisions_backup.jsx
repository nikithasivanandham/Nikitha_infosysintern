
import { useState } from "react";
import {
  BrainCircuit,
  Plane,
  Play,
  LoaderCircle,
  CheckCircle2,
  AlertCircle,
  ClipboardList,
  ShieldCheck,
  Search,
  CloudRain,
  ListChecks,
  FileText,
} from "lucide-react";

import api from "../api";

const severityStyles = {
  HIGH: "border-red-500/40 bg-red-500/10 text-red-300",
  MEDIUM: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  LOW: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
};

function formatLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function DataList({ title, items }) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-slate-200">
        {title}
      </h4>

      <ul className="space-y-2">
        {items.map((item, index) => (
          <li
            key={`${title}-${index}`}
            className="flex gap-2 text-sm text-slate-300"
          >
            <span className="text-sky-400">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RuleResultCard({ rule }) {
  const severity = String(rule.severity || "LOW").toUpperCase();
  const triggered = Boolean(rule.triggered);
  const severityClass =
    severityStyles[severity] || severityStyles.LOW;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-slate-500">
            {rule.rule_id || "Rule"}
          </p>

          <h5 className="mt-1 font-semibold text-white">
            {rule.rule_name || "Unnamed rule"}
          </h5>
        </div>

        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityClass}`}
        >
          {severity}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-2 text-sm">
        {triggered ? (
          <AlertCircle size={16} className="text-amber-400" />
        ) : (
          <CheckCircle2 size={16} className="text-emerald-400" />
        )}

        <span
          className={
            triggered ? "text-amber-300" : "text-emerald-300"
          }
        >
          {triggered ? "Rule triggered" : "Rule not triggered"}
        </span>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-300">
        {rule.message || "No message provided."}
      </p>
    </div>
  );
}

function RuleEngineResults({ ruleResults }) {
  if (!Array.isArray(ruleResults) || ruleResults.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No rule engine results are available.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {ruleResults.map((flightResult, index) => (
        <div
          key={`${flightResult.flight_number || "flight"}-${index}`}
          className="space-y-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs text-slate-500">
                Airport: {flightResult.airport_code || "N/A"}
              </p>

              <h4 className="font-semibold text-white">
                Flight {flightResult.flight_number || "N/A"}
              </h4>
            </div>

            <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs text-sky-300">
              {flightResult.triggered_rules ?? 0} triggered
            </span>
          </div>

          <div className="space-y-3">
            {Array.isArray(flightResult.results) &&
              flightResult.results.map((rule, ruleIndex) => (
                <RuleResultCard
                  key={rule.rule_id || ruleIndex}
                  rule={rule}
                />
              ))}
          </div>

          {flightResult.advisory_only && (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs leading-5 text-amber-200">
              Advisory only: this result supports operational
              review and does not authorize automatic action.
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function PlanningResults({ planningResult }) {
  if (
    !planningResult ||
    typeof planningResult !== "object" ||
    Object.keys(planningResult).length === 0
  ) {
    return (
      <p className="text-sm text-slate-500">
        No planning result is available.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-500">
            Planning status
          </span>

          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300">
            {planningResult.status || "Not specified"}
          </span>
        </div>

        <h4 className="mt-3 font-semibold text-white">
          Planning objective
        </h4>

        <p className="mt-2 text-sm leading-6 text-slate-300">
          {planningResult.planning_objective ||
            "No planning objective provided."}
        </p>

        <p className="mt-3 text-xs text-slate-500">
          Airport: {planningResult.airport || "N/A"}
        </p>
      </div>

      <DataList
        title="Research Requirements"
        items={planningResult.research_requirements}
      />

      <DataList
        title="Analysis Requirements"
        items={planningResult.analysis_requirements}
      />

      <DataList
        title="Resource Requirements"
        items={planningResult.resource_requirements}
      />

      <div>
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">
          <ListChecks size={18} className="text-sky-400" />
          Proposed Mitigation Steps
        </h4>

        {Array.isArray(planningResult.proposed_steps) &&
        planningResult.proposed_steps.length > 0 ? (
          <ol className="space-y-3">
            {planningResult.proposed_steps.map((step, index) => (
              <li
                key={`${index}-${step}`}
                className="flex gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-400/10 text-sm font-semibold text-sky-300">
                  {index + 1}
                </span>

                <span className="pt-1 text-sm leading-6 text-slate-300">
                  {step}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-slate-500">
            No proposed steps were returned.
          </p>
        )}
      </div>
    </div>
  );
}

function WorkflowSummary({ workflow }) {
  const input = workflow.input_data || {};
  const airport =
    workflow.planning_result?.airport || input.airport || workflow.airport;
  const flights =
    input.affected_flights ||
    (workflow.rule_results || []).map(
      (result) => result.flight_number
    ).filter(Boolean);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Plane size={20} className="text-sky-400" />
        <h3 className="font-semibold">Workflow Overview</h3>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-950 p-4">
          <p className="text-xs text-slate-500">Airport</p>
          <p className="mt-1 text-lg font-semibold text-white">
            {airport || "N/A"}
          </p>
        </div>

        <div className="rounded-lg bg-slate-950 p-4">
          <p className="text-xs text-slate-500">Affected flights</p>
          <p className="mt-1 text-lg font-semibold text-white">
            {flights.length}
          </p>
          <p className="mt-1 break-words text-xs text-slate-400">
            {flights.join(", ") || "None listed"}
          </p>
        </div>

        <div className="rounded-lg bg-slate-950 p-4">
          <p className="text-xs text-slate-500">Workflow status</p>
          <p className="mt-1 break-words text-sm font-semibold text-sky-300">
            {workflow.status || "Unknown"}
          </p>
        </div>
      </div>

      {input.disruption && (
        <div className="mt-4">
          <p className="text-xs text-slate-500">Disruption details</p>
          <p className="mt-1 text-sm text-slate-300">
            {input.disruption}
          </p>
        </div>
      )}

      {workflow.workflow_id && (
        <div className="mt-4">
          <p className="text-xs text-slate-500">Workflow ID</p>
          <p className="mt-1 break-all font-mono text-xs text-slate-300">
            {workflow.workflow_id}
          </p>
        </div>
      )}
    </section>
  );
}

export default function AIDecisions() {
  const [airport, setAirport] = useState("VGA");
  const [disruption, setDisruption] = useState("");
  const [affectedFlights, setAffectedFlights] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [workflow, setWorkflow] = useState(null);

  const [workflowIdToCheck, setWorkflowIdToCheck] = useState("");
  const [retrievedWorkflow, setRetrievedWorkflow] = useState(null);
  const [fetchError, setFetchError] = useState("");
  const [isFetching, setIsFetching] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setWorkflow(null);
    setRetrievedWorkflow(null);
    setFetchError("");

    const airportCode = airport.trim().toUpperCase();

    const flights = affectedFlights
      .split(",")
      .map((flight) => flight.trim())
      .filter(Boolean);

    if (!/^[A-Z]{3,4}$/.test(airportCode)) {
      setError(
        "Enter a 3- or 4-letter airport code, such as VGA, HYD, DEL, or BLR."
      );
      return;
    }

    if (!disruption.trim() || flights.length === 0) {
      setError(
        "Enter the disruption details and at least one affected flight."
      );
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/workflows/", {
        workflow_type: "airport_disruption",
        input_data: {
          airport: airportCode,
          disruption: disruption.trim(),
          affected_flights: flights,
        },
      });

      setWorkflow(response.data);

      if (response.data?.workflow_id) {
        setWorkflowIdToCheck(response.data.workflow_id);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;

      console.error(
        "Workflow request failed:",
        err.response?.data || err.message
      );

      if (detail && typeof detail === "object") {
        if (detail.workflow_id) {
          setWorkflow({
            workflow_id: detail.workflow_id,
            status: detail.status || "failed",
            input_data: {
              airport: airportCode,
              disruption: disruption.trim(),
              affected_flights: flights,
            },
            planning_result: null,
            rule_results: [],
          });
        }

        setError(
          detail.message ||
            "The workflow failed. Check the backend terminal."
        );
      } else if (typeof detail === "string") {
        setError(detail);
      } else if (err.response?.status === 401) {
        setError("Your login session may have expired. Sign in again.");
      } else if (err.response?.status === 403) {
        setError("You are not authorized to start this workflow.");
      } else if (err.response?.status === 422) {
        setError("The backend rejected the request. Check the required fields.");
      } else {
        setError(
          err.message === "Network Error"
            ? "Cannot connect to the backend. Check that FastAPI is running."
            : "The workflow failed. Check the backend terminal."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  async function fetchWorkflowById(event) {
    event.preventDefault();

    const id = workflowIdToCheck.trim();

    if (!id) {
      setFetchError("Please enter a workflow ID.");
      return;
    }

    setIsFetching(true);
    setFetchError("");
    setRetrievedWorkflow(null);

    try {
      const response = await api.get(
        `/workflows/${encodeURIComponent(id)}`
      );

      setRetrievedWorkflow(response.data);
    } catch (err) {
      const statusCode = err.response?.status;
      const detail = err.response?.data?.detail;

      if (statusCode === 401) {
        setFetchError(
          "401 Unauthorized: The token is missing, expired, or invalid."
        );
      } else if (statusCode === 403) {
        setFetchError(
          "403 Forbidden: You may not have permission to access this workflow."
        );
      } else if (statusCode === 404) {
        setFetchError(
          "404 Not Found: Check the workflow ID and make sure it belongs to your account."
        );
      } else {
        setFetchError(
          typeof detail === "string"
            ? detail
            : detail?.message ||
                err.message ||
                "Failed to retrieve workflow."
        );
      }

      console.error(
        "Workflow retrieval failed:",
        err.response?.data || err.message
      );
    } finally {
      setIsFetching(false);
    }
  }

  const displayedWorkflow = retrievedWorkflow || workflow;

  const ruleResults = displayedWorkflow?.rule_results || [];
  const planningResult = displayedWorkflow?.planning_result;

  
    const triggeredCount = ruleResults.reduce(
        (total, flightResult) => {
            const rules = Array.isArray(flightResult.results)
            ? flightResult.results
            : [];

            return (
            total +
            rules.filter((rule) => rule.triggered === true).length
            );
        },
        0
    );

  return (
    <div className="space-y-6 p-6 text-white">
      <header className="flex items-center gap-3">
        <div className="rounded-xl bg-sky-400/10 p-3">
          <BrainCircuit size={28} className="text-sky-400" />
        </div>

        <div>
          <h2 className="text-2xl font-bold">AI Decisions</h2>
          <p className="mt-1 text-sm text-slate-400">
            Airport disruption planning and rule engine assessment.
          </p>
        </div>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-5 flex items-center gap-2">
          <Plane size={20} className="text-sky-400" />
          <h3 className="font-semibold">Start Airport Workflow</h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="airport"
              className="mb-2 block text-sm text-slate-300"
            >
              Airport Code
            </label>

            <input
              id="airport"
              value={airport}
              onChange={(event) =>
                setAirport(event.target.value.toUpperCase())
              }
              placeholder="VGA"
              maxLength={4}
              pattern="[A-Za-z]{3,4}"
              title="Enter a 3- or 4-letter airport code."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-sky-400"
              required
            />
          </div>

          <div>
            <label
              htmlFor="disruption"
              className="mb-2 block text-sm text-slate-300"
            >
              Disruption Details
            </label>

            <textarea
              id="disruption"
              value={disruption}
              onChange={(event) => setDisruption(event.target.value)}
              placeholder="Example: Heavy rain causing flight delays"
              rows={3}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-sky-400"
              required
            />
          </div>

          <div>
            <label
              htmlFor="flights"
              className="mb-2 block text-sm text-slate-300"
            >
              Affected Flight Numbers
            </label>

            <input
              id="flights"
              value={affectedFlights}
              onChange={(event) => setAffectedFlights(event.target.value)}
              placeholder="AI101, 6E202"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-sky-400"
              required
            />

            <p className="mt-2 text-xs text-slate-500">
              Separate flight numbers with commas.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-sky-400 px-4 py-3 font-semibold text-slate-950 hover:bg-sky-300 disabled:opacity-60"
          >
            {loading ? (
              <>
                <LoaderCircle size={18} className="animate-spin" />
                Running Workflow...
              </>
            ) : (
              <>
                <Play size={18} />
                Run Planning Workflow
              </>
            )}
          </button>
        </form>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Search size={20} className="text-sky-400" />
          <h3 className="font-semibold">Retrieve Existing Workflow</h3>
        </div>

        <form
          onSubmit={fetchWorkflowById}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <input
            value={workflowIdToCheck}
            onChange={(event) =>
              setWorkflowIdToCheck(event.target.value)
            }
            placeholder="Enter workflow ID"
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 text-sm outline-none focus:border-sky-400"
            required
          />

          <button
            type="submit"
            disabled={isFetching}
            className="flex items-center justify-center gap-2 rounded-lg bg-sky-400 px-5 py-3 font-semibold text-slate-950 hover:bg-sky-300 disabled:opacity-60"
          >
            {isFetching ? (
              <>
                <LoaderCircle size={18} className="animate-spin" />
                Fetching...
              </>
            ) : (
              <>
                <Search size={18} />
                Fetch Workflow
              </>
            )}
          </button>
        </form>

        {fetchError && (
          <p
            role="alert"
            className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
          >
            {fetchError}
          </p>
        )}

        {retrievedWorkflow && (
          <p className="mt-3 text-sm text-emerald-300">
            Saved workflow retrieved successfully.
          </p>
        )}
      </section>

      {displayedWorkflow && (
        <>
          <WorkflowSummary workflow={displayedWorkflow} />

          <section className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <BrainCircuit size={22} className="text-sky-400" />
              <p className="mt-3 text-sm text-slate-400">
                Planning objective
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {planningResult ? "Available" : "Not available"}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <ShieldCheck size={22} className="text-emerald-400" />
              <p className="mt-3 text-sm text-slate-400">
                Flights assessed
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {ruleResults.length}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <CloudRain size={22} className="text-amber-400" />
              <p className="mt-3 text-sm text-slate-400">
                Triggered rules
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {triggeredCount}
              </p>
            </div>
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-5 flex items-center gap-2">
              <FileText size={20} className="text-sky-400" />
              <h3 className="text-lg font-semibold">
                Planning Agent Results
              </h3>
            </div>

            <PlanningResults planningResult={planningResult} />
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-5 flex items-center gap-2">
              <ShieldCheck size={20} className="text-emerald-400" />
              <h3 className="text-lg font-semibold">
                Rule Engine Results
              </h3>
            </div>

            <RuleEngineResults ruleResults={ruleResults} />
          </section>

          <p className="text-xs leading-5 text-slate-500">
            Operational note: Planning and rule engine outputs are
            advisory information. Verify live weather, flight status,
            runway conditions, and authorized operational procedures
            before making real-world decisions.
          </p>
        </>
      )}

      {!displayedWorkflow && !loading && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
          <ClipboardList
            size={36}
            className="mx-auto mb-3 text-slate-600"
          />
          <p className="font-medium text-slate-300">
            No workflow selected
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Run a new workflow or retrieve an existing workflow ID
            to display its results here.
          </p>
        </div>
      )}
    </div>
  );
}
