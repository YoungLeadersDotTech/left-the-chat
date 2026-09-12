// New checks ported from the toast-validation-suite corpus (C43, C34, C35, C23) plus three
// optional style validations (em dash, emoji-heavy, AI-ism marketing tone). All are pure
// single-file/whole-text checks with no subprocess or git dependency, so they run identically
// on a lone pasted file and on every file inside a zip drop.

import assert from 'node:assert/strict'
import { inspectSetup, inspectOptionalStyle } from '../../src/lib/checks.js'

function findingIds(files) {
  return inspectSetup(files).findings.map((item) => item.id.split(':')[0])
}

// C43: duplicate frontmatter key
const dupKey = [{
  name: 'skills/demo/SKILL.md',
  content: '---\nname: demo\ndescription: A demo skill with a long enough description to pass the length check easily\nname: demo-again\nallowed-tools: Read\n---\n\nBody.\n'
}]
assert.ok(findingIds(dupKey).includes('CFG-020'), 'must flag a duplicate top-level frontmatter key')

// C34: doubled horizontal rule
const doubledRule = [{
  name: 'skills/demo/SKILL.md',
  content: '---\nname: demo\ndescription: A demo skill with a long enough description to pass the length check easily\nallowed-tools: Read\n---\n\nText.\n\n---\n\n---\n\nMore text.\n'
}]
assert.ok(findingIds(doubledRule).includes('STYLE-004'), 'must flag two --- dividers separated only by a blank line')

// C34 must not fire on a legitimate fenced example containing --- lines
const fencedRule = [{
  name: 'skills/demo/SKILL.md',
  content: '---\nname: demo\ndescription: A demo skill with a long enough description to pass the length check easily\nallowed-tools: Read\n---\n\n```yaml\n---\n\n---\n```\n'
}]
assert.ok(!findingIds(fencedRule).includes('STYLE-004'), 'must not flag --- lines inside a fenced code example')

// C35: duplicated lead-in phrase
const dupLeadIn = [{
  name: 'AGENTS.md',
  content: '**Use for**: Use for: reviewing pull requests and other repository tasks that need doing on a regular basis.\n'
}]
assert.ok(findingIds(dupLeadIn).includes('STYLE-005'), 'must flag a bold lead-in label repeated as plain text')

// C23: unclosed code fence (odd fence count)
const unclosedFence = [{
  name: 'AGENTS.md',
  content: 'Intro text that is long enough to pad past any minimum length threshold this check might apply.\n\n```bash\necho hello\n\nRun TaskUpdate(id, status) here but this is still inside the open fence.\n'
}]
assert.ok(findingIds(unclosedFence).includes('STYLE-006'), 'must flag an odd number of ``` fence markers')

const closedFence = [{
  name: 'AGENTS.md',
  content: 'Intro text that is long enough to pad past any minimum length threshold this check might apply.\n\n```bash\necho hello\n```\n\nRun TaskUpdate(id, status) here, outside the fence.\n'
}]
assert.ok(!findingIds(closedFence).includes('STYLE-006'), 'must not flag a properly closed fence pair')

// Optional validations - all tagged source: 'optional'
const emDash = inspectOptionalStyle('A sentence with an em dash — right in the middle.')
assert.equal(emDash.length, 1)
assert.equal(emDash[0].id, 'STYLE-007')
assert.equal(emDash[0].source, 'optional')

const emoji = inspectOptionalStyle('Great work team! \u{1F680} \u{1F389} \u{2705} shipping this now!')
assert.equal(emoji.length, 1)
assert.equal(emoji[0].id, 'STYLE-008')
assert.equal(emoji[0].source, 'optional')

const aiIsm = inspectOptionalStyle('Our robust, cutting-edge solution will leverage seamless synergy to unlock unparalleled value.')
assert.equal(aiIsm.length, 1)
assert.equal(aiIsm[0].id, 'STYLE-009')
assert.equal(aiIsm[0].source, 'optional')

// A single normal use of one AI-ism word must not trip the density threshold
const oneWord = inspectOptionalStyle('This solution is robust enough for daily use by the whole team.')
assert.ok(!oneWord.some((item) => item.id === 'STYLE-009'), 'a lone AI-ism word must not trigger the density-gated finding')

// Clean prose triggers nothing
assert.deepEqual(inspectOptionalStyle('A perfectly ordinary sentence with nothing unusual in it at all.'), [])

console.log('PASS  copy-paste checks (CFG-020, STYLE-004/005/006) and optional validations (STYLE-007/008/009) fire correctly and stay quiet on clean input')
