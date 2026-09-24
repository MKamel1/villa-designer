# Intake and evidence templates

## Client-approved luxury quality brief

The design lead fills this through conversation, then reads it back in plain
language. “A+ luxury” names the agreed level of quality; it is not a certification.

| Topic | Capture | Test or decision |
|---|---|---|
| Household | People, guests, pets, likely change | Who needs separate space and when? |
| Routine | Waking, meals, work, laundry, sleep | Walk each routine through the plan |
| Hosting | Numbers, frequency, overnight stays, catering | Guest route, service route, private escape |
| Privacy | Visual and acoustic sensitivities | Sightlines and noise paths |
| Storage | Items, luggage, seasonal goods, cleaning equipment | Named storage location and usable access |
| Accessibility | Current and future mobility, sight, hearing | Entry, bathroom and bedroom activity tests |
| Comfort | Reading, darkness, temperature, air, sound | Room-specific measurable or qualitative target |
| Atmosphere | Reference image and original source | Proportion, palette, texture, light, mood; what to avoid |
| Maintenance | Cleaning frequency, staffing, patina tolerance | Cleaning and replacement path per material/equipment |
| Budget | Currency, date, range, contingency, exclusions | Cost assumptions and trade-off priorities |
| Quality priorities | Must, should, optional | What is protected if cost or area increases? |
| Approval | Client, date, revision, approved/revise | Explicit decision; no inferred consent |

For each requirement record an identifier, client wording, design interpretation,
priority, response, evidence artifact and unresolved question. Keep preference
records with that client. Reference images require rights and attribution checks
before reproduction. If none are supplied, keep the taste board provisional.

## Stage package

Record stage number/name, required facts, client-friendly questions, expert
methods, evidence card identifiers, diagram, worked calculation with all units,
qualitative criteria, failure/remedy/downstream consequence, deliverables and
approval criteria. Store shared methods in `knowledge/library.json`; stage skills
link to this material rather than copy book content.

## Source and evidence intake

Record author, title, edition, publisher, identifier, topics, access location,
rights, acquisition priority and status. Use `identified` until actual content is
read; use `content_verified` only for the stated coverage. Public-source editions
include access date. A new edition requires renewed passage checks.

For each card capture source identifier, edition, exact locator, short paraphrase,
category, conditions, exceptions, units, verification method and status. A
numerical card also needs `original_page_checked`, `verified_value` and
`regression_test`. Record every required interpretation condition in
`applies_when`, mapping a project fact name to allowed values. Do not use a
generic climate label where humidity, season, operating mode or hemisphere matter.
Diagram-dependent dimensions remain unresolved if the diagram or footnotes are
missing. No numerical card is enabled in the seed library.

## Project manifest

Use the labelled [pilot manifest](../../knowledge/projects/villa-pilot.json) as
the structural example, not as a real project brief. `id` identifies the project;
`revision` identifies the reviewed design version; `example` prevents a
demonstration from approving a real design. Every `facts` entry has `value`,
`status` (`missing`, `assumed`, `confirmed`, or `example`) and `provenance`.
Only confirmed facts can support a real gate. Decisions include the affected
stage numbers in `affects`.

Each numbered entry under `stages` may contain `artifacts`, `qualitative`, and
`approval`. Artifact records contain a project-relative `path` and `sha256`, a
cryptographic content fingerprint. Qualitative records are keyed by the package's
exact criterion and contain `status`, `reviewer`, `notes`, and `revision`.
Approval contains `status: approved`, `by`, `date`, `revision`, and `review_key`
(the review's `dependency_key` content fingerprint); only record
this after the client's explicit decision. Review operations never write approval.

The area schedule uses square metres, denoted `m2` in field names. Include room
areas and separate circulation, wall, structure and service allowances; avoid
overlap. `available_m2` is a supplied project allowance, not inferred permission.
A concept graph records rooms and connecting pairs, with an entrance identifier;
the privacy test finds whether private rooms can be reached without crossing
public entertaining space. This is a project-intent test, not a building code.

For final presentation, `render_binding` holds artifact records named `input` and
`render`, the measured model's `model_sha256`, and `revision`. `requirements`
contains each requirement's identifier, design `response` and evidence `artifact`.
File identity checks complement visual review; they cannot establish that a
renderer faithfully represented every design detail.
