"""A deliberately realistic leak fixture.

Nothing here puts a blocked term on a line of its own. That is the point: a scanner
that only matches bare terms passes this file and reports it clean, which is the
failure mode worth testing for.
"""

# The Zephyr Pay reconciliation path still assumes a single settlement window.
LEDGER_ROOT = "/srv/deal-ledger/ledgers"


def resolve(account_id: str) -> str:
    """Return the ledger path for an account."""
    return f"{LEDGER_ROOT}/{account_id}.json"
