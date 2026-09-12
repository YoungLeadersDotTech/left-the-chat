// Proves the plugin's CLI (scripts/audit.mjs) actually runs against a real directory
// on disk: exits 0 on a clean directory, exits 0 and prints findings on a dirty one.
// No framework, same style as tests/js/audit.test.mjs.

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const SCRIPT = new URL('../../scripts/audit.mjs', import.meta.url).pathname

function run(dir) {
  try {
    const stdout = execFileSync('node', [SCRIPT, dir], { encoding: 'utf8' })
    return { code: 0, stdout }
  } catch (error) {
    return { code: error.status, stdout: error.stdout || '' }
  }
}

// Clean directory: no agent files at all.
const emptyDir = mkdtempSync(join(tmpdir(), 'ltc-audit-empty-'))
const emptyResult = run(emptyDir)
assert.equal(emptyResult.code, 0, 'must exit 0 on a directory with no agent files')
assert.match(emptyResult.stdout, /no .*files found/i, 'must say plainly that nothing was found')
rmSync(emptyDir, { recursive: true, force: true })

// Dirty directory: a skill file with real findings (no worked example, vague
// description, absolute instruction language) - the same shape the checks.js
// suite already exercises, on disk this time instead of in-memory.
const dirtyDir = mkdtempSync(join(tmpdir(), 'ltc-audit-dirty-'))
mkdirSync(join(dirtyDir, 'skills', 'tidy-up'), { recursive: true })
writeFileSync(
  join(dirtyDir, 'skills', 'tidy-up', 'SKILL.md'),
  `---
name: tidy-up
description: ${'Tidies things up in the repository and generally makes everything nicer for everyone involved in the project at any time. '.repeat(3)}
allowed-tools: Read, Write, Bash, TaskCreate
---

## Phase 1: Discover
Look at the files. Always do this. Never skip it.
`
)
const dirtyResult = run(dirtyDir)
assert.equal(dirtyResult.code, 0, 'must exit 0 even when findings are present - this is a report, not a gate')
assert.match(dirtyResult.stdout, /audited 1 file/i)
assert.match(dirtyResult.stdout, /(CRITICAL|MAJOR|MINOR)/, 'must print at least one severity group')
rmSync(dirtyDir, { recursive: true, force: true })

console.log('PASS  audit.mjs CLI: clean directory exits 0 with no findings, dirty directory exits 0 with findings printed')
