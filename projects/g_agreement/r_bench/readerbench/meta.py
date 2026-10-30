"""META: the kind of request, not its content (PLAN_R §7).

question_type_3     why / when / how many questions over the same event pool (k-way) and why vs when (binary)
instruction_present the same paragraph with or without a leading instruction ("Summarise the following paragraph ...")
answer_format       the same question asking for one word vs a full sentence
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_bools, balanced_levels, fresh, rng_for

# (bare form after "did", finite past form) — the frame picks the one its grammar needs (review fix 2026-10-18 item 4)
EVENTS = [("the committee postpone the vote", "the committee postponed the vote"), ("the ferry stop running", "the ferry stopped running"),
          ("the bakery close early", "the bakery closed early"), ("the orchestra cancel the concert", "the orchestra cancelled the concert"),
          ("the school move the exam", "the school moved the exam"), ("the council repaint the bridge", "the council repainted the bridge"),
          ("the museum change its hours", "the museum changed its hours"), ("the club suspend the captain", "the club suspended the captain"),
          ("the airline ground the fleet", "the airline grounded the fleet"), ("the library extend its lease", "the library extended its lease"),
          ("the mayor resign", "the mayor resigned"), ("the factory halt production", "the factory halted production"),
          ("the band cancel the tour", "the band cancelled the tour"), ("the bank close the branch", "the bank closed the branch"),
          ("the farmers block the road", "the farmers blocked the road"), ("the court adjourn the hearing", "the court adjourned the hearing"),
          ("the station lose power", "the station lost power"), ("the team change its coach", "the team changed its coach"),
          ("the shop raise its prices", "the shop raised its prices"), ("the choir skip the rehearsal", "the choir skipped the rehearsal"),
          ("the city ban cars from the square", "the city banned cars from the square"), ("the publisher delay the book", "the publisher delayed the book"),
          ("the zoo close the aviary", "the zoo closed the aviary"), ("the hospital move the ward", "the hospital moved the ward")]
Q_PREFIX = ["", "Quick question: ", "Tell me: ", "I was wondering: ", "Can you tell me: ", "One thing: "]
Q_FRAMES = {"why": ["Why did {E}?", "For what reason did {E}?", "Explain why {Ep}."],
            "when": ["When did {E}?", "At what time did {E}?", "On what date did {E}?"],
            "how many": ["How many times did {E}?", "How many people saw that {Ep}?", "How many days before {Ep} was it announced?"]}
Q_TYPES = ["why", "when", "how many"]

PARAS = ["The harbour town grew around a single stone pier built by fishermen in the twelfth century. Trade in salt and wool "
         "followed, and by the eighteenth century the town had a customs house, two churches and a weekly market.",
         "Honeybees communicate the location of food through a waggle dance performed inside the hive. The angle of the dance "
         "relative to vertical encodes the direction of the food in relation to the sun, and its duration encodes distance.",
         "The city's tram network opened in 1899 with four horse-drawn lines. Electrification came within a decade, and at its "
         "peak the system carried a quarter of a million passengers a day before buses replaced most routes after the war.",
         "Glass is made by melting sand with soda ash and limestone at temperatures above fifteen hundred degrees. The molten "
         "material is shaped while hot and then cooled slowly so that internal stresses do not crack the finished object.",
         "The island's only village sits on the sheltered eastern shore. Its forty residents fish, keep sheep and run a small "
         "guesthouse for walkers who arrive on the twice-weekly ferry from the mainland during the summer months.",
         "A sourdough starter is a living culture of wild yeast and bacteria kept alive by regular feeding with flour and water. "
         "The acids produced by the bacteria give the bread its tang and help it keep for several days without staling.",
         "The observatory was built on the mountain because the thin, dry air gives clear skies on most nights of the year. "
         "Astronomers work in shifts through the night and sleep in dormitories cut into the rock below the telescopes.",
         "Wind turbines convert the kinetic energy of moving air into electricity. Longer blades sweep a larger area and capture "
         "more energy, which is why modern turbines have grown steadily taller since the first commercial farms were built.",
         "The canal was dug by hand over eleven years and carried coal from the inland mines to the port until the railway "
         "arrived. Today its towpath is a cycling route and the old lock-keepers' cottages are rented to holidaymakers.",
         "Lichens are partnerships between a fungus and an alga or cyanobacterium. The fungus provides shelter and minerals, the "
         "partner provides sugars from photosynthesis, and together they colonise bare rock where neither could live alone.",
         "The town's covered market dates from 1824 and still opens six days a week. Stalls sell cheese, cut flowers and fish "
         "landed that morning, and on Saturdays a second-hand book market fills the square outside.",
         "A tide gauge records the height of the sea against a fixed mark every few minutes. Decades of such records, corrected "
         "for the slow movement of the land itself, are how scientists measure the rise of global sea level.",
         "The school was founded by a merchant's widow to teach reading and arithmetic to the children of dock workers. Its "
         "first building still stands beside the church, though the classrooms moved to a modern block in the 1970s.",
         "Sheepdogs are trained with a small set of whistled commands that tell the dog to move left, move right, stop or walk "
         "on. A good dog reads the flock as much as the handler and anticipates where the sheep will try to break.",
         "The reservoir supplies water to three towns and was created by damming a narrow valley. The flooded village below "
         "it reappears in dry summers, when the tops of the church tower and the old bridge rise above the surface.",
         "Printing with movable type spread across Europe within fifty years of its introduction. A press could produce in a "
         "day what a scribe copied in months, and the price of books fell until ordinary households could own a few."]
INSTRUCTIONS = ["Summarise the following paragraph in one sentence.", "Translate the following paragraph into French.",
                "List the three main facts in the following paragraph.", "Rewrite the following paragraph for a ten-year-old.",
                "Identify the topic sentence of the following paragraph.", "Extract every date mentioned in the following paragraph."]
PARA_PREFIX = ["", "Text: ", "Passage: ", "Excerpt: ", "Paragraph: ", "Source: ", "Extract: ", "Reading: ", "Note: ", "Background: "]

QUESTIONS = ["What is the capital of France?", "Which planet is closest to the sun?", "Who wrote Hamlet?", "What is the boiling point of water in Celsius?",
             "Which ocean lies between Europe and America?", "What gas do plants absorb from the air?", "Which metal is liquid at room temperature?",
             "Who painted the Mona Lisa?", "What is the largest mammal?", "Which language is spoken in Brazil?", "How many legs does a spider have?",
             "What is the chemical symbol for gold?", "Which continent is Kenya in?", "What is the square root of 81?", "Who discovered penicillin?",
             "What is the longest river in Africa?", "What is the capital of Japan?", "Which planet is known as the red planet?",
             "Who painted The Starry Night?", "What is the freezing point of water in Celsius?", "Which ocean is the largest?",
             "What gas do humans breathe out?", "Which metal is the best conductor of electricity?", "Who wrote Pride and Prejudice?",
             "What is the smallest prime number?", "Which language is spoken in Austria?", "How many sides does a hexagon have?",
             "What is the chemical symbol for sodium?", "Which continent is Peru in?", "What is the cube of 3?", "Who invented the telephone?",
             "What is the tallest mountain on Earth?"]
ONE_WORD = ["Answer with one word.", "Reply in a single word.", "Give a one-word answer.", "One word only, please.",
            "Respond with a single word.", "Keep the answer to one word."]
FULL = ["Answer in a full sentence.", "Reply with a complete sentence.", "Give your answer as a full sentence.", "Please answer in one complete sentence.",
        "Respond with a whole sentence.", "Write the answer as a full sentence."]

FACTS: list[Fact] = [
    Fact("rb_meta_question_type_3", "META", "What kind of question is this?", "", "", "This is a {X} question.", sided="kway",
         classes=tuple(Q_TYPES), ground_truth="the frame family (why / when / how many) over the same events", balanced_factors=("frame",)),
    Fact("rb_meta_why_vs_when", "META", "Is this a 'why' question or a 'when' question?", "a why question", "a when question",
         "This is {X}.", jlens_pos="why", jlens_neg="when", ground_truth="frame family", balanced_factors=("frame",)),
    Fact("rb_meta_instruction_present", "META", "Does the text contain an instruction about what to do with the paragraph?",
         "contains an instruction", "contains no instruction", "The text {X}.", jlens_pos="instruction", jlens_neg="none",
         ground_truth="an INSTRUCTIONS line precedes the paragraph or not (same paragraph pool)", balanced_factors=("paragraph",)),
    Fact("rb_meta_answer_format", "META", "What answer format does the text ask for?", "one word", "a full sentence",
         "The requested answer format is {X}.", jlens_pos="word", jlens_neg="sentence",
         ground_truth="the format sentence appended to the same question pool", balanced_factors=("question",)),
]


def _q(rng, frame: str) -> str:
    e, ep = rng.choice(EVENTS)
    return frame.format(E=e, Ep=ep)


def build(seed: int) -> dict[str, list[Draft]]:
    out: dict[str, list[Draft]] = {}
    seen: set[str] = set()
    rng = rng_for(seed, "rb_meta_question_type_3")
    n = 3 * 96
    types = balanced_levels(Q_TYPES, n, rng)
    frames = balanced_levels([0, 1, 2], n, rng)
    kway = []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: r.choice(Q_PREFIX) + _q(r, Q_FRAMES[types[i]][frames[i]]), seen)
        kway.append(Draft(text, Q_TYPES.index(types[i]), types[i], None, {"frame": frames[i], "ground_truth": types[i]}))
    out["rb_meta_question_type_3"] = kway
    rng = rng_for(seed, "rb_meta_why_vs_when")
    n = 288   # review fix item 5: 144 test items (was 66)
    pos = balanced_bools(n, rng)
    frames = balanced_levels([0, 1, 2], n, rng)
    drafts = []
    for i in range(n):
        t = "why" if pos[i] else "when"
        text = fresh(rng, lambda r, i=i, t=t: r.choice(Q_PREFIX) + _q(r, Q_FRAMES[t][frames[i]]), seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "a why question" if pos[i] else "a when question", None, {"frame": frames[i], "ground_truth": t}))
    out["rb_meta_why_vs_when"] = drafts

    rng = rng_for(seed, "rb_meta_instruction_present")
    n = 256   # the negative class has 16 paragraphs x 10 prefixes = 160 distinct texts: label and paragraph assigned jointly
    cells = balanced_levels([(pi, lab) for pi in range(len(PARAS)) for lab in (True, False)], n, rng)
    paras = [c[0] for c in cells]
    pos = [c[1] for c in cells]
    seen2, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            body = r.choice(PARA_PREFIX) + PARAS[paras[i]]
            return (r.choice(INSTRUCTIONS) + "\n\n" + body) if pos[i] else body
        text = fresh(rng, mk, seen2)
        drafts.append(Draft(text, 1 if pos[i] else 0, "contains an instruction" if pos[i] else "contains no instruction", None,
                            {"paragraph": paras[i], "ground_truth": pos[i]}))
    out["rb_meta_instruction_present"] = drafts

    rng = rng_for(seed, "rb_meta_answer_format")
    n = 256   # question and label assigned jointly: 4 items per (question, label) cell, 6 format sentences per cell (32 questions)
    cells = balanced_levels([(qi, lab) for qi in range(len(QUESTIONS)) for lab in (True, False)], n, rng)
    qs = [c[0] for c in cells]
    pos = [c[1] for c in cells]
    seen3, drafts = set(), []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: QUESTIONS[qs[i]] + " " + r.choice(ONE_WORD if pos[i] else FULL), seen3)
        drafts.append(Draft(text, 1 if pos[i] else 0, "one word" if pos[i] else "a full sentence", None, {"question": qs[i], "ground_truth": pos[i]}))
    out["rb_meta_answer_format"] = drafts
    return out
