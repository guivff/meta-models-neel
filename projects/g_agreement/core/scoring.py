"""Deterministic claim extraction for the G-experiments (INTERFACES.md §6) + blinded sheet.

Rule set `rule-v1`. The prose version of every rule, with examples and the known limits, is
`projects/g_agreement/dataset/rubric.md`; that file is authoritative. Constants that encode a
judgment call are collected at the top so the coordinator can flip them before freezing.

Public API
    extract_claims(text, item, method) -> claim dict (primary / entities / objects / relation / truncated)
    claim_from_gen(gen, item)          -> full §6 row (adds gen_id, method, item_id, extractor, blind)
    make_blind_sheet(gens, seed)       -> [{gen_id, method, text}] shuffled; no item_id, no answer key
    score_claims(claims, items, targets) -> per-gen rows with factual_correct and target_consistent SEPARATE
    detect_tense(text)                 -> ("past"|"future"|"mixed"|None, evidence)
    detect_language(text, candidates)  -> (language|None, evidence)
    extract_target_answer(text, item)  -> (value|None, evidence)
No LLM is used anywhere in this module.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

EXTRACTOR_ID = "rule-v1"

# ---- judgment-call switches (see rubric.md "Judgment calls") --------------------------------
MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY = False  # coordinator 2026-10-07: only start->dest or an answer pattern asserts the result
TENSE_USE_WEAK_LAYER = True                     # verb-form heuristics when no explicit marker present
JLENS_PREFIX_MIN = 4                            # a top-10 token >= 4 chars that is a prefix of a candidate counts
JLENS_TOP_K = 10
LANGUAGE_WRITTEN_IN_MIN_HITS_IF_NAME_NEGATED = 2  # J1 (coordinator 2026-10-07)
STATUSES = ("supports", "contradicts", "unclear", "self_contradictory")

# =============================================================================================
# Language resources (8 languages used by the dataset). Words are lower-case; English words and
# words that are also common English tokens were deliberately excluded (see rubric.md).
# =============================================================================================
LANGUAGE_WORDS: Dict[str, set] = {
    "French": set("""le la les un une des du est sont et ou mais dans sur avec pas ne ce cette ces il
        elle ils elles nous vous je tu que qui oui très bien aussi comme être avoir bleu bleue froid
        froide blanc blanche chat quatre vert verte nuit jaune miel mardi ciel couleur réponse bonjour
        merci""".split()),
    "German": set("""der das ein eine einen ist sind und oder aber nicht für auf aus bei nach von zu ich
        du sie es wir ihr ja nein sehr auch wie wird werden haben sein blau kalt vier grün weiß weiss
        katze dienstag nacht gelb honig himmel farbe antwort danke hallo""".split()),
    "Spanish": set("""el la los las un una unos unas es está están pero en para por sí muy también como
        qué que cómo cuál tú él ella nosotros ellos ser estar tiene tienen azul frío fría frio cuatro
        verde blanco blanca gato martes noche amarillo miel cielo respuesta hola gracias""".split()),
    "Italian": set("""il la gli le un uno una è sono di da del della sì molto anche che tu lui lei noi loro
        essere avere hanno blu azzurro freddo fredda quattro verde bianco bianca gatto martedì notte giallo
        miele cielo colore risposta ciao grazie""".split()),
    "Portuguese": set("""uma uns umas é são ou mas para por não muito também como que quem tu ele ela nós
        eles elas ser estar tem têm azul frio fria quatro verde branco branca gato terça noite amarelo
        céu resposta olá obrigado obrigada""".split()),
    "Dutch": set("""de het een en maar niet voor aan bij naar uit ik jij je hij zij ze wij zijn hebben
        heeft ja nee ook zeer blauw koud vier groen kat dinsdag nacht geel gele honing lucht kleur antwoord
        hallo""".split()),
    "Swedish": set("""en ett det de och eller inte för på från jag du är har kan ska mycket också hur vad
        blå blått kall kallt fyra grön grönt vit vitt katt tisdag natt gul gult gula honung himmel färg
        svar hej""".split()),
    "Turkish": set("""bir ve ile bu şu için değil evet hayır çok ne nasıl siz onlar yok mavi soğuk dört
        yeşil beyaz kedi salı gece sarı bal gökyüzü renk cevap merhaba teşekkürler teşekkür""".split()),
}
# Forms that NAME a language (English name, own name, adjective/country forms). Used for
# text mentions (word-boundary, case-insensitive) and for J-lens tokens (folded).
LANGUAGE_NAME_FORMS: Dict[str, List[str]] = {
    "French": ["french", "français", "francais", "française", "francaise", "france", "法语", "法文"],
    "German": ["german", "deutsch", "deutsche", "deutschen", "germany", "deutschland", "德语", "德文"],
    "Spanish": ["spanish", "español", "espanol", "española", "castellano", "spain", "españa", "西班牙语", "西班牙文"],
    "Italian": ["italian", "italiano", "italiana", "italy", "italia", "意大利语", "意大利文"],
    "Portuguese": ["portuguese", "português", "portugues", "portuguesa", "portugal", "葡萄牙语", "葡萄牙文"],
    "Dutch": ["dutch", "nederlands", "netherlands", "holland", "hollands", "荷兰语", "荷兰文"],
    "Swedish": ["swedish", "svenska", "svensk", "sweden", "sverige", "瑞典语", "瑞典文"],
    "Turkish": ["turkish", "türkçe", "turkce", "turkish", "turkey", "türkiye", "turkiye", "土耳其语", "土耳其文"],
}

# =============================================================================================
# Tense resources
# =============================================================================================
TENSE_STRONG = {
    "past": [r"\bpast\b", r"\byesterday\b", r"\bhappened\b", r"\bpreviously\b", r"\bearlier\b",
             r"\bago\b", r"\blast (?:night|week|month|year|time)\b", r"\bpreterite\b", r"\balready\b"],
    "future": [r"\bfuture\b", r"\btomorrow\b", r"\bupcoming\b", r"\bnext (?:week|day|month|year|time|morning)\b",
               r"\bwill happen\b", r"\bplans? to\b", r"\bintends? to\b", r"\babout to\b"],
}
IRREGULAR_PAST = set("""went was were had did saw ate made took came got ran built bought brought wrote spent
    found swam sang flew drove rode sat stood slept drank fed met left kept felt held told sold thought
    taught caught fought won began drew grew knew threw blew wore tore broke spoke woke chose rose froze
    gave forgave hung rang swung became bent sent lent lay laid paid said heard fell led lost
    understood forgot hid bit rode shook spun stole struck swept wound""".split())
# Regular -ed words that are not past-tense verbs, or are meta-verbs describing the prompt rather
# than the event ("the user asked for ...") — excluded from the WEAK layer only.
ED_STOPLIST = set("""red bed need seed feed speed bleed shed wed sled fled led ned zed med reed greed deed
    weed breed indeed naked wicked sacred hundred kindred hatred rugged ragged jagged wretched crooked
    beloved aged shred embed proceed exceed succeed agreed freed""".split())
META_PAST = set("""asked requested instructed prompted told wanted said mentioned used described specified
    provided given based related focused called named listed needed required expected formatted phrased
    worded written stated intended designed shown displayed included contained involved implied suggested
    indicated referred noted framed posed added highlighted encoded represented activated triggered
    supposed meant
    structured formatted labeled labelled capitalized capitalised bolded bulleted numbered indented quoted
    bracketed italicized italicised established signaled signalled defined constrained closed opened followed
    preceded separated enclosed nested titled delimited punctuated demanded dictated marked tagged aligned
    templated embedded repeated positioned placed introduced completed terminated truncated unanswered
    answered filled rendered generated predicted anticipated requested""".split())
# "will <meta verb>" talks about the model/answer, not the event -> not counted in the weak layer
META_WILL = r"(?:be|likely|probably|respond|answer|reply|say|write|output|generate|produce|give|provide|need|have|use|mention|include|contain|describe|focus|follow|start|begin|end|continue|return|choose|pick|select|state|list|try|attempt)\b"
FUTURE_RE = re.compile(r"\b(?:will|won't|wont|shall|gonna)\b|\w'll\b|\w’ll\b|\bgoing to\b|\bnext (?:week|day|month|year|time|morning)\b|\b(?:is|are|was|were) about to\b", re.I)
PAST_EXPLICIT_RE = re.compile(r"\b(?:yesterday|ago|last (?:night|week|month|year|time))\b", re.I)
PAST_AUX_RE = re.compile(r"\b(?:was|were|did|didn't|didn’t|wasn't|wasn’t|weren't|weren’t|had|hadn't|hadn’t)\b", re.I)
ED_RE = re.compile(r"\b([a-z]{2,}ed)\b", re.I)
WORD_RE = re.compile(r"\w+", re.U)

NEGATION_RE = re.compile(
    r"(?:\bnot\b|\bno\b|\bnever\b|\bneither\b|\bnor\b|\bisn'?t\b|\bwasn'?t\b|\baren'?t\b|\brather than\b|"
    r"\binstead of\b|\bwithout\b|\bunlike\b|\bexcept\b)\s*"
    r"(?:(?!(?:but|yet|however|rather|instead|only)\b)\w+\s+){0,2}"   # up to 2 intervening words, never across a contrast word
    r"(?:in|a|an|the|by|to|being|using|into|of|about)?\s*$", re.I)

POSSESSION_CUE_RE = re.compile(
    r"\b(?:has|have|had|holds?|holding|held|owns?|owned|owning|keeps?|kept|keeping|carries|carry|carrying|carried|"
    r"possess(?:es)?|belongs?|belonging|with|gets?|got|given|takes?|took)\b|['’]s\b", re.I)
ARROW = r"(?:→|->|=>|⇒|➜|maps? to|leads? to|becomes?|goes? to|points? to|gives?|then|transforms? (?:in)?to|is mapped to)"
ARROW_RE = re.compile(ARROW, re.I)
REACH = r"(?:reach(?:es|ed)?|end(?:s|ed)? (?:up )?(?:at|in|on|with)|land(?:s|ed)? (?:on|at)|arrive(?:s|d)? at|get(?:s)? to|result(?:s)? in|yield(?:s)?|is|equals|gives?|leads? to|→|->|=>)"
HEDGE_RE_T = r"\b(?:either\s+)?(?:{a})\b\s*(?:,|/)?\s*(?:or|versus|vs\.?)\s+(?:the\s+)?\b(?:{b})\b"


# =============================================================================================
# Small helpers
# =============================================================================================
def fold(tok: str) -> str:
    """Lower-case, strip tokenizer space markers/punctuation, remove diacritics (NFKD)."""
    # strip tokenizer markers BEFORE NFKD (NFKD would split 'Ġ' into 'G' + combining dot)
    t = str(tok).replace("Ġ", " ").replace("▁", " ").replace("Ċ", " ")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).strip().lower()
    return "".join(ch for ch in t if ch.isalnum())


def _negated(text: str, start: int) -> bool:
    return bool(NEGATION_RE.search(text[max(0, start - 30):start]))


def _alt(forms: Sequence[str]) -> str:
    return "|".join(re.escape(f) for f in sorted(set(forms), key=len, reverse=True))


def _is_single_letter(s: str) -> bool:
    return len(s) == 1 and s.isalpha()


def _symbol_regex(sym: str) -> re.Pattern:
    """Single-letter symbols match case-sensitively (so the article 'a' is not symbol 'A')."""
    if _is_single_letter(sym):
        return re.compile(r"(?<![A-Za-z])" + re.escape(sym) + r"(?![A-Za-z])")
    return re.compile(r"\b" + re.escape(sym) + r"\b", re.I)


def _mentions(text: str, forms: Sequence[str], case_sensitive_single: bool = True) -> List[Tuple[int, int, bool]]:
    """All (start, end, negated) occurrences of any form (word-boundary)."""
    out = []
    for f in forms:
        pat = _symbol_regex(f) if case_sensitive_single and _is_single_letter(f) else re.compile(r"\b" + re.escape(f) + r"\b", re.I)
        for m in pat.finditer(text):
            out.append((m.start(), m.end(), _negated(text, m.start())))
    return sorted(set(out))


def _hedge_spans(text: str, forms_a: Sequence[str], forms_b: Sequence[str]) -> List[Tuple[int, int]]:
    spans = []
    for a, b in ((forms_a, forms_b), (forms_b, forms_a)):
        pat = re.compile(HEDGE_RE_T.format(a=_alt(a), b=_alt(b)), re.I)
        spans += [(m.start(), m.end()) for m in pat.finditer(text)]
    return spans


def _in_spans(pos: int, spans: Sequence[Tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def _span(text: str, s: int, e: int, pad: int = 40) -> str:
    return text[max(0, s - pad):min(len(text), e + pad)].replace("\n", " ").strip()


def _status(asserted: Dict[str, Any], answer: str, other: str) -> Tuple[str, Optional[str]]:
    a, b = bool(asserted.get(answer)), bool(asserted.get(other))
    if a and b:
        return "self_contradictory", None
    if a:
        return "supports", answer
    if b:
        return "contradicts", other
    return "unclear", None


def _clauses(text: str) -> List[str]:
    parts = re.split(r"[.;:!?\n]+|(?:^|\n)\s*[-*•]\s+|,?\s+(?:and|while|whereas|but|although)\s+", text)
    return [p.strip() for p in parts if p and p.strip()]


# =============================================================================================
# Detectors
# =============================================================================================
def detect_language(text: str, candidates: Sequence[str]) -> Tuple[Optional[str], Dict[str, List[str]]]:
    """Which of the two candidate languages is `text` written in? Wordlist vote using only words
    that belong to exactly one of the two candidates' lists. Returns (label|None, {lang: hits})."""
    words = [w.lower() for w in WORD_RE.findall(text)]
    lists = {c: LANGUAGE_WORDS.get(c, set()) for c in candidates}
    hits: Dict[str, List[str]] = {}
    for c in candidates:
        others = set().union(*(lists[o] for o in candidates if o != c))
        distinct = lists[c] - others
        hits[c] = sorted({w for w in words if w in distinct})
    scored = sorted(candidates, key=lambda c: -len(hits[c]))
    if len(candidates) >= 2 and len(hits[scored[0]]) > 0 and len(hits[scored[0]]) > len(hits[scored[1]]):
        return scored[0], hits
    if len(candidates) == 1 and hits[scored[0]]:
        return scored[0], hits
    return None, hits


