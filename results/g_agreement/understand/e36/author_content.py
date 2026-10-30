"""Definition-only semantic item author for E36 v2.

Input packet SHA256: 2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c
Only the definition packet was consulted. Families 0:6 are dev; 6:12 test.
"""
from __future__ import annotations

import json

FEATURES = (
    "json_status", "latex_role", "latex_subject", "list_priority", "list_topic",
    "prose_sentiment", "prose_topic", "python_error", "table_status",
)

_EVENTS = (
    "the afternoon workshop", "the weekend exhibition", "the community concert",
    "the evening performance", "the guided museum visit", "the local craft fair",
    "the neighborhood festival",
)
_TIMES = (
    "At the start of the day", "During the afternoon visit", "Near the end of the morning",
    "On the second inspection", "During the weekly observation", "Before the evening arrived",
    "When the team returned",
)
_NAMES = ("Mira", "Nora", "Lena", "Tara", "Rosa", "Anna", "Clara")
_PLACES = (
    "the library desk", "the archive room", "the reception booth", "the meeting suite",
    "the dispatch counter", "the service window", "the registration table",
)

_SENTIMENT = (
    (
        "I came away from {x} feeling delighted with the whole experience. The care and attention were excellent, and each part gave me another reason to feel pleased about attending.",
        "I came away from {x} feeling disgusted with the whole experience. The care and attention were awful, and each part gave me another reason to feel disappointed about attending.",
    ),
    (
        "Anyone considering {x} has my enthusiastic recommendation. Its thoughtful organization and charming atmosphere made the visit enjoyable, and I would gladly encourage a friend to share such a wonderful experience.",
        "Anyone considering {x} has my emphatic warning. Its careless organization and unpleasant atmosphere made the visit miserable, and I would firmly discourage a friend from enduring such a dreadful experience.",
    ),
    (
        "My expectations for {x} were exceeded in a delightful way. What unfolded was impressive from the opening moments onward, leaving me grateful for an experience that felt thoroughly rewarding.",
        "My expectations for {x} were shattered in a distressing way. What unfolded was appalling from the opening moments onward, leaving me resentful about an experience that felt thoroughly disappointing.",
    ),
    (
        "The people running {x} handled every detail with admirable care. Their considerate manner and excellent execution created an atmosphere I found welcoming, and the result deserves sincere praise.",
        "The people running {x} handled every detail with shocking carelessness. Their dismissive manner and terrible execution created an atmosphere I found alienating, and the result deserves serious criticism.",
    ),
    (
        "For the time I spent at {x}, I received something truly worthwhile. The quality was superb throughout, and reflecting on the experience brings a satisfying sense of pleasure and appreciation.",
        "For the time I spent at {x}, I received something truly worthless. The quality was abysmal throughout, and reflecting on the experience brings a troubling sense of frustration and regret.",
    ),
    (
        "Thinking back on {x}, I keep remembering moments of delight. The experience had a lovely warmth that stayed with me afterward, and even its small details now seem pleasantly memorable.",
        "Thinking back on {x}, I keep remembering moments of misery. The experience had a bitter coldness that stayed with me afterward, and even its small details now seem painfully unpleasant.",
    ),
    (
        "Whenever a detail needed attention during {x}, the response was helpful and reassuring. That dependable care made the experience feel satisfying, and I left with genuine admiration for the excellent work.",
        "Whenever a detail needed attention during {x}, the response was unhelpful and upsetting. That careless treatment made the experience feel frustrating, and I left with deep contempt for the dreadful work.",
    ),
    (
        "From the first impression through the final moments, {x} was a pleasure. Its engaging character remained consistent throughout, and I found the whole experience refreshing, delightful, and thoroughly enjoyable.",
        "From the first impression through the final moments, {x} was a disappointment. Its tedious character remained consistent throughout, and I found the whole experience exhausting, distressing, and thoroughly unpleasant.",
    ),
    (
        "Both the presentation and the atmosphere at {x} impressed me. The thoughtful details worked beautifully together, giving the experience a pleasing coherence that made it feel polished and successful.",
        "Both the presentation and the atmosphere at {x} disappointed me. The clumsy details worked badly together, giving the experience an irritating disorder that made it feel sloppy and unsuccessful.",
    ),
    (
        "After {x}, my mood was brighter and my spirits felt lifted. I valued the experience for its generous warmth, and the lasting impression it created was one of happiness and contentment.",
        "After {x}, my mood was darker and my spirits felt crushed. I resented the experience for its relentless dreariness, and the lasting impression it created was one of sadness and discontent.",
    ),
    (
        "I feel grateful that I attended {x}. The experience offered so much to appreciate that describing it brings back a cheerful feeling, along with sincere affection for its wonderful atmosphere.",
        "I feel regretful that I attended {x}. The experience offered so much to dislike that describing it brings back a gloomy feeling, along with lasting resentment toward its horrible atmosphere.",
    ),
    (
        "I would happily return to {x} for another visit. Remembering how enjoyable and rewarding it felt makes that prospect appealing, and I regard the entire experience with enthusiastic approval.",
        "I would reluctantly return to {x} for another visit. Remembering how unpleasant and disappointing it felt makes that prospect depressing, and I regard the entire experience with emphatic disapproval.",
    ),
)

