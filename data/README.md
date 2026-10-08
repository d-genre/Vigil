# VIGIL — DATASETS & ARTIFACTS DIRECTORY

This directory contains raw and processed dataset files for model training, testing, and evaluation.

---

## Directory Structure

```
data/
├── raw/        <- Original PaySim and synthetic transaction CSVs (git-ignored)
└── processed/  <- Preprocessed feature tables and split matrices (git-ignored)
```

---

## Data Hygiene & Git Rules

1. **DO NOT COMMIT DATASETS TO GIT**: All contents of `data/raw/` and `data/processed/` are explicitly ignored by `.gitignore`.
2. **PaySim Dataset**: Download the PaySim synthetic financial dataset locally during Phase 1 for ML training. Do not check it into version control.
3. **Synthetic Generator**: Attack vectors and normal synthetic transaction streams will be generated dynamically during simulation runs.
