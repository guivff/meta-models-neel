"""Independent content-only semantic checks; does not import the item author.

This is a bounded deterministic checker, not a general English understanding
system. Unsupported, conflicting, or insufficient evidence raises ValueError.
"""
from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from dataclasses import dataclass


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def _choose(a: set[str], b: set[str], values: tuple[str, str], minimum: int = 2) -> dict:
    if bool(a) == bool(b) or max(len(a), len(b)) < minimum:
        raise ValueError("ambiguous or insufficient semantic evidence")
    return {"value": values[bool(b)], "evidence": {values[0]: sorted(a), values[1]: sorted(b)}}


_POSITIVE = set("""
admirable admiration affection appealing appreciate appreciation approval beautiful
beautifully bright brighter care cheerful charming considerate consistent contentment
delight delighted delightful dependable engaging enjoyable enthusiastic excellent
glad gladness gladly grateful happiness happily helpful impressive impressed joy
lovely memorable pleasure pleased pleasing pleasant pleasantly polished positive
praise reassuring recommendation refreshing rewarding satisfying sincere superb
successful thoughtful valued warmth welcoming wonderful worthwhile
""".split())
_NEGATIVE = set("""
abysmal alienating appalling awful bad badly bitter careless carelessness clumsy
coldness contempt criticism crushed dark darker depressing disappointment disappointed
disappointing disapproval discourage discontent disgusted dismissive dislike distressing
dreariness dreadful emphatic exhausting frustrating frustration gloomy horrible
irritating miserable misery negative painful painfully regret regretful reluctantly
resented resentful resentment shocking sloppy sadness tedious terrible troubling
unhelpful unpleasant unsuccessful upsetting warning worthless
""".split())
_NEGATORS = {"not", "never", "no", "neither", "hardly", "barely", "without", "isn't", "wasn't", "weren't", "didn't", "don't", "doesn't", "cannot", "can't"}


def _sentiment(text: str) -> dict:
    positive, negative = set(), set()
    # Punctuation and coordinating clauses end a short negation scope.
    clauses = re.split(r"[.!?;,:]|\b(?:but|yet|however|although|and)\b", text.lower())
    for clause in clauses:
        words = _words(clause)
        # Negation scope is not recoverable from a fixed word-distance window.
        # Support only short, single-evaluation constructions; reject the rest.
        negators = [i for i, word in enumerate(words) if word in _NEGATORS
                    and words[i:i + 2] != ["not", "only"]]
        opinion_positions = [i for i, word in enumerate(words)
                             if word in _POSITIVE or word in _NEGATIVE]
        negated_positions = set()
        if negators:
            modifiers = {"at", "all", "very", "particularly", "really", "quite", "especially", "so", "even", "remotely", "entirely", "truly"}
            if len(negators) != 1 or len(opinion_positions) != 1:
                raise ValueError("unsupported sentiment negation scope")
            start, stop = negators[0], opinion_positions[0]
            if not start < stop <= start + 3 or not set(words[start + 1:stop]) <= modifiers:
                raise ValueError("unsupported sentiment negation scope")
            if any(word in {"enough", "unless", "except", "or"} for word in words[stop + 1:]):
                raise ValueError("unsupported sentiment negation continuation")
            negated_positions.add(stop)
        for i, word in enumerate(words):
            if word not in _POSITIVE and word not in _NEGATIVE:
                continue
            negated = i in negated_positions
            is_positive = (word in _POSITIVE) != negated
            evidence = ("negated:" if negated else "") + word
            (positive if is_positive else negative).add(evidence)
    # A few discourse words are not evaluative by themselves.
    for weak in ("care", "sincere", "consistent", "memorable", "emphatic"):
        positive.discard(weak)
        negative.discard(weak)
    return _choose(positive, negative, ("positive", "negative"))