_TOPIC = (
    (
        "{x}, the gardeners loosened soil around the vegetable seedlings and worked compost into the planting beds. They checked that the roots had enough room to spread before watering each young plant along the newly cultivated row.",
        "{x}, the researchers sampled seawater around the coral colonies and measured salinity above the ocean floor. They checked that the currents had enough strength to circulate before recording each new reading along the submerged reef.",
    ),
    (
        "{x}, a gardener explained how buried seeds absorb moisture before their shoots emerge from the soil. The discussion followed germination through the first leaves, then described the care needed to establish seedlings in a garden bed.",
        "{x}, a researcher explained how coastal tides move seawater before their currents reach the open ocean. The discussion followed circulation through the shallow reefs, then described the forces needed to carry plankton across a marine shelf.",
    ),
    (
        "{x}, measurements showed that the garden soil needed additional compost for the vegetable crop. The gardener compared moisture at several planting depths and adjusted the irrigation schedule so the growing roots would receive water throughout the week.",
        "{x}, measurements showed that the ocean water carried additional salt near the continental shelf. The researcher compared salinity at several sampling depths and mapped the tidal circulation so the moving currents could be followed throughout the week.",
    ),
    (
        "{x}, the gardener pruned the rose bushes by cutting stems above outward-facing buds. Removing crowded branches let sunlight reach the leaves, while careful spacing gave each flowering plant more room within the cultivated border.",
        "{x}, the diver surveyed the coral reef by tracing ridges above the sandy seabed. Mapping submerged channels showed where seawater reached the lagoon, while changing tides carried marine organisms farther along the underwater coastal slope.",
    ),
    (
        "{x}, aphids were found feeding on the garden beans and curling their tender leaves. The gardener inspected the undersides of the foliage, removed damaged shoots, and planned further checks to protect the developing vegetable plants.",
        "{x}, plankton were found drifting above the ocean reef and feeding its marine animals. The researcher inspected the movement of the seawater, measured tidal currents, and planned further samples to describe the surrounding saltwater ecosystem.",
    ),
    (
        "{x}, the vegetable harvest began with ripe tomatoes from the garden trellis. The gardeners examined each plant, picked the mature fruit, and left the smaller tomatoes on their vines to continue growing in the cultivated beds.",
        "{x}, the ocean survey began with migrating fish above the offshore reef. The researchers examined each shoal, tracked the marine animals, and followed the smaller fish through the seawater to observe their movement across the continental shelf.",
    ),
    (
        "{x}, seedlings were transplanted from their pots into a prepared garden bed. The gardener spread each root system gently, pressed soil around the stems, and watered the plants to help them settle into their new growing space.",
        "{x}, seawater was transported from the surface into a deeper ocean layer. The researcher traced each sinking current carefully, measured salinity below the waves, and sampled the water to describe its circulation through the surrounding marine basin.",
    ),
    (
        "{x}, mulch was spread over the garden soil between rows of vegetables. This covering reduced evaporation around the roots and restrained weeds, allowing the planted crops to keep growing with a more consistent supply of moisture.",
        "{x}, sediment was spread over the ocean floor between ridges of coral. This movement changed conditions around the reef and buried shells, allowing the marine survey to reveal how tidal currents reshape the submerged coastal habitat.",
    ),
    (
        "{x}, greenhouse vents were adjusted to control conditions for the growing seedlings. The gardener inspected the tomato plants, checked moisture in their potting soil, and prepared the next group of seeds for planting in nursery trays.",
        "{x}, underwater sensors were adjusted to record conditions in the moving seawater. The researcher inspected the coral colonies, checked salinity in their marine habitat, and prepared the next series of samples for tracking offshore ocean currents.",
    ),
    (
        "{x}, the garden plan moved beans into beds that had previously grown cabbages. Rotating vegetable crops helped manage the cultivated soil, and the gardener marked where the next planting of roots and leafy greens would take place.",
        "{x}, the ocean map traced currents into regions that had previously held cold seawater. Following coastal upwelling helped explain the marine nutrients, and the researcher marked where the next movement of plankton and migrating fish would take place.",
    ),
    (
        "{x}, the gardener tested whether a shaded border could support flowering plants. Observations of sunlight, soil texture, and drainage guided the choice of seedlings, while the planting layout kept taller stems from covering the smaller garden flowers.",
        "{x}, the researcher tested whether a shallow reef could support marine organisms. Observations of tides, seawater temperature, and salinity guided the choice of samples, while the ocean survey traced stronger currents past the smaller submerged coral colonies.",
    ),
    (
        "{x}, a garden journal linked the progress of seedlings to regular watering and soil care. Its entries described germination, leaf growth, and the preparation of compost, ending with plans for planting the next vegetable crop in spring.",
        "{x}, an ocean journal linked the movement of plankton to changing tides and seawater flow. Its entries described salinity, coral growth, and the circulation of currents, ending with plans for surveying the next marine habitat along the coast.",
    ),
)

