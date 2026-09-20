"""prover-conductor: conducts agents that prove results in Lean.

Distribution `prover-conductor`, import package `prover_conductor`, command `conductor`
(ADR-0006). Each subpackage's docstring states its responsibility and its governing ADRs.
"""

from importlib import metadata

try:
    __version__ = metadata.version("prover-conductor")
except metadata.PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0+unknown"
