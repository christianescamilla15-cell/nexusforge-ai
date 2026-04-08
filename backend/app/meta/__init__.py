"""Meta-orchestration layer — multi-LLM pipeline, predictive features, auto-specs.

Uses different local models for different phases:
- THINK: gemma4:27b / gemma3:4b (reasoning with thinking mode)
- BUILD: qwen2.5-coder:7b (structured code/JSON generation)
- DOCUMENT: llama3.1:8b (narrative text, documentation)
- VERIFY: deepseek-r1:8b (critical review with reasoning trace)
"""