_PRIORITY = (
    ("Restore network access at {x} immediately; the outage is blocking active work and must be fixed now to prevent further disruption.", "Review network access at {x} during scheduled maintenance; the connection is operating normally and can be checked at the next regular inspection."),
    ("Call the technician for {x} right now; the equipment failure requires immediate attention before the service interruption spreads to the next station.", "Call the technician for {x} next month; the equipment review is a routine appointment within the normal schedule for the next inspection."),
    ("Send the corrected access instructions to {x} within minutes; people are currently locked out and need the correction immediately to resume their work.", "Send the updated access instructions to {x} next week; people are currently working normally and can read the revision during their regular briefing."),
    ("Replace the damaged cable at {x} without delay; its failure is stopping the current service and demands immediate action from the available technician.", "Replace the aging cable at {x} during routine maintenance; its condition is stable during normal service and allows scheduling with the available technician."),
    ("Check the warning indicator at {x} immediately; the alert signals an imminent shutdown and needs attention now before the operating session is interrupted.", "Check the status indicator at {x} during the regular inspection; the display signals normal operation and needs review only at the scheduled service interval."),
    ("Escalate the unresolved access failure at {x} now; an active outage is affecting the current shift and requires a response within the next minutes.", "Review the previous access report at {x} later; a routine audit is covering the completed shift and allows a response during the next monthly meeting."),
    ("Order replacement supplies for {x} immediately; stock has run out during active service, so replenishment must happen today before the counter can reopen.", "Order replacement supplies for {x} at the regular review; stock remains sufficient during normal service, so replenishment can follow the usual monthly purchasing cycle."),
    ("Assign a replacement operator to {x} right away; the vacant position is blocking service now and must be covered before the waiting line grows.", "Assign a replacement operator to {x} next month; the planned rotation is part of normal scheduling and can be arranged during the regular staffing review."),
    ("Publish the revised opening notice for {x} immediately; a sudden closure is affecting visitors now and the notice must reach them within the next minutes.", "Publish the seasonal opening notice for {x} next week; the planned schedule is following normal arrangements and the notice can join the regular monthly update."),
    ("Activate the backup terminal at {x} now; the main terminal has failed during service and an immediate replacement is needed to clear the waiting queue.", "Inspect the backup terminal at {x} during routine maintenance; the main terminal is working during service and a scheduled review fits the usual monthly equipment check."),
    ("Update the access credentials at {x} immediately; the current credentials are blocking entry and must be corrected now so the waiting staff can begin work.", "Update the access documentation at {x} during the regular review; the current credentials allow entry and the planned revision can wait until the next monthly audit."),
    ("Clear the blocked request queue at {x} within minutes; active service is stalled and the obstruction needs immediate attention before further requests can be processed.", "Review the completed request queue at {x} next month; normal service is continuing and the archive needs routine attention during the next scheduled recordkeeping session."),
)

