E84 revived data is derived from NVIDIA's **SWE-Zero OpenHands trajectories**,
revision 7b3cd106d00f60918e722d33a1d74bc67072a7ea, dataset license **CC BY 4.0**:
https://huggingface.co/datasets/nvidia/SWE-Zero-openhands-trajectories/tree/7b3cd106d00f60918e722d33a1d74bc67072a7ea

NVIDIA / Nikolai Ludwig, Wasi Uddin Ahmad, Somshubra Majumdar and Boris Ginsburg
(2026), *From SWE-ZERO to SWE-HERO: Execution-free to Execution-based Fine-tuning
for Software Engineering Agents*, arXiv:2604.01496.

Changes for E84: seeded issue-grouped selection of historical next-assistant
prefixes; native Qwen3.6 chat serialization/tokenization; CPU file-state labels
stored separately; a text-only baseline instruction is appended in its own arm.
No transcript command/patch/test is executed. These are synthetic trajectories;
labels denote transcript-reported state, not independent execution verification.