def _past_verbs(text: str, exclude_meta: bool) -> List[str]:
    found = []
    for m in ED_RE.finditer(text):
        w = m.group(1).lower()
        if w in ED_STOPLIST or (exclude_meta and w in META_PAST):
            continue
        found.append(w)
    for w in WORD_RE.findall(text):
        if w.lower() in IRREGULAR_PAST:
            found.append(w.lower())
    for m in PAST_AUX_RE.finditer(text):
        found.append(m.group(0).lower())
    return found


def detect_tense(text: str) -> Tuple[Optional[str], Dict[str, List[str]]]:
    """Past/future detector for the TARGET's own sentence (not for readouts).
    future if any future marker and no past marker; past if the reverse; 'mixed' if both; None if neither."""
    fut = [m.group(0) for m in FUTURE_RE.finditer(text)]
    past = [m.group(0) for m in PAST_EXPLICIT_RE.finditer(text)] + _past_verbs(text, exclude_meta=False)
    ev = {"past": past, "future": fut}
    if fut and not past:
        return "future", ev
    if past and not fut:
        return "past", ev
    if past and fut:
        return "mixed", ev
    return None, ev


def tense_readout_markers(text: str) -> Dict[str, List[str]]:
    """Strong (explicit) and weak (verb-form) markers in a READOUT about the tense item."""
    out = {"strong_past": [], "strong_future": [], "weak_past": [], "weak_future": []}
    for lab in ("past", "future"):
        for pat in TENSE_STRONG[lab]:
            for m in re.finditer(pat, text, re.I):
                if not _negated(text, m.start()):
                    out[f"strong_{lab}"].append(m.group(0))
    out["weak_past"] = _past_verbs(text, exclude_meta=True)
    for m in FUTURE_RE.finditer(text):
        tok = m.group(0)
        if tok.lower() == "will" and re.match(r"\s+" + META_WILL, text[m.end():m.end() + 20], re.I):
            continue
        out["weak_future"].append(tok)
    return out


