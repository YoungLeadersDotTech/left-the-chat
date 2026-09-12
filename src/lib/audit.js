import { stableStringify } from './deterministic.js'

const TOOL_PATTERN = /(?:allowedTools|tools|tool_names)\s*[=:]\s*\[([^\]]*)\]/gi
const SKILL_PATTERN = /(?:skill|skills)\s*[=:]\s*\[([^\]]*)\]/gi

function extract(pattern, text) {
  const values = []
  for (const match of text.matchAll(pattern)) {
    values.push(...match[1].split(',').map((item) => item.replace(/["'`\s]/g, '')).filter(Boolean))
  }
  return [...new Set(values)].sort()
}

function finding(id, severity, title, detail, source = 'configuration') {
  return { id, severity, title, detail, source }
}

export function inspectSetup(files) {
  const ordered = [...files].sort((a, b) => a.name.localeCompare(b.name))
  const combined = ordered.map((file) => `--- ${file.name}\n${file.content}`).join('\n')
  const tools = extract(TOOL_PATTERN, combined)
  const skills = extract(SKILL_PATTERN, combined)
  const findings = []

  if (!ordered.length) findings.push(finding('CFG-001', 'critical', 'No setup files loaded', 'Add an agent configuration, instructions file, or pasted setup before running the audit.'))
  if (ordered.length && !tools.length) findings.push(finding('CFG-002', 'critical', 'Tool permissions are implicit', 'Declare an explicit tool allowlist so runtime access can be compared deterministically.'))
  if (/\b(always|never)\b/gi.test(combined) && !/exception|unless/gi.test(combined)) findings.push(finding('STYLE-001', 'minor', 'Absolute instruction language', 'Review absolute rules for missing exceptions or precedence.', 'prose'))
  if (combined.length > 12000) findings.push(finding('STYLE-002', 'minor', 'Large instruction surface', 'The setup exceeds 12,000 characters; consider separating core rules from reference material.', 'prose'))
  return { files: ordered.map((file) => file.name), declared: { tools, skills }, findings }
}

export function enrichAudit(staticAudit, telemetry) {
  const pricingTable = { version: '2026-09-v1', inputUsdPerMillion: 3, outputUsdPerMillion: 15 }
  const findings = [...staticAudit.findings]
  for (const tool of staticAudit.declared.tools) {
    if (!telemetry.tools.includes(tool)) findings.push(finding(`RUN-UNUSED-${tool}`, 'critical', `Declared tool never used: ${tool}`, 'Runtime telemetry contains no matching invocation.', 'runtime'))
  }
  for (const tool of telemetry.tools) {
    if (staticAudit.declared.tools.length && !staticAudit.declared.tools.includes(tool)) findings.push(finding(`RUN-UNDECLARED-${tool}`, 'critical', `Undeclared tool used: ${tool}`, 'Runtime telemetry reports access outside the declared allowlist.', 'runtime'))
  }
  telemetry.errors.forEach((error, index) => findings.push(finding(`RUN-ERROR-${String(index).padStart(3, '0')}`, 'critical', 'Unhandled runtime error', error, 'runtime')))
  findings.sort((a, b) => a.severity.localeCompare(b.severity) || a.id.localeCompare(b.id))
  return {
    reportVersion: 1,
    pricingTable,
    declared: staticAudit.declared,
    actual: telemetry,
    metrics: {
      ...telemetry.metrics,
      estimatedCostUsd: Number(((telemetry.metrics.inputTokens / 1000000) * pricingTable.inputUsdPerMillion + (telemetry.metrics.outputTokens / 1000000) * pricingTable.outputUsdPerMillion).toFixed(6)),
      errorCount: telemetry.errors.length,
      findingCount: findings.length,
      criticalCount: findings.filter((item) => item.severity === 'critical').length
    },
    findings
  }
}

export function buildPromptA(staticAudit) {
  return `Run a read-only environment probe for this agent setup. Return JSON only using schema {"source":"agent","tools":["tool_name"],"errors":[],"metrics":{"durationMs":0,"inputTokens":0,"outputTokens":0}}. Declared surface: ${stableStringify(staticAudit.declared)}`
}

export function buildPromptB(report) {
  const critical = report.findings.filter((item) => item.severity === 'critical').map(({ id, title, detail }) => ({ id, title, detail }))
  return `Fix the agent setup issues below without expanding permissions. Preserve working behavior, make the smallest deterministic changes, then rerun the same probe and return the telemetry JSON. Findings: ${stableStringify(critical)}`
}
