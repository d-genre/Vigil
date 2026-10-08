# VIGIL — CONTRIBUTING & GIT WORKFLOW

This document defines the team collaboration standards, Git branching strategy, and pull request procedures for the Vigil hackathon repository.

---

## 1. Git Branching Strategy

To enable four team members (and their AI coding agents) to work in parallel without merge conflicts, development follows a strict feature-branch model.

```
main (DEMO-SAFE & ALWAYS STABLE)
  │
  ├── feature/ml           (Member 1 — ML & Datasets)
  ├── feature/fraud-graph   (Member 2 — Fraud Patterns & Graph)
  ├── feature/frontend      (Member 3 — React Dashboard)
  └── feature/backend       (Member 4 — FastAPI & LangGraph Integration)
```

### Branch Rules:
1. **`main` is Demo-Safe**: The `main` branch must build and run at all times. Direct commits to `main` are strictly prohibited.
2. **Feature Branches**: Each member works strictly on their assigned branch:
   - Member 1: `feature/ml`
   - Member 2: `feature/fraud-graph`
   - Member 3: `feature/frontend`
   - Member 4: `feature/backend`
3. **No Cross-Pushes**: Do not push code to another member's feature branch unless requested.

---

## 2. Daily Integration & PR Workflow

1. **Pull Latest Main**: Before starting work or initiating major integration, pull or rebase the latest `main` into your feature branch:
   ```bash
   git checkout feature/<your-module>
   git fetch origin
   git rebase origin/main
   ```
2. **Local Testing**: Run local unit tests (`pytest`) and verify your code before committing.
3. **Logical Commits**: Commit code in clean, logical increments with descriptive commit messages (e.g., `feat(ml): add CatBoost prediction wrapper`).
4. **Pull Requests (PR)**: Open a PR from your feature branch to `main`. At least one team member must review and approve before merging.
5. **No Force-Push**: Never force-push (`git push --force`) to `main` or shared branches.

---

## 3. Environment & Security Hygiene

* **Secrets**: Never commit `.env`, API keys, or database credentials. Always update `.env.example` when introducing new environment configuration keys.
* **Large Datasets & Models**: Never commit raw CSV files, zip archives, SQLite databases (`*.db`), model binaries (`*.cbm`), or vector stores (`*.faiss`). Keep them in `data/` which is ignored by Git.

---

## 4. AI Agent Governance in Development Workflow

> **AI agents are allowed to implement code autonomously inside their assigned ownership boundary, but architecture, shared contracts, and interfaces are controlled by the team.**

- AI agents operating on behalf of a team member must strictly restrict their edits to that member's owned directory.
- Shared contracts in `schemas/` and `docs/` cannot be altered autonomously by an agent.
- Any conflict between module boundaries must be escalated to the human team lead.
