"""Build the updated Activation Readers doc (v11) and the changes doc from v10. Run from the repo root:
    .venv/bin/python results/g_agreement/report/build_v11.py "/Users/guivff/Downloads/Activation_Readers (10).docx"
"""
import copy
import sys
from pathlib import Path

import docx
from docx.shared import Emu, Pt

SRC = Path(sys.argv[1])
OUT = Path("results/g_agreement/report")
F2 = Path("results/g_agreement/f2")
d = docx.Document(SRC)
P = list(d.paragraphs)
changes = []  # (section, before, after)


def set_text(p, text, section):
    before = p.text
    runs = p.runs
    if runs:
        runs[0].text = text
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run(text)
    changes.append((section, before, text))


def insert_after(p, text, section, like=None):
    """New paragraph after p with like's paragraph properties (and first-run formatting)."""
    like = like or p
    new = copy.deepcopy(like._p)
    for r in new.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r"):
        new.remove(r)
    p._p.addnext(new)
    np_ = docx.text.paragraph.Paragraph(new, p._parent)
    run = np_.add_run(text)
    if like.runs:
        src = like.runs[0]
        run.bold, run.italic = src.bold, src.italic
        if src.font.size:
            run.font.size = src.font.size
        if src.font.name:
            run.font.name = src.font.name
    changes.append((section, "", text))
    return np_


def insert_picture_after(p, img, caption, section, caption_like):
    pic_p = insert_after(p, "", section, like=P[11])
    changes.pop()
    pic_p.runs[0].add_picture(str(img), width=Emu(5943600))
    cap = insert_after(pic_p, caption, section, like=caption_like)
    return cap


# ---------------- TLDR
set_text(P[4], "Readers report what is linearly present in the vector, not how much the model relies on it. Scaled to the same "
         "size, the part of an edit inside the J-space moves the model's answer about 6× less than the rest, yet readers follow "
         "both about equally (78–91%). They mostly miss the direction a trained probe relies on.", "TLDR")
set_text(P[6], "Where and how you read changes the answer. At layer 42 no reader names who holds what in free text, but at "
         "layer 56 the Oracle does 86% of the time; prefilling an answer doesn't help, and a prefill that names a candidate "
         "just gets copied. Two-candidate log-odds oversell the readers, and the model's upcoming wrong answer only shows up "
         "in the J-lens and Oracle from layer 52, four layers after a probe.", "TLDR")
# ---------------- Setup
set_text(P[8], P[8].text.replace(
    "Scored from free text, no reader named who holds what, and a prompt-only baseline got all 32 states. That blind spot was a scoring artefact:",
    "Scored from free text at layer 42, no reader named who holds what, and a prompt-only baseline got all 32 states. That blind spot was a scoring and layer artefact:").replace(
    "(two candidates flatter them; see Misc).",
    "(two candidates flatter them; see Misc), and read at layer 56 the Oracle names it in free text (section 3). The Oracle Lens "
    "was trained on every fourth layer from 20 to 60, so 42 is off its grid; rerunning the main comparisons at 44 changed no "
    "conclusion (Misc)."), "Setup")
# ---------------- Section 1
insert_after(P[13], "In free text the picture is different: on the 32 pilot states no two readers ever named the same wrong answer. "
             "They fail together by naming neither candidate.", "1. Majority")
# ---------------- Section 2
set_text(P[19], "We then split the edit into pieces (64 states per cell). On ownership, the top-384 J-space component and the "
         "remainder outside J-space each flip the model's answer 0% of the time, yet readers move towards them 80–94% and 67–88% "
         "of the time. That could just mean the readers are more sensitive than the model, so we rescaled each piece to the full "
         "edit's size at every position. The J-space piece still flips 0 of 64 answers at full strength and half of them only at "
         "twice that, while the rest flips all 64; the model's answer log-odds move 6× less for the J-space piece (+3.9 vs +24.8 "
         "nats). Readers follow both pieces about equally, 78–91% already at a quarter of the strength. The direction a trained "
         "probe uses, which the probe follows 96% of the time, barely moves the model (0–5%) and leaves the readers inside the "
         "random band (45–56%); on the Oracle's own training layer it does partly follow it (66%).", "2. In the vector")
