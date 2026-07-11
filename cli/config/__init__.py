"""Canonical Maika project configuration.

`project.yaml` is the single source of truth for which host adapters are
enabled over one shared `.maika` core and which is primary; `platforms.yaml`
records each enabled adapter's descriptor; `install-manifest.yaml` records the
exact files each adapter installed (so disable removes precisely them).
"""
