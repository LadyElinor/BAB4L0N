# Repository lessons and provenance

These are **conceptual references, not direct integrations**. The implementation
is a new small standard-library prototype. It does not import, train on or execute
these repositories. References identify the research snapshots used in the design
handoff, not necessarily the latest upstream state.

## The Unfinished Commonwealth

Reference: `LadyElinor/unfinished-commonwealth` at
`ae5037b0dcf1e51a6f30614996ffcd0bbb01f584`.

- Source: [README](https://github.com/LadyElinor/unfinished-commonwealth/blob/ae5037b0dcf1e51a6f30614996ffcd0bbb01f584/README.md),
  especially the proposal-only participation profile, durable intent, and scoped
  lessons passed to successors without inherited execution permission.
- Applied here: bounded observations and proposals, preserved objections, explicit
  evidence references, immutable replay identity, and memory that confers no authority.
- Not imported: AP1/C2 transport, credentials, assembly, workshop succession or
  Commonwealth's learned-practice semantics.

## Adiona

Reference: `LadyElinor/Adiona` at
`4566a5baace34b0823154fa9fb31bdea4192ff52`.

- Source: [README](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/README.md),
  especially the distinctions between proposal, decision, execution permission,
  receipt and recovery, plus transactional state and receipt writes.
- Applied here: host-owned grants, separate proposal/effect/audit stages, atomic
  effect accounting, revocation and honest local-only assurance labels.
- Not imported: authenticated roles, capability/delegation machinery, full
  constitutional architecture or geometry/reasoning components. Licensing remains
  unresolved for reuse; this bundle includes no Adiona source code.

## CORTAC

Reference: `LadyElinor/CORTAC` at
`9eb2a148892690dfdb107aab373b6d7895421eb9`.

- Source: [evaluation README](https://github.com/LadyElinor/CORTAC/blob/9eb2a148892690dfdb107aab373b6d7895421eb9/evaluation/README.md),
  especially explicit exposed-fixture labels, equal comparison budgets, separate
  useful completion and refusal outcomes, and gates against unsupported claims.
- Applied here: clearly labeled exposed scoring examples, identical fresh
  before/after task budgets, fixed improvement scope, and an explicit claim ledger.
- Not imported: the proposed multi-arm study, society, bootstrap analysis or live
  scored runner. Babalon's small demo is not a replication of that research.

## Fidelis

The design handoff also named `Fidelis` at
`57c94ff78cecd0feb48dbb22e557842a82d22e0d` for licensing/authority-boundary lessons.
That exact source was not locally re-inspected in this finishing pass, so it is
recorded as a handoff reference, not independently verified implementation lineage.
No Fidelis source is included and no licensing permission is inferred.

## Verification scope

The three README references above were read directly from their local Git commit
objects during this finishing pass. Current upstream branch state was not checked.
Conceptual similarity does not establish code lineage, license compatibility or
interoperability. The byte manifest in the delivered archive covers Babalon's files,
not the upstream repositories.
