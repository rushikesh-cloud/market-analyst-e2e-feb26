# Documentation Map

This directory is the working system of record for the market analyst engine. Start with `../specs.md`, then open the specific document that matches the current task.

## Current Focus

The first implementation phase is notebook-first validation. The notebooks are intended to make each capability visible, testable, and easy to change before the same reusable modules are exposed through a FastAPI backend.

Primary notebook references:

- `product-specs/notebook-first-validation.md` defines the notebook inventory, acceptance criteria, and validation scope.
- `design-docs/notebook-first-modularization.md` defines what belongs in reusable Python modules versus notebook cells.
- `generated/db-schema.md` records the planned database shapes used by RAG and analysis outputs.
- `exec-plans/active/2026-05-09-notebook-first-foundation.md` tracks the active setup work for the notebook phase.

## Documentation Areas

- `product-specs/`: product behavior, acceptance criteria, and milestone scope.
- `design-docs/`: design choices, modularity rules, and implementation principles.
- `exec-plans/`: active work plans and known technical debt.
- `generated/`: generated or mechanically maintained references such as database schema documentation.

## Update Rule

When a task changes product behavior, scope, acceptance criteria, or constraints, update `../specs.md` in the same change set and add or revise the relevant document in this directory.
