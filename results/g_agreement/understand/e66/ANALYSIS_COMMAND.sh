#!/bin/sh
set -eu
cd '/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree'
exec '/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python' -m projects.g_agreement.understand.e66.analyze_once --spec '/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/results/g_agreement/understand/e66/ANALYSIS_SPEC.json' --integrator-post-judging