# =============================================================================================
# Family extractors (text readouts)
# =============================================================================================
def _answer_patterns(text: str, cand: str) -> List[Tuple[int, int]]:
    c = re.escape(cand)
    boundary_l = r"(?<![A-Za-z])" if _is_single_letter(cand) else r"\b"
    boundary_r = r"(?![A-Za-z])" if _is_single_letter(cand) else r"\b"
    flags = 0 if _is_single_letter(cand) else re.I
    pats = [
        r"\b(?:answer|owner|holder|result|destination|output|response|final (?:answer|symbol|destination)|it|this|that|one)\s*(?:is|:|=|would be|should be|must be|will be)\s*(?:the\s+)?[\"'“‘]?" + boundary_l + c + boundary_r,
        r"^\W*" + c + r"\W*$",
        boundary_l + c + boundary_r + r"\s*(?:is|['’]s)\s+the\s+(?:answer|owner|one|holder|result|destination)\b",
        boundary_l + c + boundary_r + r"\s+has it\b",
        r"\b(?:reach(?:es|ed)?|end(?:s|ed)? (?:up )?(?:at|in|on|with)|land(?:s|ed)? (?:on|at)|arrive(?:s|d)? at|get(?:s)? to)\s+(?:the\s+)?[\"'“‘]?" + boundary_l + c + boundary_r,
    ]
    out = []
    for p in pats:
        for m in re.finditer(p, text.strip(), flags | re.M):
            if not _negated(text, m.start()):
                out.append((m.start(), m.end()))
    return out


