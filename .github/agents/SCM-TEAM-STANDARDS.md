# Team Operating Standards (All Agents)

## 1) Scope Discipline
- Work only on explicitly requested scope.
- Do not change unrelated modules.
- Prefer the smallest correct diff over broad rewrites.

## 2) Anchor-First Editing
- Use symbol/function/block-targeted edits (hashline/anchor style).
- Start from changed hunks and impacted symbols, not full-file rereads.
- Expand context only when necessary.

## 3) Debugger/Repro First (for bugs)
- Reproduce or trace failing paths before patching.
- Fix root cause, not symptoms.
- Check sibling paths for the same defect pattern.

## 4) Resource and Memory Safety
- Ensure cleanup/dispose/cancel/close patterns are correct.
- Prevent leaked listeners, timers, handles, tasks, and connections.
- No silent fallbacks that hide failures.

## 5) Type and Contract Safety
- Preserve API contracts unless explicitly changed.
- Avoid unsafe casts and brittle workarounds.
- Validate null, edge, and error paths explicitly.

## 6) Reuse Before Build
- Reuse existing helpers/patterns before adding abstractions.
- No unnecessary dependencies.
- Keep architecture boundaries intact.

## 7) Verification Standard
- Run relevant existing checks first; broaden only if risk requires.
- Confirm behavior on impacted surfaces.
- Report outcome clearly and concisely.

## 8) Review Quality Bar
- High-signal findings only: correctness, security, reliability, performance.
- Ignore style-only noise unless it affects correctness or maintainability.
- Prioritize by severity and user impact.

## 9) Release Safety
- Build/test gates must pass before release.
- Health checks and smoke checks are required.
- Rollback path must be explicit and fast.

## 10) Token and Speed Optimization
- Diff-first investigation.
- Symbol-first navigation.
- Parallelize independent checks where safe.
- Use concise structured outputs.
- Stop exploration once enough evidence is gathered.

## Required Output Template (all agents)
- Objective
- Actions taken
- Result
- Risks/follow-ups (if any)