_LIST_TOPIC = (
    ("For {x}, reserve train tickets for the trip and compare departure times before adding the chosen connection to the travel itinerary.", "For {x}, reserve library sessions for the course and compare revision times before adding the chosen exercises to the study timetable."),
    ("For {x}, check the passport and visa requirements, then list the travel documents needed to cross the border on the planned journey.", "For {x}, check the syllabus and exam requirements, then list the study materials needed to revise the chapters for the planned assessment."),
    ("For {x}, compare hotel locations near the destination and choose accommodation that leaves enough time to reach the airport before the return flight.", "For {x}, compare library sessions near the exam date and choose revision periods that leave enough time to practice the exercises before the final assessment."),
    ("For {x}, divide the holiday budget between accommodation, transport, and meals, then reserve enough money for the remaining days of the trip.", "For {x}, divide the study schedule between reading, revision, and exercises, then reserve enough time for the remaining chapters of the course."),
    ("For {x}, pack the suitcase according to the destination weather and prepare a travel checklist for the luggage needed during the journey.", "For {x}, organize the notebooks according to the course syllabus and prepare a study checklist for the revision needed before the examination."),
    ("For {x}, map the route between cities and check each train connection so that the itinerary allows time to reach the next destination.", "For {x}, map the links between chapters and check each practice exercise so that the revision schedule allows time to master the next topic."),
    ("For {x}, arrange airport transport for the departure morning and confirm the flight time before setting the final schedule for the journey.", "For {x}, arrange library study for the revision morning and confirm the exam time before setting the final schedule for the assessment."),
    ("For {x}, research the destination attractions, select the places to visit, and build an itinerary that groups nearby sights on each travel day.", "For {x}, review the course objectives, select the chapters to revise, and build a timetable that groups related exercises on each study day."),
    ("For {x}, compare flight routes with train routes and record the travel time, ticket cost, and arrival point for each possible journey.", "For {x}, compare lecture notes with textbook chapters and record the revision time, practice questions, and learning goal for each possible study session."),
    ("For {x}, leave space in the travel itinerary for delayed transport and identify another train that could still reach the booked accommodation.", "For {x}, leave space in the revision timetable for difficult chapters and identify another exercise that could still reinforce the required course material."),
    ("For {x}, confirm the hotel reservation, save the boarding pass, and write the airport transfer details beside the first day of the travel itinerary.", "For {x}, confirm the library reservation, save the practice exam, and write the revision session details beside the first day of the study timetable."),
    ("For {x}, prepare a return journey checklist covering transport to the airport, the flight connection, and collection of luggage at the final destination.", "For {x}, prepare a final revision checklist covering review of the syllabus, the practice examination, and correction of exercises before the scheduled course assessment."),
)