def _extract_language(text: str, item: dict) -> dict:
    cands = item["primary"]["candidates"]
    answer = item["primary"]["answer"]
    other = cands[1 - cands.index(answer)]
    forms = {c: LANGUAGE_NAME_FORMS[c] for c in cands}
    hedges = _hedge_spans(text, forms[cands[0]], forms[cands[1]])
    asserted: Dict[str, List[str]] = {c: [] for c in cands}
    mentioned: List[str] = []
    name_negated: Dict[str, bool] = {c: False for c in cands}
    for c in cands:
        for s, e, neg in _mentions(text, forms[c]):
            if c not in mentioned:
                mentioned.append(c)
            if neg:
                name_negated[c] = True
            elif not _in_spans(s, hedges):
                asserted[c].append("named: " + _span(text, s, e))
    lang, hits = detect_language(text, cands)
    # J1: if this language's NAME is negated anywhere, written-in evidence needs >= 2 distinct hits
    if lang is not None and name_negated[lang] and len(hits[lang]) < LANGUAGE_WRITTEN_IN_MIN_HITS_IF_NAME_NEGATED:
        lang = None
    if lang is not None:
        asserted[lang].append("written-in: " + ", ".join(hits[lang][:6]))
    status, value = _status(asserted, answer, other)
    evidence = " | ".join(asserted[answer][:2] + asserted[other][:2])
    if status == "unclear" and hedges:
        evidence = "hedged: " + _span(text, hedges[0][0], hedges[0][1])
    return {"primary": {"status": status, "value": value, "evidence": evidence},
            "entities_mentioned": mentioned, "objects_mentioned": [],
            "relation": {"status": "absent", "evidence": "n/a: family has no secondary relation"},
            "detail": {"language_word_hits": hits}}


