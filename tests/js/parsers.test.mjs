// T-12e follow-up: parseOpenCodeLog was renamed to parseGenericLog because it was never an
// OpenCode parser (OpenCode keeps session data in a SQLite database, not a JSON/JSONL log, and
// its tool rows use a bare `tool` field the walker doesn't read). This proves the rename didn't
// quietly break the generic JSON/JSONL walking that does genuinely work.

import assert from 'node:assert/strict'
import { parseGenericLog, parseTelemetry } from '../../src/lib/parsers.js'

// A plain JSON array of generic tool-call-shaped records - not Claude Code's shape, not
// OpenCode's real shape, just the generic tool_name/usage fields the walker understands.
const GENERIC_ARRAY = JSON.stringify([
  { tool_name: 'Read', usage: { input_tokens: 100, output_tokens: 20 } },
  { tool_name: 'Read', usage: { input_tokens: 50, output_tokens: 10 } },
  { tool_name: 'Bash', usage: { input_tokens: 30, output_tokens: 5 } }
])

const direct = parseGenericLog(GENERIC_ARRAY)
assert.equal(direct.source, 'generic')
assert.deepEqual(direct.toolCounts, { Read: 2, Bash: 1 })
assert.equal(direct.metrics.inputTokens, 180)
assert.equal(direct.metrics.outputTokens, 35)

// Same input via the public parseTelemetry entry point, explicit 'generic' strategy.
const viaStrategy = parseTelemetry(GENERIC_ARRAY, 'generic')
assert.deepEqual(viaStrategy.toolCounts, { Read: 2, Bash: 1 })

// JSONL form - one record per line, the other real-world shape the walker has to handle.
const GENERIC_JSONL = GENERIC_ARRAY
  ? JSON.parse(GENERIC_ARRAY).map((record) => JSON.stringify(record)).join('\n')
  : ''
const viaJsonl = parseGenericLog(GENERIC_JSONL)
assert.deepEqual(viaJsonl.toolCounts, { Read: 2, Bash: 1 })

// The auto-detect fallback for anything that doesn't look like a Claude Code log must still
// route to the generic walker (renamed from the opencode branch), not throw or silently drop.
const viaAuto = parseTelemetry(GENERIC_ARRAY, 'auto')
assert.deepEqual(viaAuto.toolCounts, { Read: 2, Bash: 1 })

console.log('PASS  parsers.js: parseGenericLog (renamed from parseOpenCodeLog) still parses JSON array, JSONL, and the auto-detect fallback route to it')
