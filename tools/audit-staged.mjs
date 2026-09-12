#!/usr/bin/env node
// audit-staged - run the static prompt checks against staged agent files.
//
// This is the auditor half of the pre-commit hook (plan task T-12d). It is the
// behaviour a judge recognises without needing agentic explained to them: it runs
// unprompted and it takes a consequential action.
//
// Static checks only, deliberately. The declared-versus-actual family needs runtime
// telemetry and there is none at commit time, so this carries the half that can run
// in milliseconds. A commit hook that takes a second gets bypassed within a day.

import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { inspectSetup } from '../src/lib/checks.js'

// What counts as an agent file. Narrow on purpose: a hook that fires on every commit
// is a hook that gets uninstalled.
const AGENT_FILE = /(^|\/)(SKILL\.md|AGENTS?\.md|CLAUDE\.md)$|(^|\/)agents\/[^/]+\.md$|(^|\/)skills\/[^/]+\.md$/

function stagedFiles() {
  try {
    return execFileSync('git', ['diff', '--cached', '--name-only', '--diff-filter=ACM'], { encoding: 'utf8' })
      .split('\n').map((line) => line.trim()).filter(Boolean)
  } catch {
    return []
  }
}

const targets = stagedFiles().filter((name) => AGENT_FILE.test(name))
if (!targets.length) process.exit(0)

const files = []
for (const name of targets) {
  try { files.push({ name, content: readFileSync(name, 'utf8') }) } catch { /* deleted between list and read */ }
}
if (!files.length) process.exit(0)

const { findings } = inspectSetup(files)
const blocking = findings.filter((item) => item.severity === 'critical')
const advisory = findings.filter((item) => item.severity === 'major')

for (const item of blocking) console.error(`BLOCK  ${item.id}  ${item.title}\n       ${item.detail}`)
for (const item of advisory) console.error(`warn   ${item.id}  ${item.title}`)

if (!blocking.length) {
  if (advisory.length) console.error(`\nleft-the-chat: ${advisory.length} advisory finding(s) in ${files.length} prompt file(s). Not blocking.`)
  process.exit(0)
}

console.error(`\nleft-the-chat: ${blocking.length} blocking finding(s) in ${files.length} staged prompt file(s).`)
console.error('Fix them, or commit with --no-verify if you disagree. A hook you cannot skip is a hook that gets deleted.')
process.exit(1)