_GARDEN = set("""garden gardens gardener gardeners gardening soil compost planting planted
seed seeds seedling seedlings germination vegetable vegetables crops crop cultivation
cultivated watering irrigation pruning pruned weeds mulch greenhouse potting nursery
trellis tomatoes beans foliage flowering bushes shoots roots stems harvest cabbages""".split())
_OCEAN = set("""ocean oceans oceanic marine seawater saltwater salinity coral corals reef reefs
seabed tides tidal lagoon offshore plankton upwelling submerged underwater continental
coastal coast shoal shoals migrating currents circulation sediment waves""".split())
_TRAVEL = set("""travel trip journey itinerary holiday flight flights airport passport visa
border luggage suitcase destination destinations hotel accommodation boarding transport
train tickets ticket departure arrival reservation attractions sights transfer""".split())
_STUDY = set("""study studying revision revise revised course syllabus exam examination
assessment textbook lecture chapters chapter exercises exercise practice learning
library notebooks material questions reinforce master objectives memorise memorize notes quiz""".split())
_ALGEBRA = set("""algebra algebraic polynomial polynomials coefficients coefficient roots root
factorization factoring equations equation variable variables matrix matrices invertible
determinant determinants eigenvalue eigenvector scalar linear vector vectors group groups
associativity associative identity inverse homomorphism kernel subgroup ring ideal quotient
cosets arithmetic symbolic recurrence discriminant quadratic""".split())
_GEOMETRY = set("""geometry geometric geometrical triangle triangles triangular polygon polygons
quadrilateral angle angles circle circles circumference chord chordal chord chords arc radius
radii diameter perpendicular bisector altitude midpoint endpoints vertex vertices planar
surface sphere spherical tessellation tessellations congruent reflection diagram diagonal
distances distance lengths length coordinate axes tangent cosine tiled""".split())


def _domain(text: str, which: str) -> dict:
    if which == "list_topic":
        text = _current_list_item(text)
    words = set(_words(text))
    if which == "prose_topic":
        return _choose(words & _GARDEN, words & _OCEAN, ("garden", "ocean"), 3)
    if which == "list_topic":
        # "reservation" and "library" alone do not distinguish trips from study.
        return _choose(words & (_TRAVEL - {"reservation"}), words & (_STUDY - {"library"}), ("travel", "study"), 3)
    # Matrix/vector can describe spatial geometry; remove overlap when geometry
    # has explicit supporting evidence. The inverse exception is not assumed.
    algebra, geometry = words & _ALGEBRA, words & _GEOMETRY
    incidental_algebra = {"linear", "vector", "vectors", "matrix", "matrices", "equation", "equations", "coefficients", "roots", "root"}
    incidental_geometry = {"distances", "distance", "length", "lengths", "coordinate"}
    if len(geometry - incidental_geometry) >= 3:
        algebra -= incidental_algebra
    if len(algebra - incidental_algebra) >= 2:
        geometry -= incidental_geometry
    return _choose(algebra, geometry, ("algebra", "geometry"), 3)


def _current_list_item(text: str) -> str:
    """Return only the actual final bullet item, including indented continuation."""
    lines = text.rstrip().splitlines()
    bullet = re.compile(r"^(?P<indent>[ \t]*)[-*+]\s+(?:\[[ xX]\]\s+)?(?P<body>\S.*)$")
    matches = [(index, bullet.match(line)) for index, line in enumerate(lines)]
    matches = [(index, match) for index, match in matches if match is not None]
    if not matches:
        raise ValueError("expected a current Markdown list item")
    index, match = matches[-1]
    indent = len(match.group("indent").expandtabs(4))
    continuation = lines[index + 1:]
    if any(not line.strip() or len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip()) <= indent for line in continuation):
        raise ValueError("final token is outside the current list item")
    return " ".join([match.group("body")] + [line.strip() for line in continuation])


def _priority(text: str) -> dict:
    lowered = _current_list_item(text).lower()
    # Only these short negations have a supported urgency interpretation. In
    # particular, do not turn long-distance negation into a positive match.
    unchecked = re.sub(r"\b(?:not|never) urgent\b|\bwithout delay\b", "", lowered)
    if set(_words(unchecked)) & _NEGATORS:
        raise ValueError("unsupported priority negation scope")
    urgent_patterns = (r"\bimmediately\b", r"\bright now\b", r"\bright away\b", r"\bwithout delay\b", r"\bwithin (?:the next )?(?:\d+ )?minutes\b", r"\bimminent\b", r"\bimmediate (?:attention|action|replacement)\b", r"\brequires? immediate\b", r"\bmust be (?:fixed|corrected|covered)\b", r"\burgent\b", r"\btime.critical\b", r"\bactive outage\b")
    routine_patterns = (r"\broutine\b", r"\bscheduled maintenance\b", r"\bregular (?:inspection|review|briefing|staffing|monthly)\b", r"\bnext (?:week|month|monthly)\b", r"\bnormal (?:schedule|scheduling|service|operation|arrangements)\b", r"\bplanned (?:rotation|revision|schedule)\b", r"\busual monthly\b", r"\blow.priority\b", r"\bcan wait\b", r"\bevery (?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")
    urgent, routine = set(), set()
    for patterns, target, opposite in ((urgent_patterns, urgent, routine), (routine_patterns, routine, urgent)):
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                lead = _words(lowered[max(0, match.start() - 24):match.start()])
                negated = any(word in _NEGATORS for word in lead[-3:])
                (opposite if negated else target).add(("negated:" if negated else "") + match.group())
    return _choose(urgent, routine, ("urgent", "routine"), 1)


