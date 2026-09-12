# Skills Toolkit - Eval System Upgrade

Raises the eval committee from a defect-absence checker to a craft bar. Drop these
into the skills-toolkit eval references and upstream via PR to the source repo named
in each file's `upstream-source`.

## What changed and why
The old anchors scored 90-100 as "no meaningful gaps" - measuring absence of
defects, so competent-but-bland work scored 90+ with nowhere left to climb. This
upgrade recenters the bar so correct lands in the 70s and the 90s must be earned by
craft, depth, and originality.

## Files
- `references/quality-bar-rubric.md` - the recentred 0-100 bands + craft/depth/originality axes. Supersedes the old calibration anchors in eval.md and eval-competition.md.
- `agents/eval-alumni-adversary.md` - mandatory adversarial reviewer that finds the worst real fault and can CAP the score (major craft fault -> max 84).
- `skills/eval-scout-generate/SKILL.md` - on-demand evaluator generation under a fixed template, the library-gap protocol (small gap = update existing; large = new; ambiguous = ask), and PR-upstream growth.
- `agents/generated/eval-alumni-comic-craft.md` - a real generated evaluator (the comic-craft critic), proving the generation path.

## Not gamification
The harder bar and the always-name-a-weakness rule exist to force honest, consistent
thinking about what would make the work better - because nothing is ever finished -
not to manufacture engagement or extract turns. State this plainly when scoring.