cap2 = insert_picture_after(P[19], F2 / "t2/fig_t2.png",
                            "Same-size pieces of the ownership edit. Left: the model flips with the non-J piece (orange) as with the full edit, "
                            "and with the J-space piece (blue) only at twice the dose. Right: readers follow every piece about equally from the "
                            "lowest dose; random directions stay near 50%.", "2. In the vector", P[18])
set_text(P[20], "Our reading: the model under-weights directions that the readers weight fully, so a reader's score tells you "
         "what is linearly present, not how much the model relies on it. Part of the gap is sensitivity: on this edit the readers "
         "respond at a dose at least 8× smaller than the one that flips the model. One honest hedge: readers moving smoothly with "
         "the dose is partly expected by construction, since any roughly linear score will do that.", "2. In the vector")
# ---------------- Section 3
set_text(P[21], "3. At layer 42 readers miss things they catch a few layers later", "3. Layers")
p_a = insert_after(P[25], "The same holds for the bindings that started the project. With the plain chat template, the Oracle names "
                   "who holds the object or where the arrows end in free text 86% of the time at layer 56, against 12% at layer 44, "
                   "and gets both versions of each pair right; the J-lens names them at layers 56–60 (25–62%) and never below 52. "
                   "Prefilling an answer stem (\"The person who carries the lantern is\") does not help at any layer, and a stem "
                   "that names a candidate (\"The answer, in Italian, is\") is simply copied: readers name the stem's word 59–95% "
                   "of the time even when it is wrong.", "3. Layers")
insert_after(p_a, "Some facts stay hidden even so. Mapping every prompt position at layers 36–60, we found 60 cells where a trained "
             "probe reads the answer (80% or more) while the J-lens and Oracle sit at chance, all on template and instruction "
             "tokens just before the answer (such as \"<think>\" and \"Reply\"); by the last token the readers catch up. We haven't "
             "yet tested whether the model uses those positions. On the puzzles the model gets wrong, the Oracle doesn't look more "
             "confused than on ones it gets right (1.35 vs 1.29 candidate answers per readout); from layer 52 it reports the "
             "model's wrong choice rather than weighing options.", "3. Layers")
# ---------------- Misc
m1 = insert_after(P[35], "Suraj's newline feature (characters since the last newline) stays unreadable at new read sites. With "
                  "\"<|im_end|>\" appended, a counting instruction, or both, no reader separates long-line from short-line reads "
                  "(48–65%), while a probe does (85–97%). With the counting instruction the Oracle talks about line length, but "
                  "equally for long and short lines.", "Misc")
m2 = insert_after(m1, "The NLA's own reconstructor recovers 50–70% of the variance at the last token but goes negative on template "
                  "tokens, and it doesn't tell the NLA's right readouts from wrong ones within a family.", "Misc")
insert_after(m2, "The Oracle Lens is trained on every fourth layer and 42 isn't one of them. Rerunning the main comparisons at 44 "
             "changed no conclusion; it raised two ownership cells (class-mean direction 77% → 92%, probe direction 52% → 66%).", "Misc")
# ---------------- Next, caveats, questions
set_text(P[37], "First, test whether the template positions where a probe reads what the readers miss are used by the model, by "
         "editing only there. Second, redo the main free-text comparisons at layer 56, where the readers report bindings, and "
         "re-score every earlier two-way test with the full candidate set. Third, replicate the two system-turn effects, then use "
         "a preamble that contradicts world knowledge to separate \"reads the context\" from \"reads the model's belief\". SAEs are "
         "still not in the comparison.", "Next")
set_text(P[38], "Caveats: the prompts are synthetic with rule-based keys, and there is one model. Reads are at the last token "
         "unless stated, each steering cell has 64 states, claim precision rests on 32 + 8 states, the prefill and stem results "
         "rest on 16 pairs, and the stem test was scored by rules after our judge credits ran out (rules and judge agreed on 92% "
         "of readouts in the first prefill test).", "Next")
