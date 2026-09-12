// Telemetry schema, frozen 2026-09-12 (plan task T-12a).
//
// This is the hard serialisation point between the lanes. The page (Lane A) renders it, the
// checks (Lane B) compare against it, and Prompt A (Lane C) is the thing that produces it. It is
// versioned so that a report carrying an older shape can say so rather than silently miscompare.
//
// Every field is optional on the wire and defaulted here, because a real agent will sometimes be
// unable to answer part of the probe (no session log, a runner that does not record phases) and a
// missing answer must degrade one check rather than break the report.

export const TELEMETRY_SCHEMA_VERSION = 2

export const EMPTY_TELEMETRY = {
  schemaVersion: TELEMETRY_SCHEMA_VERSION,
  source: 'unknown',
  tools: [],
  toolCounts: {},
  skillsFired: [],
  skillCounts: {},
  agentsDispatched: [],
  tasksCreated: 0,
  phaseSequence: [],
  errors: [],
  environment: {},
  metrics: { durationMs: 0, inputTokens: 0, outputTokens: 0, totalTokens: 0 }
}

// The JSON shape Prompt A asks the agent to return. Kept as a literal so the prompt text and the
// parser can never drift apart: both read this one object.
export const PROBE_SCHEMA = {
  schemaVersion: TELEMETRY_SCHEMA_VERSION,
  source: 'claude-code | opencode | other',
  tools: ['ToolName'],
  toolCounts: { ToolName: 0 },
  skillsFired: ['skill-name'],
  skillCounts: { 'skill-name': 0 },
  agentsDispatched: ['agent-name'],
  tasksCreated: 0,
  phaseSequence: ['phase label in the order it actually ran'],
  errors: ['error message'],
  environment: {
    os: 'darwin | linux | win32',
    python3: 'version string, or null if absent',
    agent: 'agent name and version',
    gitWorktree: 'branch name, or null if not a git repo',
    gitDirty: false
  },
  metrics: { durationMs: 0, inputTokens: 0, outputTokens: 0 }
}

export function coerceTelemetry(value) {
  const input = value && typeof value === 'object' ? value : {}
  const metrics = input.metrics && typeof input.metrics === 'object' ? input.metrics : {}
  const inputTokens = Number(metrics.inputTokens) || 0
  const outputTokens = Number(metrics.outputTokens) || 0
  return {
    ...EMPTY_TELEMETRY,
    ...input,
    schemaVersion: Number(input.schemaVersion) || TELEMETRY_SCHEMA_VERSION,
    tools: [...new Set((input.tools || []).map(String))].sort(),
    toolCounts: input.toolCounts || {},
    skillsFired: [...new Set((input.skillsFired || []).map(String))].sort(),
    skillCounts: input.skillCounts || {},
    agentsDispatched: [...new Set((input.agentsDispatched || []).map(String))].sort(),
    tasksCreated: Number(input.tasksCreated) || 0,
    phaseSequence: (input.phaseSequence || []).map(String),
    errors: [...new Set((input.errors || []).map(String))].sort(),
    environment: input.environment || {},
    metrics: {
      durationMs: Number(metrics.durationMs) || 0,
      inputTokens,
      outputTokens,
      totalTokens: Number(metrics.totalTokens) || inputTokens + outputTokens
    }
  }
}
