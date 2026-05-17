# RAG Eval Case Builder Plan

## Goal

Add a notebook-first evaluation preparation surface for the two target annual reports in `reports/` so the next retrieval-eval step can test whether the vector database can answer financially important questions grounded in the source documents.

## Scope

- Reuse Azure Document Intelligence markdown extraction already present in the repo.
- Save raw markdown for `bandhan_annual_report.pdf` and `emcure_annual_report.pdf`.
- Build 10 broad markdown coverage windows across the two reports.
- Curate 10 financially important Q/A eval cases for later vector DB scoring.
- Keep the notebook thin by moving reusable behavior into a service module plus a checked-in eval dataset.

## Deliverables

- `market_analyst/services/rag_eval.py`
- `data/evals/fundamental_rag_eval_cases.json`
- `notebooks/09_rag_eval_case_builder.ipynb`
- provider/runtime fixes required for the notebook to run in the current Windows environment

## Verification

- Generate the notebook file deterministically from `scripts/create_rag_eval_notebook.py`.
- Run targeted tests for the provider override parsing and the eval helper module.
