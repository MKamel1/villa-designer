"""Concept design by search and critique (ADR-0016).

`critic` scores a concept the same way whatever produced it: a room graph
(published precedents, the pilot concepts) or a generated layout. `generator`
lays out a programme per parti on a plot and hands every variant to the critic.
The critic is calibrated in tests/test_concept_calibration.py; geometric checks
have no published dimensioned precedents yet, so generated concepts are
diagnostic until that calibration can run.
"""