set_text(P[40], "Should a reader be judged at its training site, or wherever the fact is load-bearing? At layer 56 the Oracle "
         "reports bindings it misses at 42.", "Questions")
set_text(P[41], "Is \"follows a direction the model under-weights\" a reader failure, or a correct report of a vector the model "
         "relies on less?", "Questions")
for p in d.paragraphs:  # keep the date line, if any, current
    pass
OUT.mkdir(parents=True, exist_ok=True)
out_main = OUT / "Activation_Readers_v11.docx"
d.save(out_main)

# ---------------- changes doc
c = docx.Document()
st = c.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10.5)
c.add_heading("Activation readers: what changed since v10", level=0)
c.add_paragraph("Guiv Farmanfarmaian, Suraj Prasad · 2026-10-15 · Qwen3.6-27B. Every experiment below was pre-registered before "
                "it ran (BRIEF_Z.md and PREREG_WV.md in the repo). Follow-ups 2 and 3 used 2.9 GPU-hours on one H100.")
EXPS = [
    ("Oracle Lens on its training grid (O44)",
     "Is anything in v10 an artefact of reading the Oracle Lens at layer 42, which is off the grid it was trained on (every fourth layer)?",
     "Re-read the same states at layer 44: the 140 natural pairs and the 2,688 steering edits.",
     "No conclusion changes. The Oracle still follows the J-space and remainder pieces that never flip the model (91% and 94%). Two "
     "ownership cells rise: the class-mean direction (77% → 92%) and the probe direction (52% → 66%, above the 47% random band).",
     "Setup and Misc mention the rerun; section 2 notes the Oracle partly follows the probe direction on its grid."),
    ("Answer prefill vs chat template (F2-1)",
     "Agam: are the free-text misses an artefact of reading at the wrong position or format?",
     "32 pilot states in three formats: chat template; chat template plus an assistant-turn answer stem that names no "
     "candidate (\"The person who carries the lantern is\"); plain text plus the same stem. Read at the last three tokens, "
     "layers 42 and 44, 4 samples per reader.",
     "The stem does not help; it lowers free-text hits (Oracle at 44: 50% → 38% → 17%). Bindings stay at 0–9% free-text hits in "
     "every format while their log-odds wins stay at 81–100%. A later check found the J-lens names the bindings at layers 56–60 "
     "in every format, which led to F2-5.",
     "Section 3 and TLDR: prefill doesn't help."),
    ("Same-size split edit (F2-2)",
     "Agam: could \"readers follow edits the model ignores\" just mean readers are more sensitive?",
     "64 ownership states. The J-space piece of the edit, the rest, and a random direction were each rescaled to the full "
     "edit's size at every position; doses 0.25–2.",
     "Partly yes. The J-space piece flips 0 of 64 answers at full strength and 52% at twice it; the rest flips all 64. The "
     "model's answer log-odds move 6× less for the J-space piece (+3.9 vs +24.8 nats), while readers follow both 78–91% from "
     "the lowest dose. So the model under-weights that piece about 6×, and readers respond at a dose at least 8× smaller.",
     "Section 2 rewritten: \"follows edits the model ignores\" becomes \"the model under-weights what readers weight fully\". New figure."),
    ("Probe vs readers at every position (F2-3)",
     "Agam: is there a concept a probe finds at some positions that the readers don't show?",
     "140 pairs in four families, every prompt position, layers 36–60 step 4. Held-out probe vs J-lens and Oracle log-odds.",
     "60 cells where the probe reads the answer at 80% or more while both readers are at chance: 45 in ownership, 15 in tense, "
     "all on template and instruction tokens before the answer. By the last token the readers catch up. Caveats: the probe is "
     "trained on a two-way label and the readers are zero-shot; the NLA is absent; one analysis rule was set after a first look.",
     "Section 3: new paragraph; Next: test whether the model uses those positions."),
    ("Diagnostics: NLA reconstruction, Oracle confidence, Oracle confusion (F2-4)",
     "Agam: does FVE flag the readers' mistakes? Is the model visibly weighing options in the Oracle's readouts?",
     "The NLA's own reconstructor on 1,192 NLA readouts; the Oracle's log-prob of its own asserted answer; Oracle readouts on "
     "297 puzzle errors and 103 controls at layers 44–56.",
     "FVE is 0.5–0.7 at the last token and negative on template tokens; within a family it does not separate right from wrong "
     "readouts (only 18 wrong). The Oracle's confidence doesn't predict correctness (AUROC 0.40). The Oracle lists about as many "
     "answers on errors as on correct items (1.35 vs 1.29); from layer 52 it names the model's wrong answer.",
     "Misc: FVE line; section 3: confusion sentence."),
    ("Agam's exact stems with a copy control (F2-5)",
     "Agam: try prefills like \"The answer, in Spanish, is\".",
     "His stems with the right candidate and with the wrong one, chat and plain formats; \"The answer is\" for ownership and "
     "mapping. Oracle at layers 44 and 56, NLA at 42, J-lens at every even layer.",
     "Readers copy the stem: with the wrong candidate in it they name that candidate 59–95% of the time and the right one at most "
     "5%. \"The answer is\" lowers hits. With the plain chat template and no stem, the Oracle names the ownership or mapping answer "
     "in free text 86% [67, 98] of the time at layer 56, against 12% at 44, right for both versions of each pair. Scored by "
     "rules because the judge credits ran out.",
     "TLDR, Setup and section 3: the free-text blind spot on bindings is a layer-42 effect."),
    ("Newline feature at new read sites (F2-6)",
     "Agam: does inserting <|im_end|> or a counting instruction make the newline feature readable?",
     "60 hard-wrapped wikitext passages, a read near the end of a long line and one near the start, four read sites (raw, "
     "<|im_end|>, counting instruction, both), Suraj's fixed reader templates plus a placebo.",
     "No reader tracks it at any site (48–65%), while a probe does (85–97%). With the instruction plus <|im_end|> the Oracle "
     "mentions line length in half its readouts, equally for long and short lines.",
     "Misc: new line."),
]
for title, q, ran, found, effect in EXPS:
    c.add_heading(title, level=2)
    for lab, txt in (("Question. ", q), ("What we ran. ", ran), ("Finding. ", found), ("Change in the document. ", effect)):
        para = c.add_paragraph()
        r = para.add_run(lab); r.bold = True
        para.add_run(txt)
