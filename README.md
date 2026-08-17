# 🤖 Replica-Pro: Multi-Agent Orchestrator

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI](https://github.com/bablu-builds/replica-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/bablu-builds/replica-pro/actions)

> **One command to rule them all.** Break any project idea into 4 parallel tasks, assign them to multiple Replit agents, and auto-merge everything into a GitHub repo using LLMs (OpenAI/DeepSeek/Kimi/GLM).

---

## 🚀 Quick Start (30 Seconds)

```bash
git clone https://github.com/bablu-builds/replica-pro.git
cd replica-pro/replica-pro
pip install -e '.[dev]'
cp .env.example .env

# Run in Mock Mode (No credentials needed!)
RMAO_MODE=mock RMAO_LLM_PROVIDER=fake rmao run "Build a Todo App" --tasks 3
