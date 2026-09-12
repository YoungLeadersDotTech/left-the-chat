// PII-001 is graded major, so a false positive here is the finding most likely to make someone
// distrust the whole report. These cases come from a real 200-plugin corpus, where 84 matches for
// the phone shape contained almost no phone numbers - mostly Unix and Slack timestamps.
import { inspectSetup } from '../../src/lib/checks.js'

const PAD = ' '.repeat(50)
const pii = (text) => inspectSetup([{ name: 't.md', content: text + PAD }])
  .findings.filter((f) => f.id.startsWith('PII-001'))

const QUIET = {
  'slack or unix timestamp': 'Recorded at [source-ts: 1773856303] in the log.',
  'millisecond timestamp': 'Timestamp 1789220772634 was captured.',
  'ascending placeholder': 'Use 1234567890 as the example id.',
  'zero-led placeholder': 'Use 0123456789 as the example id.',
  'bare ten-digit id': 'Account 4971757731 is the record.',
  'iso dates': 'Runs 2026-11-03 to 2026-11-05 in Dublin.',
  'year with a plus': 'Changelog entry +2014 was the first release.',
  'semver': 'Bumped to 1.2.3 in this release.'
}

const FIRES = {
  'international': 'Call me on +353 87 123 4567 if it breaks.',
  'us parenthesised': 'Reach support at (555) 123-4567 today.',
  'us dashed': 'Call 555-123-4567 for help with this.',
  'dotted': 'Ring 087.123.4567 and ask for me.'
}

const failures = []
for (const [name, text] of Object.entries(QUIET)) {
  if (pii(text).length) failures.push(`false positive on ${name}`)
}
for (const [name, text] of Object.entries(FIRES)) {
  if (!pii(text).length) failures.push(`missed a real phone number: ${name}`)
}

// A located finding is the point of carrying a line at all.
const located = inspectSetup([{ name: 't.md', content: `line one\nline two\nCall 555-123-4567 now.${PAD}` }])
  .findings.filter((f) => f.id.startsWith('PII-001'))
if (!located.length) failures.push('expected a phone finding to locate')
else if (located[0].line !== 3) failures.push(`expected line 3, got ${located[0].line}`)

if (failures.length) {
  console.error('FAIL  PII precision')
  for (const f of failures) console.error('      ' + f)
  process.exit(1)
}
console.log(`PASS  PII precision: ${Object.keys(QUIET).length} identifier shapes stay quiet, ${Object.keys(FIRES).length} real phone formats fire, finding reports its line`)