def _extract_tense(text: str, item: dict) -> dict:
    answer = item["primary"]["answer"]
    other = "future" if answer == "past" else "past"
    mk = tense_readout_markers(text)
    asserted = {"past": list(mk["strong_past"]), "future": list(mk["strong_future"])}
    layer = "strong"
    if not asserted["past"] and not asserted["future"] and TENSE_USE_WEAK_LAYER:
        asserted = {"past": list(mk["weak_past"]), "future": list(mk["weak_future"])}
        layer = "weak"
    status, value = _status(asserted, answer, other)
    evidence = f"{layer}: past={asserted['past'][:4]} future={asserted['future'][:4]}"
    return {"primary": {"status": status, "value": value, "evidence": evidence},
            "entities_mentioned": [], "objects_mentioned": [],
            "relation": {"status": "absent", "evidence": "n/a: family has no secondary relation"},
            "detail": {"markers": mk, "layer": layer}}


def _object_regex(obj: str, other_obj: str) -> re.Pattern:
    """Full phrase, or the head noun alone when the two objects have different head nouns."""
    head, other_head = obj.split()[-1], other_obj.split()[-1]
    alts = [re.escape(obj)]
    if head != other_head:
        alts.append(re.escape(head))
    return re.compile(r"\b(?:" + "|".join(alts) + r")s?\b", re.I)


def _extract_ownership(text: str, item: dict) -> dict:
    cands = item["primary"]["candidates"]
    answer = item["primary"]["answer"]
    other = cands[1 - cands.index(answer)]
    ask, other_obj = item["secondary"]["objects"]
    ask_re, other_re = _object_regex(ask, other_obj), _object_regex(other_obj, ask)
    mentioned = [c for c in cands if _mentions(text, [c])]
    objs = [o for o, r in ((ask, ask_re), (other_obj, other_re)) if r.search(text)]
    bindings: Dict[str, List[str]] = {c: [] for c in cands}
    for cl in _clauses(text):
        om = ask_re.search(cl)
        if not om or not POSSESSION_CUE_RE.search(cl):
            continue
        names = [(c, s) for c in cands for s, e, neg in _mentions(cl, [c]) if not neg]
        if not names:
            continue
        # bind the candidate nearest to the asked object (handles "X has the key and Y the rope" leftovers)
        c_best = min(names, key=lambda cs: abs(cs[1] - om.start()))[0]
        bindings[c_best].append(cl)
    asserted: Dict[str, List[str]] = {c: list(bindings[c]) for c in cands}
    for c in cands:
        for s, e in _answer_patterns(text, c):
            asserted[c].append("answer-pattern: " + _span(text, s, e))
    status, value = _status(asserted, answer, other)
    if bindings[answer] and bindings[other]:
        rel = ("wrong", "both candidates bound to the asked object: " + bindings[answer][0][:60] + " || " + bindings[other][0][:60])
    elif bindings[answer]:
        rel = ("correct", bindings[answer][0])
    elif bindings[other]:
        rel = ("wrong", bindings[other][0])
    elif len(mentioned) == 2 and ask in objs:
        rel = ("unbound", "both names and the asked object appear, no binding clause")
    else:
        rel = ("absent", "")
    evidence = " | ".join((asserted[answer] + asserted[other])[:3])
    return {"primary": {"status": status, "value": value, "evidence": evidence},
            "entities_mentioned": mentioned, "objects_mentioned": objs,
            "relation": {"status": rel[0], "evidence": rel[1]},
            "detail": {"bindings": bindings}}