_ROLE = (
    (r"For every even integer \(n\), the square \(n^2\) is divisible by four. Indeed, writing \(n=2k\) gives \(n^2=4k^2\), which establishes the claim for all such integers.", r"For the chosen even integer \(n=6\), calculate the square by writing \(6=2\cdot3\). Substitution gives \(6^2=4\cdot9=36\), so this worked calculation produces a multiple of four."),
    (r"If a real polynomial \(p\) has \(p(a)=0\), then \(x-a\) divides \(p(x)\). Polynomial division gives remainder \(p(a)\), proving the implication for every polynomial satisfying the hypothesis. The quotient is again a polynomial.", r"Take the polynomial \(p(x)=x^2-9\) and choose \(a=3\). Direct substitution gives \(p(3)=0\), and factoring the expression yields \((x-3)(x+3)\) for this particular polynomial."),
    (r"In any group, the equation \(ab=ac\) implies \(b=c\). Multiplication on the left by \(a^{-1}\), followed by associativity and the identity law, proves cancellation for arbitrary group elements.", r"In the additive group of integers, take the equation \(5+7=5+7\). Adding \(-5\) to both sides and simplifying gives \(7=7\), demonstrating cancellation for these particular group elements."),
    (r"For every pair of invertible matrices \(A,B\) of equal size, \((AB)^{-1}=B^{-1}A^{-1}\). Multiplying the proposed inverse on either side of \(AB\) gives the identity, establishing the formula. Thus the factor order is reversed.", r"For the chosen diagonal matrices \(A=2I\) and \(B=3I\), compute \(AB=6I\). Taking the inverse gives \((AB)^{-1}=I/6\), which also equals \((I/3)(I/2)\) in this calculation."),
    (r"Every finite arithmetic progression with first term \(a\), last term \(b\), and length \(n\) has sum \(n(a+b)/2\). Pairing terms from opposite ends proves this identity for arbitrary progression length. Each pair has the same sum.", r"Consider the arithmetic progression \(2,4,6,8\), whose first and last terms are \(2\) and \(8\). Pairing opposite terms gives \(10+10=20\), so this particular four-term progression has sum \(20\)."),
    (r"For every real number \(x\), one has \(x^2\geq0\). If \(x\) is nonnegative its square is nonnegative, and if \(x\) is negative the product of two negative factors is positive.", r"For the chosen real number \(x=-7\), evaluate its square explicitly. Multiplying \((-7)(-7)\) gives \(49\), because the two negative factors have a positive product in this numerical calculation."),
    (r"Any linear map sends the zero vector to the zero vector. From \(T(0)=T(0+0)=T(0)+T(0)\), subtraction establishes the claim for every linear map between vector spaces. This also fixes the additive identity.", r"Take the linear map \(T(x,y)=(2x,3y)\) and insert the zero vector. The computation \(T(0,0)=(2\cdot0,3\cdot0)=(0,0)\) determines the image in this particular case."),
    (r"For every differentiable function \(f\) and constant \(c\), the derivative of \(cf\) equals \(cf'\). Factoring \(c\) out of the difference quotient and taking the limit proves the rule. The constant does not depend on the increment.", r"Take the function \(f(x)=x^2\) and the constant \(c=3\). Differentiating \(3x^2\) gives \(6x\), which agrees with multiplying \(f'(x)=2x\) by three in this worked calculation."),
    (r"Every convergent real sequence is bounded. A tail has terms within one unit of its limit; combine that bound with the maximum absolute value of the finitely many earlier terms. Both bounds are finite, so their maximum is finite.", r"Consider the sequence \(a_n=1/n\) for positive integers \(n\). Its first terms are \(1,1/2,1/3\), and each term lies between zero and one, giving a concrete bound of one for this sequence."),
    (r"For any two finite sets \(A,B\), their union has size \(|A|+|B|-|A\cap B|\). Counting the common elements once instead of twice establishes the formula for arbitrary finite sets. The subtraction removes exactly the duplicated contribution.", r"Choose the finite sets \(A=\{1,2\}\) and \(B=\{2,3\}\). Their union is \(\{1,2,3\}\), so counting its elements gives \(3=2+2-1\) in this particular calculation."),
    (r"If integers \(a\) and \(b\) are both odd, their sum is even. Writing \(a=2r+1\) and \(b=2s+1\) yields \(a+b=2(r+s+1)\), proving the assertion in general.", r"Choose the odd integers \(a=5\) and \(b=9\), then compute their sum. Substituting these values gives \(a+b=5+9=14=2\cdot7\), so this particular sum is even."),
    (r"For any positive real numbers \(a,b\), the arithmetic mean is at least the geometric mean. Expanding \((\sqrt a-\sqrt b)^2\geq0\) gives \(a+b\geq2\sqrt{ab}\), proving the inequality.", r"Choose the positive real numbers \(a=4\) and \(b=9\). Their arithmetic mean is \((4+9)/2=6.5\), while their geometric mean is \(\sqrt{4\cdot9}=6\), as this numerical calculation shows."),
)

