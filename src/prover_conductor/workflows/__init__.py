"""Durable runs, approvals, the merge queue, and the scheduling of agents over the work graph.

The durable engine is chosen when first needed; Ray actors never hold state that must survive a
restart (ADR-0005). Governing ADRs: ADR-0004, ADR-0005. No implementation yet.
"""
