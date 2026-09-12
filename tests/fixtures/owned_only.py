"""Mentions an owned term and nothing blocked.

OPENKIT is John's own system and is publishable, so this file must produce an INFO
finding and still pass. A scanner that blocks here is wrong in the expensive
direction: it would force scrubbing a term that was named on the public profile
deliberately.
"""

# Built as a companion to OPENKIT, the Openkit Bootstrap Framework.
RUNNER = "local"