_SUBJECT = (
    (r"Factor the polynomial \(x^2-5x+6\) into \((x-2)(x-3)\). The coefficients determine two roots, and substituting either root makes the original polynomial vanish, linking the factorization to solutions of the algebraic equation.", r"Divide the triangle by drawing an altitude from its vertex to the opposite side. The resulting right triangles each contain a right angle, and their remaining angles sum to ninety degrees, linking the construction to the geometry of the figure. Its altitude meets the base perpendicularly."),
    (r"Solve the linear equations \(x+y=5\) and \(x-y=1\) by elimination. Adding the equations isolates the variable \(x\), and substitution then determines \(y\), giving an ordered pair that satisfies the entire algebraic system.", r"Construct the perpendicular bisector of a line segment by intersecting two circles of equal radius. Joining their intersection points produces a line through the midpoint, giving a geometric construction whose points are equally distant from the segment endpoints. Both arcs use the same compass opening."),
    (r"The matrix product is computed by multiplying rows by columns. Each resulting entry is a sum of products, and the matrix representation records how two linear transformations combine when they act on the same vector space.", r"The polygon area is computed by dividing the figure into triangles. Each resulting piece has a base and altitude, and the geometric decomposition records how several triangular regions combine when they occupy the same planar surface."),
    (r"A group operation combines two elements while preserving associativity. The identity element leaves every input unchanged, and each inverse cancels its corresponding element, providing the algebraic structure needed to manipulate products and solve group equations.", r"A circle construction joins two points while preserving a fixed radius. The central angle determines the intercepted arc, and each chord connects its corresponding endpoints, providing the geometric structure needed to compare lengths and locate inscribed angles."),
    (r"A basis expresses every vector as a linear combination of independent vectors. The coefficients are unique, and changing the basis transforms those coefficients through an invertible matrix, preserving the underlying algebraic relationships in the vector space.", r"A coordinate diagram expresses every point as a location relative to perpendicular axes. The distances are measured, and rotating the diagram transforms those positions through a rigid motion, preserving the underlying geometric relationships between angles and line segments."),
    (r"An eigenvector of a matrix keeps its direction under the associated linear transformation. Its eigenvalue supplies the scalar multiplier, so the equation \(Av=\lambda v\) turns the transformation into an algebraic relation between a matrix and a vector.", r"An angle bisector of a triangle divides its vertex angle into equal parts. Its intersection supplies a point on the opposite side, so the resulting construction turns the diagram into a geometric relation between side lengths and adjacent angles."),
    (r"Polynomial long division separates a dividend into a divisor times a quotient plus a remainder. Comparing coefficients determines each successive term, and the resulting identity supports algebraic simplification of rational expressions involving the original polynomials.", r"A tangent construction separates a circle from a line touching its circumference at one point. Drawing the radius determines a perpendicular angle, and the resulting diagram supports geometric calculation of distances involving the original circle and exterior point."),
    (r"The determinant detects whether a square matrix has an inverse. Expanding along a row reduces the calculation to smaller determinants, and a nonzero result ensures that the corresponding linear equations have a unique algebraic solution.", r"The diagonal detects how a quadrilateral can split into triangles. Drawing it between opposite vertices reduces the area calculation to smaller triangular regions, and their side lengths determine the corresponding geometric measurements within the original planar figure."),
    (r"A homomorphism preserves the operation between elements of two groups. Its kernel consists of elements mapped to the identity, and studying that subgroup explains how the mapping preserves algebraic structure while identifying some distinct input elements.", r"A reflection preserves the distance between points of two congruent figures. Its axis consists of points fixed by the transformation, and studying that line explains how the mapping preserves geometric shape while reversing the orientation of the figure."),
    (r"The quadratic formula expresses the roots in terms of a polynomial's coefficients. Completing the square derives the formula, and the discriminant determines whether the corresponding algebraic equation has two distinct real solutions, one repeated solution, or complex roots.", r"The cosine rule expresses a side length in terms of a triangle's other measurements. Dropping an altitude derives the formula, and the included angle determines how the corresponding geometric figure relates its three sides through the resulting squared distances."),
    (r"A recurrence defines each sequence term through an algebraic expression involving earlier terms. Substituting the initial values generates the next entries, while a closed formula can be checked by inserting it into the same symbolic recurrence relation.", r"A tessellation covers each planar region through a geometric arrangement involving repeated polygons. Matching the interior angles joins the next pieces, while a repeating pattern can be checked by inspecting the edges and vertices throughout the same tiled surface."),
    (r"An ideal is a subset of a ring closed under addition and multiplication by ring elements. Passing to the quotient groups elements into cosets, and arithmetic on those cosets yields an algebraic structure governed by the original ring operations.", r"A sphere is a surface whose points share a fixed distance from one center. Passing a plane through it produces a circle, and measurements on that circle yield a geometric description governed by the original radius and the plane's position."),
)