def _latex_role(text: str) -> dict:
    if "\\" not in text:
        raise ValueError("expected LaTeX prose")
    # Strip display labels before classifying the statement's semantic form.
    body = re.sub(r"\\(?:paragraph|section|subsection)\{[^}]*\}", "", text)
    if "?" in body:
        raise ValueError("an interrogative is not an asserted theorem or worked example")
    lowered = body.lower()
    general = set(re.findall(r"\b(?:for every|every [a-z]+|for any|any linear map|in any group|arbitrary|in general|proves? the|proving the|establish(?:es|ing) the)\b", lowered))
    concrete = set(re.findall(r"\b(?:chosen|choose|take the|consider the|particular|worked calculation|numerical calculation|direct substitution|substituting these values|compute their|calculate the|evaluate its)\b", lowered))
    math_has_number = bool(re.search(r"\\\([^)]*\d", body))
    if concrete and math_has_number and not general:
        return {"value": "example", "evidence": {"concrete_computation": sorted(concrete), "numeric_math": True}}
    if general and not concrete:
        return {"value": "theorem", "evidence": {"general_claim": sorted(general)}}
    raise ValueError("ambiguous theorem/example content")


_UNSET = object()


@dataclass
class _Shape:
    """Abstract built-in value; never an executed value from the supplied code."""
    kind: str
    literal: object = _UNSET
    items: object = None
    item: object = None


def _merge_shape(left, right):
    if left is None or left.kind == "unknown":
        return right
    if right is None or right.kind == "unknown":
        return left
    return _Shape(left.kind if left.kind == right.kind else "ordinary")


