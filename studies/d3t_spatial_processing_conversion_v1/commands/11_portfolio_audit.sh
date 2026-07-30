#!/usr/bin/env bash
set -euo pipefail
se-exploration-portfolio-audit \
  --ledger state/decisions/exploration_candidate_ledger.json \
  --candidate-dir studies \
  --output analyses/governance/exploration_portfolio_audit
