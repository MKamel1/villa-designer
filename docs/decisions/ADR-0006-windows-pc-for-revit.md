# ADR-0006 — Revit on the Windows PC; single-machine VM deferred

- **Status:** accepted
- **Date:** 2026-09-20

## Context

Revit is Windows-only; there is no Linux build and Wine is not a viable
path for Autodesk products. The client asked whether everything could run
on the Linux workstation to minimise platforms.

Measured on `ai-workstation`: AMD-V present, `/dev/kvm` present, IOMMU
already active with 36 groups, and **two GPUs** — the RTX 3090 plus the
9950X integrated AMD graphics. That is precisely the configuration GPU
passthrough requires: host on the iGPU, 3090 passed to a Windows guest.

## Decision

Run Revit and AutoCAD on the existing Windows PC for now. Record the
Windows-VM-on-the-workstation option as viable and deferred.

## Consequences

- Zero setup risk; work starts immediately.
- Two machines, coordinated by git.
- **The data-sync concern is already solved by ADR-0002**, not by machine
  count. Consolidating is a convenience win, not a correctness one — which
  is what makes deferring it safe.

## Revisit when

The VM becomes worth building once the Revit and lighting work is proven.
Open questions to resolve first: whether the 3090 isolates cleanly in its
IOMMU group, a Windows licence for the guest, and how Autodesk activation
behaves inside a VM (permitted in general, but fingerprinting is an
unverified risk).
