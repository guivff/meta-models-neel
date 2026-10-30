# E67 custody repair — 2026-10-27

The original local E67 commit incorrectly tracked the pairing map, sample inventory and source binding. That commit was removed from the branch's reachable history before publication; deleting the paths in a follow-up commit was not used. No backup branch/tag was created pointing at it. E76 was already cleanly upstream and remains unchanged.

The three original files now physically reside only under git-ignored cache/g_agreement/understand/e67/wave1/integrator_wave1/, with byte-identical contents. The CPU-only archive identified in CUSTODY_LOCATION.20261027.json transfers them to the Integrator's ignored cache. Never stage that archive, map or source binding on a pod or pass it to the judge. The existing INTEGRATOR_SEAL.json remains public and unchanged; it contains hashes only.

All19 original public E67 files are byte-identical, including the packets, rubric, schema, original code, original handoff and every original seal. CUSTODY_LOCATION records their original SHA256 values. To preserve that frozen byte sequence, earlier custody-location wording in INTEGRATOR_HANDOFF.20261027.md is superseded by this note rather than edited.

For compatibility with the unchanged verifier, restore_private_custody67.py verifies the three cached private hashes against the original public integrator seal, then makes ignored, untracked CPU-only symlinks at the old local paths. No private file or symlink is in the Git tree. Copy/extract the private archive under cache/g_agreement/understand/e67/ first, then run:

```sh
python3 results/g_agreement/understand/e67/restore_private_custody67.py
```

The original public seals now verify without changing a hash, sample, donor, opaque ID, condition, prompt, readout or rubric. The scientific build and once-only guards are unchanged. Do not rerun the frozen packet builder. Judge delivery remains exactly the five files in judge_wave1/; a whole-folder archive that follows local custody links is forbidden.

.gitignore now excludes *.PRIVATE.json. The active versioned pre-commit hook at .githooks/pre-commit scans the actual staged blobs and rejects private filenames anywhere in the index, including case variants. It also rejects reachable private-file history, so a later deletion cannot conceal an earlier private commit. Credential-like values are blocked without echoing them; ordinary offline/cache identifiers are reported only as counts. Local hook configuration is core.hooksPath=.githooks. Install the same setting in another checkout to use it there.

Twelve tests pass, including private-filename rejection, staged credential rejection without value echo, ordinary public identifier acceptance, case variants and the later-deletion history regression. The required final audit is:

```sh
git log --all -- '*PRIVATE.json'
```

It must print nothing. The replacement commit ID is reported in the worker's final message and the ignored cache receipt cache/g_agreement/understand/e67/CUSTODY_REPAIR_COMMIT.json. The public-source and private-custody content hashes remain those accepted for wave1. E67 judgments/analysis were not run or changed during this repair.