class _BoundedPython:
    """Analyze ordinary finite built-in data, not arbitrary Python objects.

    External sequences must be finite and have elements compatible with requested
    built-ins (numeric for sum, mutually sortable for sorted). Unknown calls and
    arbitrary object protocols are outside this explicit input contract.
    """

    def __init__(self, arguments):
        self.env = {arg.arg: _Shape("input") for arg in arguments.posonlyargs + arguments.args + arguments.kwonlyargs}
        self.active_iterables = []
        for arg in (arguments.vararg, arguments.kwarg):
            if arg is not None:
                self.env[arg.arg] = _Shape("sequence", item=_Shape("ordinary"))

    def element(self, value):
        if value.kind == "input":
            return _Shape("ordinary")
        if value.kind == "str":
            return _Shape("str")
        if value.kind not in ("sequence", "set", "dict"):
            raise ValueError("unsupported or non-finite iterable")
        if value.items is not None:
            merged = _Shape("unknown")
            for item in value.items:
                merged = _merge_shape(merged, item)
            return merged
        return value.item or _Shape("ordinary")

    def bind(self, target, value):
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            if value.items is None or len(target.elts) != len(value.items):
                raise ValueError("unpacking length is not statically known")
            for part, item in zip(target.elts, value.items):
                self.bind(part, item)
        elif isinstance(target, ast.Subscript):
            container = self.expression(target.value)
            key = self.expression(target.slice)
            if container.kind != "dict" or key.kind not in ("str", "integer", "number", "bool", "none"):
                raise ValueError("only supported dictionary updates are permitted")
            if any(container is iterable for iterable in self.active_iterables):
                raise ValueError("mutating a collection during iteration is unsupported")
            container.item = _merge_shape(container.item, value)
        else:
            raise ValueError("unsupported assignment target")

    def expression(self, node):
        if node is None:
            return _Shape("none", None)
        if isinstance(node, ast.Constant):
            kind = "bool" if isinstance(node.value, bool) else "integer" if isinstance(node.value, int) else "number" if isinstance(node.value, (float, complex)) else "str" if isinstance(node.value, str) else "none" if node.value is None else "ordinary"
            return _Shape(kind, node.value)
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise ValueError("unbound or external name")
            return self.env[node.id]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            items = tuple(self.expression(item) for item in node.elts)
            if isinstance(node, ast.Set) and any(item.kind not in ("integer", "number", "str", "bool", "none") for item in items):
                raise ValueError("set elements are not provably hashable")
            return _Shape("set" if isinstance(node, ast.Set) else "sequence", items=items)
        if isinstance(node, ast.Dict):
            values = _Shape("unknown")
            for key, value in zip(node.keys, node.values):
                if key is None or self.expression(key).kind not in ("integer", "number", "str", "bool", "none"):
                    raise ValueError("unsupported dictionary key")
                values = _merge_shape(values, self.expression(value))
            return _Shape("dict", item=values)
        if isinstance(node, ast.JoinedStr):
            for piece in node.values:
                if isinstance(piece, ast.FormattedValue):
                    self.expression(piece.value)
                    if piece.format_spec is not None:
                        raise ValueError("dynamic format specifications are unsupported")
                elif not isinstance(piece, ast.Constant):
                    raise ValueError("unsupported string component")
            return _Shape("str")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self.expression(node.operand)
            if value.kind not in ("integer", "number"):
                raise ValueError("unsupported unary arithmetic")
            literal = value.literal
            if literal is not _UNSET and isinstance(node.op, ast.USub):
                literal = -literal
            return _Shape(value.kind, literal)
        if isinstance(node, ast.BinOp):
            left, right = self.expression(node.left), self.expression(node.right)
            if isinstance(node.op, ast.Add) and left.kind in ("integer", "number") and right.kind in ("integer", "number"):
                return _Shape("integer" if left.kind == right.kind == "integer" else "number")
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and left.kind in ("integer", "number") and right.kind in ("integer", "number"):
                if right.literal is _UNSET or right.literal == 0:
                    raise ValueError("division requires a known nonzero denominator")
                if not isinstance(node.op, ast.Div) and not left.kind == right.kind == "integer":
                    raise ValueError("floor division and remainder require integer operands")
                return _Shape("integer" if not isinstance(node.op, ast.Div) and left.kind == right.kind == "integer" else "number")
            raise ValueError("unsupported operator or operand type")
        if isinstance(node, ast.Compare) and all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
            self.expression(node.left)
            for other in node.comparators:
                self.expression(other)
            return _Shape("bool")
        if isinstance(node, ast.Subscript):
            container = self.expression(node.value)
            if isinstance(node.slice, ast.Slice):
                if container.kind not in ("input", "sequence", "str"):
                    raise ValueError("unsupported slice container")
                for part in (node.slice.lower, node.slice.upper, node.slice.step):
                    if part is not None and self.expression(part).kind != "integer":
                        raise ValueError("unsupported slice bound")
                if node.slice.step is not None and self.expression(node.slice.step).literal in (0, _UNSET):
                    raise ValueError("slice step must be known and nonzero")
                return _Shape("str" if container.kind == "str" else "sequence", item=self.element(container))
            index = self.expression(node.slice)
            if container.items is None or type(index.literal) is not int or not -len(container.items) <= index.literal < len(container.items):
                raise ValueError("subscript bounds are not statically safe")
            return container.items[index.literal]
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            saved = dict(self.env)
            try:
                for generator in node.generators:
                    if generator.is_async:
                        raise ValueError("async comprehensions are unsupported")
                    self.bind(generator.target, self.element(self.expression(generator.iter)))
                    for condition in generator.ifs:
                        if self.expression(condition).kind != "bool":
                            raise ValueError("unsupported comprehension condition")
                if isinstance(node, ast.DictComp):
                    if self.expression(node.key).kind not in ("integer", "number", "str", "bool", "none"):
                        raise ValueError("unsupported dictionary key")
                    return _Shape("dict", item=self.expression(node.value))
                value = self.expression(node.elt)
                return _Shape("set" if isinstance(node, ast.SetComp) else "sequence", item=value)
            finally:
                self.env = saved
        if isinstance(node, ast.Call):
            args = [self.expression(arg) for arg in node.args]
            keywords = {item.arg: self.expression(item.value) for item in node.keywords}
            if None in keywords:
                raise ValueError("unpacked keyword arguments are unsupported")
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in self.env:
                    raise ValueError("a shadowed built-in call is unsupported")
                if name in ("ValueError", "RuntimeError", "TypeError", "KeyError", "IndexError") and not keywords:
                    return _Shape("exception")
                if name == "str" and len(args) == 1 and not keywords:
                    return _Shape("str")
                if name == "len" and len(args) == 1 and not keywords:
                    self.element(args[0])
                    return _Shape("integer")
                if name == "sum" and len(args) == 1 and not keywords:
                    item = self.element(args[0])
                    if item.kind not in ("integer", "number", "ordinary", "unknown"):
                        raise ValueError("sum requires numeric elements")
                    return _Shape("number")
                if name == "max" and len(args) == 1 and set(keywords) == {"default"}:
                    return _merge_shape(self.element(args[0]), keywords["default"])
                if name in ("list", "set", "sorted", "reversed") and len(args) == 1 and not keywords:
                    return _Shape("set" if name == "set" else "sequence", item=self.element(args[0]))
                if name == "enumerate" and len(args) == 1 and not keywords:
                    return _Shape("sequence", item=_Shape("sequence", items=(_Shape("integer"), self.element(args[0]))))
                if name == "zip" and args and not keywords:
                    return _Shape("sequence", item=_Shape("sequence", items=tuple(self.element(arg) for arg in args)))
            if isinstance(node.func, ast.Attribute):
                receiver = self.expression(node.func.value)
                method = node.func.attr
                if method == "strip" and receiver.kind == "str" and not args and not keywords:
                    return _Shape("str")
                if method == "join" and receiver.kind == "str" and len(args) == 1 and not keywords:
                    if self.element(args[0]).kind not in ("str", "unknown"):
                        raise ValueError("join requires strings")
                    return _Shape("str")
                if method == "get" and receiver.kind == "dict" and len(args) == 2 and not keywords:
                    if args[0].kind not in ("str", "integer", "number", "bool", "none"):
                        raise ValueError("dictionary lookup requires a supported hashable key")
                    return _merge_shape(receiver.item, args[1])
            raise ValueError("unknown call or unsupported call signature")
        raise ValueError("unsupported expression grammar")

    def statement(self, node):
        if isinstance(node, ast.Assign):
            value = self.expression(node.value)
            for target in node.targets:
                self.bind(target, value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            self.bind(node.target, self.expression(node.value))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            pass  # A docstring cannot change control flow.
        elif isinstance(node, ast.Pass):
            pass
        elif isinstance(node, ast.For) and not node.orelse:
            iterable = self.expression(node.iter)
            element = self.element(iterable)
            previous_names = set(self.env)
            self.bind(node.target, element)
            self.active_iterables.append(iterable)
            try:
                for statement in node.body:
                    self.statement(statement)
            finally:
                self.active_iterables.pop()
            # A finite loop may be empty: newly introduced names are not definite.
            self.env = {name: value for name, value in self.env.items() if name in previous_names}
        else:
            raise ValueError("unsupported earlier statement or ambiguous control flow")


def _python_error(text: str) -> dict:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise ValueError("incomplete or invalid Python") from exc
    try:
        tokens = [token for token in tokenize.generate_tokens(io.StringIO(text).readline)
                  if token.type not in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE,
                                        tokenize.NL, tokenize.INDENT, tokenize.DEDENT)]
    except (tokenize.TokenError, IndentationError) as exc:
        raise ValueError("invalid Python token stream") from exc
    if not tokens or tokens[-1].type == tokenize.COMMENT:
        raise ValueError("read token is in a comment, not the final statement")
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(functions) != 1 or len(tree.body) != 1:
        raise ValueError("expected exactly one function")
    function = functions[0]
    if not function.body:
        raise ValueError("empty function")
    final = function.body[-1]
    if not isinstance(final, (ast.Raise, ast.Return)):
        raise ValueError("final statement does not unambiguously transfer control")
    analysis = _BoundedPython(function.args)
    for statement in function.body[:-1]:
        analysis.statement(statement)
    analysis.expression(final.value if isinstance(final, ast.Return) else final.exc)
    if isinstance(final, ast.Raise) and final.exc is None:
        raise ValueError("bare raise requires unavailable exception context")
    return {"value": "raise" if isinstance(final, ast.Raise) else "return", "evidence": {"final_statement": type(final).__name__, "line": final.lineno, "function": function.name, "input_contract": "ordinary finite built-in collections with operator-compatible elements"}}


