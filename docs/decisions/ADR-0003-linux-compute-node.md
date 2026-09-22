# ADR-0003 — ai-workstation runs everything non-Autodesk

- **Status:** accepted
- **Date:** 2026-09-20

## Context

Lighting simulation and rendering are computationally heavy. Measured
capability of the SSH host `ai-workstation`:

- Ubuntu 24.04, 32-core Ryzen 9 9950X, 91 GB RAM, 1.2 TB free
- NVIDIA RTX 3090, 24 GB
- Docker, Python 3.12, git present; Blender and Radiance absent

## Decision

All non-Autodesk work runs on `ai-workstation`: the rule engine, lighting
calculation, Radiance, Blender renders, viewer builds. Windows keeps only
Revit and AutoCAD. git is the contract between the two machines.

## Consequences

- Radiance is CPU-only, so it uses the 32 cores and never contends with
  anything wanting the GPU. Blender Cycles takes the 3090.
- Toolchains go in Docker so they are reproducible and do not pollute the
  host.
- Two machines must stay coordinated — solved by git, not by copying, and
  made safe by ADR-0002 (one authored artifact).

## Alternatives rejected

- **Everything on Windows** — wastes a 32-core/3090 machine and makes
  Radiance and Blender slower.
- **Everything on Linux** — impossible; Revit has no Linux build
  (see ADR-0006).