_PROGRAMS = (
    ("summarize", "    total = sum(values)\n    count = len(values)\n    detail = f\"batch {tag}: {count} entries total {total}\"", "ValueError"),
    ("normalize", "    cleaned = [str(value).strip() for value in values]\n    joined = ','.join(cleaned)\n    detail = f\"batch {tag}: normalized {joined}\"", "RuntimeError"),
    ("measure", "    widths = [len(str(value)) for value in values]\n    largest = max(widths, default=0)\n    detail = f\"batch {tag}: largest width {largest}\"", "ValueError"),
    ("enumerate_entries", "    indexed = list(enumerate(values))\n    preview = indexed[:3]\n    detail = f\"batch {tag}: indexed preview {preview}\"", "RuntimeError"),
    ("group_entries", "    counts = {}\n    for value in values:\n        key = str(value)\n        counts[key] = counts.get(key, 0) + 1\n    detail = f\"batch {tag}: counts {counts}\"", "ValueError"),
    ("order_entries", "    ordered = sorted(str(value) for value in values)\n    first = ordered[:2]\n    detail = f\"batch {tag}: opening entries {first}\"", "RuntimeError"),
    ("build_pairs", "    pairs = list(zip(values, values[1:]))\n    count = len(pairs)\n    detail = f\"batch {tag}: {count} adjacent pairs {pairs}\"", "ValueError"),
    ("split_entries", "    midpoint = len(values) // 2\n    left, right = values[:midpoint], values[midpoint:]\n    detail = f\"batch {tag}: partitions {left} and {right}\"", "RuntimeError"),
    ("collect_unique", "    unique = set(str(value) for value in values)\n    ordered = sorted(unique)\n    detail = f\"batch {tag}: distinct entries {ordered}\"", "ValueError"),
    ("make_lookup", "    lookup = {index: value for index, value in enumerate(values)}\n    keys = list(lookup)\n    detail = f\"batch {tag}: lookup keys {keys}\"", "RuntimeError"),
    ("reverse_entries", "    reversed_values = list(reversed(values))\n    preview = reversed_values[:4]\n    detail = f\"batch {tag}: reverse preview {preview}\"", "ValueError"),
    ("mark_positions", "    positions = [index for index, value in enumerate(values) if value is not None]\n    detail = f\"batch {tag}: populated positions {positions}\"", "RuntimeError"),
)


def _json_status(t: int, f: int, v: int) -> str:
    status = ("approved", "rejected")[v]
    n = f + 1
    records = (
        {"request": n, "checks": {"identity": True, "complete": True}, "decision": status},
        {"review": {"case": n, "votes": [1, 1, 0], "decision": status}},
        {"batches": [{"number": 0, "count": 2}, {"number": n, "count": 3, "decision": status}]},
        {"document": {"revision": n, "pages": [2, 4, 6]}, "audit": {"checked": True, "decision": status}},
        {"route": ["intake", "review"], "record": {"number": n, "reviewers": [{"present": True}], "decision": status}},
        {"limits": {"minimum": 2, "maximum": 9}, "observed": n, "decision": status},
        {"sessions": [{"number": n, "stages": [{"step": 1, "complete": True}, {"step": 2, "decision": status}]}]},
        {"revision": n, "evidence": {"attachments": ["form", "receipt"], "missing": []}, "decision": status},
        {"entries": {"current": {"sequence": n, "assessment": {"score": 8, "decision": status}}}},
        {"allocation": {"requested": n, "available": 10}, "review": [{"round": 1, "notes": None}, {"round": 2, "decision": status}]},
        {"checks": [{"name": "format", "passed": True}, {"name": "fields", "passed": True}], "case": n, "decision": status},
        {"ledger": {"page": n, "items": [{"reference": 12, "outcome": {"reviewed": True, "decision": status}}]}},
    )
    text = json.dumps(records[t], ensure_ascii=True, separators=(",", ":"))
    return text[:text.rfind('"' + status + '"') + len(status) + 2]


