# I-4 reconstruction-head check — 28 October 2026

**Live checkpoint result: NOT RUN.** This workspace reports `torch.cuda.is_available() == False`; no current integrator pod assignment or GPU custody has been verified. A CPU stub pass is not evidence that the checkpoint heads run. The requested maximum is 1,800 GPU seconds, after E79/E80c priority work.

`SMOKE_REQUEST.json` binds one public item: the first item in E23's sealed input file, using its P32 text verbatim. The original file and seal hashes are recorded. Selection did not inspect labels, native reader outcomes or statistical results. Only opaque ID and public text are staged.

The command reuses the existing Oracle adapter in `projects/g_agreement/w_claims/ar.py`: official training source `a32590085a6070d75f950155d3c2b3db3eec97ef`, pinned whitener, registered AR checkpoint, layer44 output. It then releases that model and reuses `load_decoder_only` and `NLA.reconstruct`, loading NLA's native block42 backbone and trained value head. It does not load the NLA verbalizer or substitute a language-model head. The final norm and LM head are unused by this NLA path, as already reviewed for E27(c).

The integrator supplies a fully hashed asset manifest covering the registered base model, Oracle AR and NLA AR, plus the pinned official checkout and whitener. `SMOKE_REQUEST.json` contains the CLI and assignment schema. `SMOKE_EXACT_PREFLIGHT.json` names the exact source/public-item archive and hash. The fixed deadline starts before staging; an alarm enforces the cap. There are no downloads, automatic retries, scoring, judging or reader generation.

Success requires both real checkpoint calls to return finite tensors of shape `[1, 5120]`. Each phase writes its timing immediately. The output seal records the item, request, asset and custody hashes plus output fingerprints. It makes no fidelity or scientific claim. CPU tests exercise both stage paths and malformed-vector rejection; they do not validate GPU loading or checkpoint availability.

**Handoff:** I-4/Track Q integrator can run this smoke on assigned custody within the cap. Until the real output seal is returned, neither reconstructor is newly confirmed by this check. No GPU was launched, no GO issued, and no shared pod was claimed by W-mechanism.
