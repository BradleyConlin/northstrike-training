[![CI](https://github.com/BradleyConlin/northstrike-training/actions/workflows/ci.yml/badge.svg)](https://github.com/BradleyConlin/northstrike-training/actions/workflows/ci.yml)

# Northstrike Training & Deployment

This repo contains the full scaffold for simulation → training → evaluation → deployment → observability.
See `docs/architecture_overview.md` and the per-module READMEs. Fill in code where marked TODO.

## Quickstart
- `make rl_train_hover` (after setting up Python env)
- `make bench_waypoints` to run a sample benchmark

## Structure
See the repository tree and `docs/` for details.

![CI](https://github.com/BradleyConlin/northstrike-training/actions/workflows/ci.yml/badge.svg)

## Project status
- **CI:** [![CI](https://github.com/BradleyConlin/northstrike-training/actions/workflows/ci.yml/badge.svg)](https://github.com/BradleyConlin/northstrike-training/actions/workflows/ci.yml)
- **24-point dashboard:** [reports/24-point-status.md](reports/24-point-status.md)
- **Waypoint demo:** `python -m scripts.run_waypoint_demo --help`

## CI
[![Lint & Unit](https://github.com/BradleyConlin/northstrike-training/actions/workflows/lint_test.yml/badge.svg)](https://github.com/BradleyConlin/northstrike-training/actions/workflows/lint_test.yml)
[![Simulation Tests](https://github.com/BradleyConlin/northstrike-training/actions/workflows/sim_tests.yml/badge.svg)](https://github.com/BradleyConlin/northstrike-training/actions/workflows/sim_tests.yml)

[![Bench & Report](https://github.com/BradleyConlin/northstrike-training/actions/workflows/bench_and_report.yml/badge.svg)](https://github.com/BradleyConlin/northstrike-training/actions/workflows/bench_and_report.yml)
