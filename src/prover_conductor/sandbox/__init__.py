"""SandboxRunner and its backends: Ray Sandboxes (gVisor) on clusters and an OS-level sandbox
locally. Every execution of tenant-controlled or model-written code goes through this package.

Governing ADRs: ADR-0005, ADR-0008. Deterministic layer. No implementation yet.
"""