def _json_status(text: str) -> dict:
    tokens, closing = [], []
    i = 0
    decoder = json.JSONDecoder()
    while i < len(text):
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if char == '"':
            try:
                value, consumed = decoder.raw_decode(text[i:])
            except json.JSONDecodeError as exc:
                raise ValueError("incomplete JSON string") from exc
            tokens.append(("string", value))
            i += consumed
        elif char in "{[":
            closing.append("}" if char == "{" else "]")
            tokens.append(("punct", char))
            i += 1
        elif char in "}]":
            if not closing or closing.pop() != char:
                raise ValueError("unbalanced JSON containers")
            tokens.append(("punct", char))
            i += 1
        elif char in ":,":
            tokens.append(("punct", char))
            i += 1
        else:
            match = re.match(r"(?:true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", text[i:])
            if not match:
                raise ValueError("invalid JSON token")
            tokens.append(("atom", match.group()))
            i += len(match.group())
    if len(tokens) < 3 or tokens[-3:-1] != [("string", "decision"), ("punct", ":")]:
        raise ValueError("read token is not the current decision value")
    if tokens[-1] not in (("string", "approved"), ("string", "rejected")):
        raise ValueError("unknown decision")
    try:
        json.loads(text + "".join(reversed(closing)))
    except json.JSONDecodeError as exc:
        raise ValueError("malformed JSON prefix") from exc
    return {"value": tokens[-1][1], "evidence": {"field": "decision", "parsed_value": tokens[-1][1], "open_containers": len(closing)}}


