# TASKPLAN readback — PromptBoard — Bundles 1136/1137

Snapshot: 2026-08-12T03:17:43+02:00 (Europe/Berlin).

This continuation handled exactly the selector-delivered bundle 1136/1137.

## Selection, provenance, and write boundary

The selector supplied
`C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard`,
but that path does not exist. The current OneDrive Git projection is
`C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\DATA\REL-PUB_PromptBoard`,
which is also the path recorded by the `.SOFTWARE` registry. The task database
still carries the stale `LLM` selector path. The `.SOFTWARE` lock cache reports
zero active logical locks, and no project `LOCK*` file was found; this does not
authorize changes to the foreign checkout.

The resolved OneDrive checkout is foreign/dirty: 144 porcelain entries (121
tracked modified/deleted and 23 untracked), including 83 `flutter_port` paths,
23 test paths, 17 source paths, 9 documentation paths, 5 build paths, and
modified Store files. Its local `main` is
`5cd7be0de26a387b272d2849305de3e262a9bb92`; cached `origin/main` is the stale
`9bd7e51533dfc811e55e85b0615cd58994f1eefc`, while fresh
`git ls-remote` returns `be5bcd3bad93601b567a9155d6fa42bbb9b1e7e8`.
`git diff --check` already reports foreign trailing whitespace in
`STORE_LISTING.md` and a blank-at-EOF in `src/inline_variables.py`.
No OneDrive file was changed, adopted, merged, deleted, or marked done.

There is no PromptBoard entry in `.SYNC/workstation/repos.json`, so no
manifest-authorized Plan-D clone exists. The clean local tasksolver clone
`C:\_Local_DEV\repos\REL-PUB_PromptBoard-tasksolver-1136-1137` is an evidence
snapshot only; it is based on remote `main` `be5bcd3...` plus the local
tasksolver documentation commit `afd32c3`, and was not pushed.

## Task 1136 — test/version/release document drift

The current OneDrive documents disagree: `README.md` and `README_de.md` show
116/116, `STATE.md` still says 119/119 (updated 2026-08-01), `CHANGELOG.md`
retains historical 85/85 and older counts, and `RELEASES.md` still says the
historical v1.1.1 line had 30/30. `AUFGABEN.txt` records a 116/116 CI claim
for remote commit `be5bcd3`, but explicitly keeps TW-PROMPTBOARD-05 open
because the local worktree is not that commit and is foreign-dirty. The
published line is documented as v1.1.1, while `pyproject.toml` carries
unreleased development metadata 1.1.3. Store-P1 remains open: real WACK /
Partner-Center acceptance is not certified.

In the clean evidence snapshot, a fresh read-only
`python -B -m pytest -q -p no:cacheprovider` run returned **116 passed** and
`python -B tests/source_platform_smoke.py` returned **source_platform_smoke:
OK**. These results certify that snapshot only; they are not permission to
overwrite the OneDrive documents or to claim the dirty OneDrive checkout has
the same test state. The snapshot's documents explicitly preserve historical
counts and the v1.1.1/v1.1.3 distinction.

## Task 1137 — artifacts, hashes, and runtime licenses

The current OneDrive v1.1.1 files were hashed read-only:

- EXE: 47,107,559 bytes, SHA-256
  `70dc711f2eae7a3d25053a27ab6afa445be4f1786b6965b60e1cffef17226159`;
- source ZIP: 126,508 bytes, SHA-256
  `81273a6af1c2c0ed05189601ff3eac26aa6e5593e2c9800e92ca5c738db2d815`;
- root MSIX: 46,822,349 bytes, SHA-256
  `44c3481cb435c7ea9cb2f084d2b22e265e757dd4552088ac2778fd57e373c9ef`.

`SHA256SUMS.txt` matches the EXE and source ZIP. The parallel `SHA256SUMS`
contains only the divergent old EXE hash
`477c2f5c6dda2e31f5be060af3a4235d017b0bf69a824210f37dd6f03692e2e3` and
does not list the source ZIP or MSIX. The source ZIP has 41 entries, including
24 `__pycache__`/`.pyc` entries. `releases/v1.1.1/CHANGELOG.txt` still starts
with `[Unreleased] - 2026-06-17`. `THIRD_PARTY_LICENSES.txt` (dated 2026-07-02)
and its license test are untracked foreign files; no release-owner approval
establishes them as the final runtime inventory.

For comparison, the clean evidence snapshot contains a deterministic
105-member source ZIP with no bytecode/runtime-data entries and a single
canonical three-entry `SHA256SUMS.txt`. Its read-only
`python -B scripts/certify_release.py verify` passed; the explicit
`--require-msix` check exited 1 because `makeappx.exe` is unavailable. Thus
EXE/source/license evidence is locally reproducible, but MSIX/WACK and the
foreign OneDrive release set remain uncertified.

## Disposition

Tasks 1136 and 1137 remain open and assigned to `tasksolver-codex` with
`delegation_status=blocked_foreign_state`. The stale selector path, foreign
dirty OneDrive state, missing manifest-authorized Plan-D target, document
count drift, duplicate/stale hash evidence, bytecode in the foreign source
archive, and open Store-P1 gates prevent safe completion claims. Only this
local evidence document is written; no OneDrive source, control document,
artifact, license file, test, build, upload, commit, push, or mirror changed.

