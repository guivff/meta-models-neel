# Implementation readings before capture or readout acquisition

PROVISIONAL, pending coordinator ratification. 2026-10-28, CPU packaging only;
no new capture or reader outcomes opened. §198–§201 sources and owner freezes
control counts, read sites, arms, templates and candidate selection.

E91 uses the existing dev-only E3-style standardized logistic recipe, lambda.001,
LBFGS200, separately per polarity type and native layer; test labels never fit.
E92 extends that recipe to a three-class softmax linear probe, same dev-only
normalization and lambda.001/LBFGS200, fixed source order user/tool/assistant.
E92 accuracy and confusion matrices are descriptive; no binary gate is invented.

E85's fixed downstream question is appended to the existing user body before the
same thinking-disabled chat generation prefix. This preserves the registered
system cue, genre text and question while asking the model a user question rather
than inserting a question into an assistant answer. One greedy answer, max128
new tokens, on400 test items only. The new public behaviour prompts are sealed
before any GPU score. No additional chat turn, model answer or private factor
labels are added to the pod. BOW remains descriptive per417210fa.

Each new bank's capture is sealed before the CPU probe release. The public archive
has opaque IDs, public prompts, split/reader_allowed and source digests; feature
and arm placeholders used by the shared runner carry no hidden label information.
The CPU adapter joins original private row/factor/source labels only after capture.

E81/E90 uses exact-length batches up to64 to avoid recurrent-layer left padding.
Both128-token instruction arms and the32-token no-instruction arm retain the exact
owner-frozen prompt/token bytes. Batch size is an operational choice; no text,
item, decoding parameter or read point is changed.