def _extract_mapping(text: str, item: dict) -> dict:
    cands = item["primary"]["candidates"]
    answer = item["primary"]["answer"]
    other = cands[1 - cands.index(answer)]
    start, mid = item["secondary"]["entities"][0], item["secondary"]["entities"][1]
    symbols = item["secondary"]["entities"]
    mentioned = [s for s in symbols if _mentions(text, [s])]
    bindings: Dict[str, List[Tuple[str, str]]] = {c: [] for c in cands}  # cand -> [(src, span)]
    for src in (start, mid):
        for dst in cands:
            s_re, d_re = _symbol_regex(src).pattern, _symbol_regex(dst).pattern
            flags = 0 if (_is_single_letter(src) or _is_single_letter(dst)) else re.I
            pats = [
                s_re + r"\s*(?:,|:)?\s*" + ARROW + r"\s*(?:the\s+)?" + d_re,                         # "B -> C", "B maps to C"
                s_re + r"\s*" + ARROW + r"\s*\S+\s*" + ARROW + r"\s*" + d_re,                          # "A -> B -> C"
                r"(?:from|at|starting (?:at|from)|start(?:ing)? at|begin(?:ning)? at)\s+" + s_re + r"\b.{0,80}?" + REACH + r"\s+(?:the\s+)?[\"'“‘]?" + d_re,
            ]
            for p in pats:
                for m in re.finditer(p, text, flags | re.I if flags else flags):
                    if not _negated(text, m.start()):
                        bindings[dst].append((src, _span(text, m.start(), m.end(), 10)))
    def _primary_bindings(c):
        return [b for b in bindings[c] if b[0] == start or MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY]
    asserted: Dict[str, List[str]] = {c: [f"{src}->{c}: {sp}" for src, sp in _primary_bindings(c)] for c in cands}
    for c in cands:
        for s, e in _answer_patterns(text, c):
            asserted[c].append("answer-pattern: " + _span(text, s, e))
    status, value = _status(asserted, answer, other)
    mid_ans = [sp for src, sp in bindings[answer] if src == mid]
    mid_oth = [sp for src, sp in bindings[other] if src == mid]
    if mid_ans and mid_oth:
        rel = ("wrong", "intermediate bound to both candidates: " + mid_ans[0] + " || " + mid_oth[0])
    elif mid_ans:
        rel = ("correct", mid_ans[0])
    elif mid_oth:
        rel = ("wrong", mid_oth[0])
    elif mid in mentioned and all(c in mentioned for c in cands):
        rel = ("unbound", "intermediate and both candidates appear, no directed binding")
    else:
        rel = ("absent", "")
    evidence = " | ".join((asserted[answer] + asserted[other])[:3])
    return {"primary": {"status": status, "value": value, "evidence": evidence},
            "entities_mentioned": mentioned, "objects_mentioned": [],
            "relation": {"status": rel[0], "evidence": rel[1]},
            "detail": {"bindings": {c: [list(b) for b in bindings[c]] for c in cands}}}


def _extract_choice(text: str, item: dict) -> dict:
    """G6 'choice' family (rubric §10). No external answer key: a single asserted candidate is recorded
    as `supports` with `provisional: True`; score_claims re-labels it against the target's own answer."""
    cands = item["primary"]["candidates"]
    hedges = _hedge_spans(text, [cands[0]], [cands[1]])
    asserted: Dict[str, List[str]] = {c: [] for c in cands}
    mentioned: List[str] = []
    for c in cands:
        for s, e, neg in _mentions(text, [c]):
            if c not in mentioned:
                mentioned.append(c)
            if not neg and not _in_spans(s, hedges):
                asserted[c].append("named: " + _span(text, s, e))
        for s, e in _answer_patterns(text, c):
            asserted[c].append("answer-pattern: " + _span(text, s, e))
    answer = item["primary"].get("answer")
    if answer in cands:  # key already filled in (analysis may re-extract with the target answer)
        status, value = _status(asserted, answer, cands[1 - cands.index(answer)])
        provisional = False
    else:
        hit = [c for c in cands if asserted[c]]
        if len(hit) == 2:
            status, value = "self_contradictory", None
        elif len(hit) == 1:
            status, value = "supports", hit[0]
        else:
            status, value = "unclear", None
        provisional = status == "supports"
    evidence = " | ".join((asserted[cands[0]] + asserted[cands[1]])[:3])
    if status == "unclear" and hedges:
        evidence = "hedged: " + _span(text, hedges[0][0], hedges[0][1])
    return {"primary": {"status": status, "value": value, "evidence": evidence, "provisional": provisional},
            "entities_mentioned": mentioned, "objects_mentioned": [],
            "relation": {"status": "absent", "evidence": "n/a: family has no secondary relation"},
            "detail": {"asserted": asserted}}


# =============================================================================================
# J-lens token-list extractor (never turns tokens into a sentence)
# =============================================================================================
def jlens_forms(item: dict) -> Dict[str, List[str]]:
    fam = item["family"]
    cands = item["primary"]["candidates"]
    if fam == "language":
        return {c: sorted({fold(f) for f in LANGUAGE_NAME_FORMS[c]}) for c in cands}
    if fam == "tense":
        return {"past": ["past", "yesterday", "happened", "ago", "was", "were", "did", "earlier", "previously", "preterite"],
                "future": ["future", "tomorrow", "will", "shall", "going", "upcoming", "next", "later", "soon"]}
    return {c: [fold(c)] for c in cands}


def _token_matches(tok: str, forms: Sequence[str], other_forms: Sequence[str], raw: str) -> bool:
    f = fold(tok)
    if not f:
        return False
    for form in forms:
        if len(form) == 1:  # single-letter symbol: exact, case-sensitive on the raw token
            if raw.replace("Ġ", "").replace("▁", "").strip() == form.upper():
                return True
            continue
        if f == form:
            return True
        if len(f) >= JLENS_PREFIX_MIN and form.startswith(f) and not any(o.startswith(f) for o in other_forms):
            return True
    return False


