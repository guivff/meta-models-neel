# E33 operational re-pin — 2026-10-25, before any production score

Authority: §136 and Guiv's priority instruction; Integrator request 53bf46ad.
The 4.5 GPU-hour cap, all five doses, both prompts, all 25 rows, both frozen
phrasing pairs, all 84 test items per row, and every scientific gate are fixed.

Prior provider custody is 927.1 seconds: original attempt 406.6 seconds plus
three setup-only deployments of 251.6, 250.4 and 18.5 seconds. Reserve 928
seconds, rounding upward. The remaining 15,272 seconds are split into fixed
slot envelopes of 9,043 seconds for doses 0/.25/.5 and 6,229 seconds for .75/1.
This trims 521 seconds from the previous combined allocation.

Each envelope includes a 600-second allowance for SSH/setup loss. The live
pod's setup remains on its own provider clock. If a deployment fails before
science, Integrator may finalize its stopped-pod evidence in the common run
plan and deduct that loss from its slot's replacement allocation. The allowance
is inside the slot envelope and the total 16,200 seconds; it is not extra time.
No unbooked replacement, clock reset or scientific gate retry is authorized.

After reserving 600 seconds per slot, the remaining planning budget is split
3:2 with the number of doses. Each real pod must still pass its own complete
warmed forecast using its actual remaining custody. The planning allowance
does not replace timing measurements or permit dropping a path.
