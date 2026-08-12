# TASKPLAN Readback — PromptBoard — stale selector cursor

Zeitpunkt: 2026-08-12 12:05 Europe/Berlin
Rolle: TASKSOLVER
Tasks: 1136 / 1137

## Exact selector boundary

The selector delivered
`C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\LLM\REL-PUB_PromptBoard`.
FileCommander reports that this directory does not exist. The `LLM` parent is
also absent. No control document, release file, artifact, license inventory,
or Git state could be read at the exact selected path, and the path was not
replaced with a self-selected neighbor.

## Relocation and foreign-state evidence

FileCommander search resolves the current projection under
`C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\DATA\REL-PUB_PromptBoard`.
That checkout is `main...origin/main [behind 15]`, has active `cldflt.sys`,
and contains the foreign `.git/index-WORKSTATION-LG` and
`.git/FETCH_HEAD-WORKSTATION-LG` files. Its read-only baseline shows 230
files / 285,977,958 bytes and mass modifications, deletions, and untracked
assets/source/tests. No file there was changed, adopted, staged, or merged.

The current documents are not a safe completion basis even independently of
the stale path: `README.md`/`README_de.md` state 116/116, `STATE.md` states
119/119, `CHANGELOG.md` retains historical counts, and `RELEASES.md` retains
30/30 for the old v1.1.1 line. The release tree has duplicate checksum files;
the source ZIP has 41 entries including 24 bytecode entries; and the
untracked `THIRD_PARTY_LICENSES.txt` is not an owner-approved runtime
inventory. These are read-only findings, not corrections.

## Indirect local evidence (not substituted for the bundle)

The dedicated local clone
`C:\_Local_DEV\repos\REL-PUB_PromptBoard-tasksolver-1136-1137` is clean at
`main...origin/main [ahead 2]`. Its fresh isolated checks returned **116
passed** and `python -B tests/source_platform_smoke.py` returned
`source_platform_smoke: OK`. This evidence applies only to that local
snapshot; it does not certify the dirty OneDrive projection or authorize
document/artifact adoption. A prior release verifier also records the
MSIX/WACK and runtime-license gates as open.

## Disposition

Tasks 1136 and 1137 remain **open / blocked_foreign_state** for this
continuation. No task was marked done, and no OneDrive source, control
document, release artifact, checksum, license file, build, upload, merge,
rename, or push was performed. The stale selector path is skipped once after
this evidence and the selector is queried exactly once; the persistent
TASKSOLVER Goal remains active.