def _table_status(text: str) -> dict:
    raw_lines = text.rstrip().splitlines()
    last_break = max((index for index, line in enumerate(raw_lines) if not line.strip()), default=-1)
    lines = [line.strip() for line in raw_lines[last_break + 1:]]
    if len(lines) < 3:
        raise ValueError("table needs header, separator, and current row")
    def cells(line: str) -> list[str]:
        if not line.startswith("|"):
            raise ValueError("expected a Markdown table row")
        return [cell.strip() for cell in line.strip("|").split("|")]
    separator_index = None
    for index, line in enumerate(lines[:-1]):
        parts = cells(line)
        if parts and all(re.fullmatch(r":?-{3,}:?", cell) for cell in parts):
            separator_index = index
    if separator_index is None or separator_index == 0:
        raise ValueError("missing table separator")
    headers = cells(lines[separator_index - 1])
    separator = cells(lines[separator_index])
    if len(headers) != len(separator) or headers.count("Decision") != 1:
        raise ValueError("invalid or ambiguous Decision column")
    decision_index = headers.index("Decision")
    current = cells(lines[-1])
    if len(current) != decision_index + 1 or current[-1] not in ("approved", "rejected") or lines[-1].endswith("|"):
        raise ValueError("read token does not end the current Decision cell")
    return {"value": current[-1], "evidence": {"column": decision_index + 1, "data_row": len(lines) - separator_index - 1, "parsed_value": current[-1]}}


def infer_label(feature: str, text: str) -> dict:
    """Infer a packet value from actual prefix content; ambiguous content fails."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty text")
    if text[-1].isspace():
        raise ValueError("final read token cannot be inferred by stripping whitespace")
    if feature in ("latex_role", "latex_subject"):
        final_line = text.rsplit("\n", 1)[-1]
        for match in re.finditer("%", final_line):
            slash_count = 0
            cursor = match.start() - 1
            while cursor >= 0 and final_line[cursor] == "\\":
                slash_count += 1
                cursor -= 1
            if slash_count % 2 == 0:
                raise ValueError("read token is inside a LaTeX comment")
    if feature == "prose_sentiment":
        return _sentiment(text)
    if feature in ("prose_topic", "list_topic", "latex_subject"):
        return _domain(text, feature)
    if feature == "list_priority":
        return _priority(text)
    if feature == "latex_role":
        return _latex_role(text)
    if feature == "python_error":
        return _python_error(text)
    if feature == "json_status":
        return _json_status(text)
    if feature == "table_status":
        return _table_status(text)
    raise ValueError("unsupported semantic feature")