def _table_status(t: int, f: int, v: int) -> str:
    # Every schema has a genuinely different decision-cell position/row structure.
    specs = (
        (["Request", "Decision"], [f"R{f+1}", "pending"], 0),
        (["Batch", "Checks", "Decision"], [str(f+1), "3/3", "pending"], 1),
        (["Form", "Pages", "Signatures", "Decision"], [f"F{f+1}", "4", "2", "pending"], 2),
        (["Decision", "Revision", "Reviewer"], ["pending", str(f+1), _NAMES[f]], 3),
        (["Case", "Decision", "Amount", "Currency", "Owner"], [str(f+1), "pending", "120", "CHF", _NAMES[f]], 1),
        (["Record", "Complete", "Decision", "Archive"], [f"D{f+1}", "yes", "pending", "2026"], 0),
        (["Round", "Reviewers", "Votes", "Quorum", "Filed", "Decision"], [str(f+1), "5", "4", "yes", "yes", "pending"], 1),
        (["Item", "Requested", "Available", "Decision", "Unit"], [f"I{f+1}", "3", "8", "pending", "sets"], 2),
        (["Version", "Decision", "Timestamp"], [str(f+1), "pending", "09:30"], 0),
        (["Application", "Score", "Decision", "Panel", "Round", "Filed"], [f"A{f+1}", "8", "pending", "3", "2", "yes"], 3),
        (["Decision", "Packet", "Attachments", "Missing"], ["pending", str(f+1), "5", "0"], 1),
        (["Shipment", "Count", "Weight", "Checked", "Decision"], [f"S{f+1}", "6", "12", "yes", "pending"], 2),
    )
    headers, cells, prior = specs[t]
    decision_index = headers.index("Decision")
    alignment = [":---" if i % 3 == 0 else "---:" if i % 3 == 1 else ":---:" for i in range(len(headers))]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(alignment) + " |"]
    for row in range(prior):
        previous = list(cells)
        previous[decision_index] = "pending"
        # Different rows have observed checks/revisions, while status is unfinished.
        for i, cell in enumerate(previous):
            if i != decision_index and cell.isdigit():
                previous[i] = str(int(cell) + row + 1)
        lines.append("| " + " | ".join(previous) + " |")
    current = cells[:decision_index] + [("approved", "rejected")[v]]
    lines.append("| " + " | ".join(current))
    return "\n".join(lines)


def render(feature: str, template_index: int, filler_index: int, value_index: int) -> str:
    """Render a raw prefix, with no labels or template/filler identifiers added."""
    t, f, v = template_index, filler_index, value_index
    if feature not in FEATURES or not 0 <= t < 12 or not 0 <= f < 7 or v not in (0, 1):
        raise ValueError("unsupported feature or item coordinate")
    if feature == "prose_sentiment":
        return _SENTIMENT[t][v].format(x=_EVENTS[f])
    if feature == "prose_topic":
        return _TOPIC[t][v].format(x=_TIMES[f])
    if feature == "list_priority":
        return "- [ ] " + _PRIORITY[t][v].format(x=_PLACES[f])
    if feature == "list_topic":
        return "- [ ] " + _LIST_TOPIC[t][v].format(x=_NAMES[f])
    if feature == "latex_role":
        return r"\paragraph{Discussion " + _NAMES[f] + "}\n" + _ROLE[t][v]
    if feature == "latex_subject":
        return r"\paragraph{Notes for " + _NAMES[f] + "}\n" + _SUBJECT[t][v]
    if feature == "python_error":
        name, body, error = _PROGRAMS[t]
        prefix = f"def {name}(values):\n    tag = {_NAMES[f]!r}\n" + body
        # The computation and message are identical; only control transfer differs.
        return prefix + (f"\n    raise {error}(detail)" if v == 0 else "\n    return detail")
    if feature == "json_status":
        return _json_status(t, f, v)
    return _table_status(t, f, v)