def _parse_tokens(text_or_tokens: Any) -> List[str]:
    if isinstance(text_or_tokens, (list, tuple)):
        return [str(t) for t in text_or_tokens]
    s = str(text_or_tokens).strip()
    if s.startswith("["):
        try:
            return [str(t) for t in json.loads(s)]
        except json.JSONDecodeError:
            pass
    return [t for t in re.split(r"[,\n]", s) if t.strip()]


def _extract_jlens(text_or_tokens: Any, item: dict) -> dict:
    tokens = _parse_tokens(text_or_tokens)[:JLENS_TOP_K]
    cands = item["primary"]["candidates"]
    answer = item["primary"]["answer"]
    other = cands[1 - cands.index(answer)] if answer in cands else None
    forms = jlens_forms(item)
    hits: Dict[str, List[str]] = {c: [] for c in cands}
    for tok in tokens:
        for c in cands:
            oth = [f for o in cands if o != c for f in forms[o]]
            if _token_matches(tok, forms[c], oth, tok):
                hits[c].append(tok)
    if answer in cands:
        status, value = _status(hits, answer, other)
    else:  # choice family without a key yet: provisional, see _extract_choice
        hit = [c for c in cands if hits[c]]
        status, value = ("self_contradictory", None) if len(hit) == 2 else ("supports", hit[0]) if hit else ("unclear", None)
    ents = []
    for e in item["secondary"].get("entities") or []:
        if any(_token_matches(t, [fold(e)], [], t) for t in tokens):
            ents.append(e)
    if item["family"] == "language":
        ents = [c for c in cands if hits[c]]
    return {"primary": {"status": status, "value": value,
                        "evidence": json.dumps({c: hits[c] for c in cands}, ensure_ascii=False)},
            "entities_mentioned": ents, "objects_mentioned": [],
            "relation": {"status": "absent", "evidence": "n/a: token list carries no binding"},
            "detail": {"tokens": tokens, "hits": hits}}


# =============================================================================================
# Public API
# =============================================================================================
def extract_claims(text: Any, item: dict, method: str, finish_reason: Optional[str] = None) -> dict:
    """Return the claim body for one readout. `text` is a str for text methods, a token list (or its
    JSON) for method == 'jlens'. `finish_reason == 'length'` sets truncated."""
    fam = item["family"]
    if method == "jlens":
        out = _extract_jlens(text, item)
    else:
        text = "" if text is None else str(text)
        out = {"language": _extract_language, "tense": _extract_tense, "ownership": _extract_ownership,
               "mapping": _extract_mapping, "choice": _extract_choice}[fam](text, item)
    out["truncated"] = finish_reason == "length"
    out["extractor"] = EXTRACTOR_ID
    out["method"] = method
    out["item_id"] = item["item_id"]
    assert out["primary"]["status"] in STATUSES
    return out


def gen_text(gen: dict) -> Any:
    """The text (or token list) a reader produced, per INTERFACES §5."""
    native = gen.get("native") or {}
    if gen.get("method") in ("jlens", "jlens_null"):
        # prefer the decoded strings (tokenizer.decode per id); the byte-level BPE display strings
        # mangle non-ASCII tokens (" franÃ§ais"), which the rubric could not match.
        return native.get("tokens_decoded") or native.get("tokens", [])
    if "text" in native:
        return native["text"]
    samples = native.get("samples") or []
    if samples:
        return samples[0]
    return gen.get("raw_output", "")


def claim_from_gen(gen: dict, item: dict) -> dict:
    assert gen["item_id"] == item["item_id"], (gen["item_id"], item["item_id"])
    c = extract_claims(gen_text(gen), item, gen["method"], gen.get("finish_reason"))
    return {"gen_id": gen["gen_id"], "method": gen["method"], "item_id": item["item_id"],
            "extractor": EXTRACTOR_ID, "primary": c["primary"],
            "entities_mentioned": c["entities_mentioned"], "objects_mentioned": c["objects_mentioned"],
            "relation": c["relation"], "truncated": c["truncated"], "blind": True}


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DEFAULT_SHEET_CACHE = os.path.join(REPO_ROOT, "cache", "g_agreement")


def sheet_id_for(gen_id: str, salt: str) -> str:
    return hashlib.sha256((salt + gen_id).encode("utf-8")).hexdigest()[:12]