c.add_heading("Corrections made after an independent review", level=2)
for t in ("The first summary said the J-space piece needs \"about four times\" the dose; the readers already respond at a quarter of "
          "the dose and the model needs twice the full dose, so the gap is at least 8×.",
          "The first FVE summary averaged over positions and reported \"FVE about zero\"; by position it is 0.5–0.7 at the last "
          "token and negative on template tokens.",
          "The 60 probe-only cells are described as a first pass, since the probe is trained and the readers are zero-shot."):
    c.add_paragraph(t, style="List Bullet")
c.add_heading("Text changes in the main document", level=2)
tbl = c.add_table(rows=1, cols=3)
tbl.style = "Light Grid Accent 1"
h = tbl.rows[0].cells
h[0].text, h[1].text, h[2].text = "Section", "v10", "v11"
for sec, before, after in changes:
    if not after.strip():
        continue
    row = tbl.add_row().cells
    row[0].text, row[1].text, row[2].text = sec, before or "(new paragraph)", after
c.add_heading("Figures", level=2)
for img, cap in ((F2 / "t1/fig_t1.png", "F2-1: answer prefill vs chat template (32 pilot states)."),
                 (F2 / "t2/fig_t2.png", "F2-2: same-size pieces of the ownership edit."),
                 (F2 / "t3/fig_t3.png", "F2-3: probe vs readers at every position and layer; black squares are probe-only cells."),
                 (F2 / "t6/fig_t6.png", "F2-6: the newline feature at four read sites.")):
    c.add_picture(str(img), width=Emu(5943600))
    cp = c.add_paragraph(cap); cp.runs[0].italic = True
out_diff = OUT / "Activation_Readers_changes_since_v10.docx"
c.save(out_diff)
print(out_main, out_diff, len(changes), "changes")
