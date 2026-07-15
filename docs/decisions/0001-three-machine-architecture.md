# ADR-0001: Three-machine architecture

**Context.** Development, 24/7 inference, and GPU training have different
hardware needs, and a solo dev owns exactly one of each class of machine.

**Decision.** The laptop develops and runs tests/dry-run evals; the Mac
Studio (M4 Max, 128GB) runs inference (llama.cpp `llama-server`, Ollama/LM
Studio as fallbacks), the Mindcraft bot, trajectory logging, and judge-model
scoring; RunPod rents CUDA for training only. One repo; git is the sync
layer for code.

**Consequences.** Data and weights never enter git — they stay on the Studio
(sync strategy is a backlog item). Everything must run offline on the laptop
against mocks; provider-specific code stays behind the OpenAI-compatible
client so serving stacks are swappable config.