def make_blind_sheet(gens: Iterable[dict], seed: int = 20261007, module: str = "g1",
                     salt: Optional[str] = None, cache_dir: Optional[str] = None) -> List[dict]:
    """Rows with an opaque sheet_id (sha256(salt + gen_id)[:12]), method and text only — no gen_id,
    no item_id, no answer key — in an order shuffled by `seed`. `salt` defaults to the content of
    <cache_dir>/sheet_salt.txt (created on first use). The mapping {sheet_id: gen_id} is written to
    <cache_dir>/sheet_map_<module>.json (default cache/g_agreement/, never results/)."""
    cache_dir = DEFAULT_SHEET_CACHE if cache_dir is None else cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    if salt is None:  # default salt: read cache/<...>/sheet_salt.txt, create it on first use
        salt_path = os.path.join(cache_dir, "sheet_salt.txt")
        if not os.path.exists(salt_path):
            import secrets
            with open(salt_path, "w", encoding="utf-8") as f:
                f.write(secrets.token_hex(16))
        with open(salt_path, encoding="utf-8") as f:
            salt = f.read().strip()
    rows, mapping = [], {}
    for g in gens:
        t = gen_text(g)
        text = json.dumps(t, ensure_ascii=False) if isinstance(t, (list, tuple)) else str(t)
        sid = sheet_id_for(g["gen_id"], salt)
        assert sid not in mapping, f"sheet_id collision for {g['gen_id']}"
        mapping[sid] = g["gen_id"]
        rows.append({"sheet_id": sid, "method": g["method"], "text": text})
    random.Random(seed).shuffle(rows)
    with open(os.path.join(cache_dir, f"sheet_map_{module}.json"), "w", encoding="utf-8") as f:
        json.dump({"module": module, "seed": seed, "map": mapping}, f, ensure_ascii=False, indent=1)
    return rows


def extract_target_answer(text: str, item: dict) -> Tuple[Optional[str], str]:
    """The target model's own answer as one of the two candidates (or None)."""
    fam = item["family"]
    cands = item["primary"]["candidates"]
    text = "" if text is None else str(text)
    if fam == "language":
        lab, hits = detect_language(text, cands)
        return lab, json.dumps(hits, ensure_ascii=False)
    if fam == "tense":
        lab, ev = detect_tense(text)
        return (lab if lab in cands else None), json.dumps(ev, ensure_ascii=False)
    present = [c for c in cands if _mentions(text, [c])]
    if fam == "choice" and len(present) == 2:
        first = re.sub(r"^\W+", "", text).split()
        head = re.sub(r"\W+$", "", first[0]) if first else ""
        for c in cands:
            if head.lower() == c.lower():
                return c, "first word (both options mentioned)"
        return None, "both options mentioned, neither is the first word"
    first = re.sub(r"^\W+", "", text).split()
    if first:
        head = re.sub(r"\W+$", "", first[0])
        for c in cands:
            if (head == c) if _is_single_letter(c) else (head.lower() == c.lower()):
                return c, "first word"
    if len(present) == 1:
        return present[0], "only candidate mentioned"
    return None, f"candidates present: {present}"


def _index(items: Any) -> Dict[str, dict]:
    if isinstance(items, dict) and "items" in items:
        items = items["items"]
    if isinstance(items, dict):
        return items
    return {it["item_id"]: it for it in items}


def _target_texts(targets: Any) -> Dict[str, str]:
    if targets is None:
        return {}
    if isinstance(targets, dict):
        return {k: (gen_text(v) if isinstance(v, dict) else v) for k, v in targets.items()}
    return {g["item_id"]: gen_text(g) for g in targets}


def score_claims(claims: Iterable[dict], items: Any, targets: Any = None) -> List[dict]:
    """Per-claim rows. `factual_correct` compares the claim value with the answer key;
    `target_consistent` compares it with the target model's OWN extracted answer. Both are None
    when the claim is unclear/self_contradictory (or when the target gave no classifiable answer)."""
    idx, tt = _index(items), _target_texts(targets)
    rows = []
    for c in claims:
        it = idx[c["item_id"]]
        answer = it["primary"]["answer"]
        status, value = c["primary"]["status"], c["primary"].get("value")
        decided = status in ("supports", "contradicts")
        tv, tev, treg = None, "", None
        if c["item_id"] in tt:
            tv, tev = extract_target_answer(tt[c["item_id"]], it)
            treg = bool(re.search(it["target_answer_regex"], str(tt[c["item_id"]])))
        if it["family"] == "choice" and answer is None:
            # the key IS the target's greedy answer; a provisional `supports` is re-labelled against it
            answer = tv
            if decided and tv is not None:
                status = "supports" if value == tv else "contradicts"
            elif decided:
                status = "supports" if c["primary"].get("provisional") else status
        rows.append({
            "gen_id": c.get("gen_id"), "method": c.get("method"), "item_id": c["item_id"],
            "family": it["family"], "split": it["split"], "pair_id": it["pair_id"],
            "status": status, "value": value, "answer": answer,
            "factual_correct": (value == answer) if (decided and answer is not None) else None,
            "target_value": tv, "target_regex_match": treg,
            "target_correct": (tv == answer) if tv is not None else None,
            "target_consistent": (value == tv) if (decided and tv is not None) else None,
            "truncated": bool(c.get("truncated")),
            "relation_status": (c.get("relation") or {}).get("status"),
        })
    return rows
