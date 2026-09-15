"""cufolio_lab — shadow portfolio-allocation sidecar for hq-trading-system.

Reads HQ's calendar-aligned daily-returns artifact and writes ONE advisory
allocation flag-file. Never routes orders, never sizes real capital, never on
any trade hot path. Shadow until the research gate clears.
"""
__version__ = "0.1.0"
