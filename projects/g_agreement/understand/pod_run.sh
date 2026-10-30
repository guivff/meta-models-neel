#!/usr/bin/env bash
# Integrator invokes this on an assigned pod. No provisioning/SSH/downloads.
set -euo pipefail
if [ "$#" -ne 5 ]; then
  echo 'usage: pod_run.sh E3|E4 INPUT_PARENT OUT ASSETS ASSIGNMENT' >&2
  exit 2
fi
experiment="$1"
inputs="$2"
out="$3"
assets="$4"
assignment="$5"
case "$experiment" in
  E3) phases=(olens nla jlens) ;;
  E4) phases=(olens nla jlens target) ;;
  *) echo 'experiment must be E3 or E4' >&2; exit 2 ;;
esac
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
runner=(python -m projects.g_agreement.understand.run)
common_args=(--experiment "$experiment" --inputs "$inputs" --out "$out" --assignment "$assignment")
seal_on_exit() {
  result=$?
  trap - EXIT
  if ! "${runner[@]}" seal "${common_args[@]}"; then
    echo 'Sealing incomplete: pull preserved files and reconcile accounting locally; do not rerun GPU phases.' >&2
    result=1
  fi
  exit "$result"
}
trap seal_on_exit EXIT
for phase in "${phases[@]}"; do
  "${runner[@]}" calibrate "${common_args[@]}" --phase "$phase" --assets "$assets"
done
"${runner[@]}" gate "${common_args[@]}"
for phase in "${phases[@]}"; do
  "${runner[@]}" collect "${common_args[@]}" --phase "$phase" --assets "$assets"
done
