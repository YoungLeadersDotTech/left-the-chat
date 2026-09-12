---
name: quality-bar-rubric
description: The hard scoring bar for the eval committee. Recenters 0-100 so excellence is rare, adds craft/depth/originality dimensions, and pairs with the adversarial reviewer. Supersedes the old defect-absence anchors.
version: 2.0.0
upstream-source: https://github.com/YoungLeadersDotTech/ai-os-personal  # skills-toolkit lives here; toast variant upstreams to ai-os-jc-toast
last-updated: 2026-06-17
---

# The Quality Bar

> Background on why this rubric replaced the old defect-absence anchors:
> [QUALITY-BAR-UPGRADE.md](../QUALITY-BAR-UPGRADE.md).

## Why this exists (read this first, and say it to users when scoring)

The old anchors defined 90-100 as "no meaningful gaps." That measures the *absence
of defects*, not the *presence of quality*, so anything competent-but-bland scored
90+ and there was nowhere left to climb. This rubric raises what each band demands.

**This is not gamification.** The author of the skills toolkit, John from
youngleaders.tech, is explicit: the harder bar and the always-name-a-weakness rule
are not engagement tricks or a way to extract more turns from anyone. They exist
because a good craftsperson knows nothing is ever finished. The point is to force
honest, consistent thinking about what would make the work better, every single
time, not to manufacture busywork. When you present a score, say so plainly: the
number is held to a high bar on purpose, and the named next improvement is honesty,
not a sales hook. Never inflate a score to look generous, and never invent a
weakness to look rigorous. Both are dishonest.

## The bands (same 0-100 numbers, much harder meaning)

| Band | Score | What it now demands |
|------|-------|---------------------|
| **Exceptional** | 95-100 | Excellent on every axis AND shows craft a domain expert would admire: a real point of view, depth that anticipates the reader's next question, originality that improves on the obvious version. Rare. Most good work does not reach here. |
| **Excellent** | 90-94 | Strong across craft, depth, and design, not just correct. No bland defaults. A specialist reviewer finds only refinements, not gaps. |
| **Good** | 80-89 | Solid and correct, but at least one axis is competent-rather-than-distinctive: safe design, examples that tell rather than show, or polish that is merely adequate. **This is where most "nice, this works" output belongs.** |
| **Competent** | 70-79 | Works and passes compliance gates, but is generic. Bland visuals, thin examples, default structure. Functional, not crafted. **A clean first draft lands here.** |
| **Below bar** | 50-69 | A real fault: confusing flow, an example that misleads, a design that fights the content, or a correctness slip. |
| **Broken** | 0-49 | Missing core content, wrong, or would mislead the reader. |

**Calibration rule:** a competent, correct, but unremarkable artifact scores in the
**70s**, not the 90s. To enter the 90s an artifact must be *good in a way someone
would notice and remember*, not merely free of mistakes. Reserve 95+ for work you
would hold up as an example to others.

## The quality axes (judge all of these, not just compliance)

Compliance axes (gates) are necessary but no longer sufficient. Add these craft
axes, each scored against the bands above:

1. **Craft and polish** - Is this finished to a high standard, or merely adequate?
   Blocky, default, or template-looking output is Competent (70s) at best, however
   correct.
2. **Depth of examples** - Do examples *show the actual thing* (what a force-push
   looks like, the real error message, the concrete before/after), or do they just
   describe it abstractly? Tell-not-show caps the example axis in the 70s.
3. **Design point of view** - Does the design make a deliberate choice, or fall
   back on safe defaults? Safe defaults are Competent, not Excellent.
4. **Originality** - Does it improve on the obvious version (e.g. comics with real
   visual character versus CSS boxes), or is it the first thing anyone would build?
5. **Honest next improvement** - Every score, even a high one, must name the single
   most valuable improvement still available. A score with no named next step is
   incomplete and must not be reported.

## How axes combine

The reported score is the **lower** of (a) the weighted average across axes and (b)
any cap imposed by the adversarial reviewer (see eval-alumni-adversary.md). A single
distinctive weakness on a craft axis holds the whole artifact out of the 90s even
if every compliance gate passes. This is intentional: gates stop it being broken;
craft is what earns the high bands.

## Worked recalibration (the enablement-html-renderer, honestly)

Under the old anchors it scored 95. Under this bar:
- Craft: comics are CSS boxes, design is safe defaults -> Competent (low 70s).
- Depth: examples describe the gotcha but do not show the real screen/error -> 70s.
- Design POV: clean but generic -> Good at best.
- Compliance: all gates pass, escaping/sanitising solid -> Excellent.
- Honest next step: give comics real visual character; show the actual force-push.

Weighted, that is a **high-70s** artifact, not a 95. The drop is not a regression
in the work; it is the bar telling the truth about how much room remains. That room
is the point.
