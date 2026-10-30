# E125 original-source custody supplement

This is evidence delivery for R-4 request83e408f3, not another E125 execution.
`ORIGINAL_GIT_OBJECT_PROOF.json` embeds13 original Git **commit/tree metadata**
objects, reconstructible from base64 with original type/length headers. No source
blob is embedded or exported. Every commit→directory tree→source path→blob SHA1
is checked by `verify.py`. Twelve bindings cover the original CODE_SEAL and all11
sealed source members. The thirteenth binds the executed Track Q wrapper.

`--external-bytes` reads the already-delivered local canonical sources and verifies
each original Git blob identity plus SHA256 without exporting those bytes. Without
that option, the verifier checks all metadata object identities and directory-path
bindings only. This is a real tree-path proof, not an asserted path/hash list.

Original source7d2a4df992282019889132e307aa3e895f42c3a6 was recovered from the
pre-existing sealed ORIGINAL_SOURCE.bundle into an isolated temporary Git object
store, using the shared repository only as a read-only prerequisite store. Its
recorded committer time is2026-10-29T14:43:29Z. The actual wrapper is original
32b12a400ee073fcbc1f913af5ca181397cf4bd9, recorded15:08:32Z. Both precede the
owner-sealed attempt creation15:10:02.212Z. These are original recorded Git times,
not an independent wall-clock attestation. Wrapper bytes match the existing sealed
reviewer copy SHA256bc6aac268e5da22ce69e52c7d4651312e1872c1557c85c464297f37dfb356dd8.
Separate offline-v2a20e39597 was not the executed source.

Run `python verify.py ORIGINAL_GIT_OBJECT_PROOF.json --external-bytes` from this
directory to verify13metadata objects/13bindings and the existing local bytes.
Three tampering checks reject modified object bytes, a wrong path, and a wrong
source SHA256. No model or diagnostic is executed.

Original report commitf37c27d351241e4f70f885d6ca06ef384bb15ed3 is unavailable here
or in the supplied source bundle. It is explicitly MISSING; W-lens is asked to
supply its original commit/tree proof. No replacement date is substituted.
R-4 retains independent custody disposition.

No source/worker blob, labels, generated answer text, arrays, infrastructure
assignment or raw output cache is published. No diagnostic recomputation, model,
probe, guard, alignment, shuffle, retry, judging, GPU operation or cost booking
occurred. E125 remains NOT RUN operational with its existing immutable receipts.
