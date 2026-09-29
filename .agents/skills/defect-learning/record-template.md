# Defect record template (append to docs/LEARNINGS.md)

```
### <id: short-kebab-slug> — <one-line title in plain words>
- Observed: <what was wrong, measured; where (file/view/element); evidence path>
- Found by / stage: <client | lead review | critic | test | read-back> at <stage>;
  should have been caught at: <earliest stage that had the information>
- Reproduction: <test path::name, frozen real input>
- Direct cause: <the wrong value/shape/call>
- Escape: <why no existing check caught it>
- Contributing factors: <brief, trusted input, batch size, missing reference...>
- Class (general root): <stated without project nouns>
- Siblings: <other places the same root can occur; related past records>
- Control tier: 1 prevent-by-construction | 2 fail-closed check (stage) | 3 process step (why not scriptable)
- Control: <the construction change / check / step, file paths>
- Proofs: fires on real repro <test>; fires on sibling <test>; quiet on clean <test>;
  generalises <other option / mutation test>
- Registry: <registry id>
```
