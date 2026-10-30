# E114 frozen input transformation (§226)

Three E57 rows, every original test item: nesting_depth, indent_level and
page_range_digit,84 items each. Two arms per item,504 capture inputs total.
No dev items, resampling, new labels or probe fitting. Source BANK_SEAL and exact
items/annotations/definitions hashes are in MANIFEST.json. No reader/probe/judge
or J-lens files were opened to build this bank.

The only change is one frozen sentence prepended, then one newline, then the exact
original source text. SENTENCES.json fixes the wording. The stated arm names the
original state's value. The control names the opposite-variant frozen source
item's value with the SAME template/filler. For page ranges, use the actual
hundreds digit in the CURRENT citation and its paired opposite, preserving all
1–4 versus6–9 cases (not a3/7-only subset). The paired source IDs, actual numbers,
original state labels and annotations remain CPU-side. Both arms retain the
original E57 label/gold; the control's false statement does not relabel the source.
This implements "other value" by the frozen source pair, without authoring a new
pair or changing a rule, threshold, arm or item population.

Raw prefixes, no added chat wrapper. Whole-prefix pinned-Qwen tokenization;
capture at the original registered read token, now the final token of the new
prefix. All504 last token IDs equal the original final token IDs. No source
prefix crop, suffix, question or new continuation. The public record has ONLY
opaque id, prompt, input_ids and read_position; an explicit value sentence is the
registered manipulation, while added gold/targets/source keys/arm joins stay CPU.

I-2 binds the actual native Oracle44 runner and capped measured admission. One
greedy Oracle readout per transformed input; E57 judge unchanged, bankE114≤USD2.
No NLA arm is added. TotalGPU≤1080s, including setup/custody, under §217. W-text
never allocates pods or makes paid calls. W-mech2 owns the source-bound tested
once-only outcome adapter, committed before any affected output; I-2 watcher
executes it once, R-2 reviews on completed seal. The registered descriptive
reading compares S in the stated arm (≥.30) to E100's sealed transplant (≤.10);
W-text supplies inputs, not another analysis or an altered S definition.

Pre-freeze CPU authoring correction: E57 optional annotations do not have entries
for depth/indent. Original labels are complete in source items; optional lookup
returns an empty metadata object for those rows only, and still requires the
page-range pair annotation. Failed empty authoring directory/lock are retained
in ignored cache. Regression test added before freeze; no model/reader output,
cap spending, scientific restart or outcome analysis occurred.
