"""Transactional install engine for `maika init` / `maika update`.

A planner turns a fully-staged desired tree plus the current target into a
pure-data action list; a transaction engine applies it atomically (preflight,
backup, temp-file + os.replace, journal, reverse rollback) so any failure
restores the exact pre-operation target state.
"""
