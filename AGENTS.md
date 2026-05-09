Welcome. You are operating as an autonomous engineering agent within this repository.

**CRITICAL RULE:** Do not assume context. This file is your map, not an encyclopedia. The system of record for this project is the `docs/` directory. Rely on progressive disclosure: locate the specific context you need in the designated files before executing any task.

## 1. Context Navigation & Access

Use the following structured references to understand the system state before writing or modifying code.

* **Top-Level Entry:** [ARCHITECTURE.md](https://www.google.com/search?q=./ARCHITECTURE.md) (Domain models, package layering, and strict dependencies).
* **Design & Principles:** [DESIGN.md](https://www.google.com/search?q=./DESIGN.md) and `docs/design-docs/core-beliefs.md`.
* **Active Plans & State:** `docs/exec-plans/active/` (for current task progression) and `docs/exec-plans/tech-debt-tracker.md`.
* **Product Specifications:** `docs/product-specs/` (for translating intent into verifiable acceptance criteria).
* **Generated Schemas:** `docs/generated/db-schema.md` (always consult this for database models and data shapes).

## 2. Architectural Boundaries

To maintain high-impact velocity without decay, we enforce a rigid, layered domain architecture. You must respect these constraints and never bypass layers.

* **Forward-Only Dependencies:** Flow is strictly Types → Config → Repo → Service → Runtime → UI.
* **Frontend/Backend Segregation:** Refer strictly to [FRONTEND.md]() for Next.js and React component architecture. Python backend logic and processing pipelines must remain strictly isolated.
* **Agentic Orchestration:** Workflows built via n8n or autonomous graph logic (e.g., LangGraph) must be encapsulated within the `Service` and `Runtime` layers. State management for RAG or agentic loops must not bleed into client-facing UI components.
* **Cross-Cutting Concerns:** External connectors (such as Azure AI Foundry or AWS services), authentication, and telemetry must be injected through a single explicit `Providers` interface.

## 3. Design & Implementation "Taste"

We optimize for agent legibility, mechanical enforcement, and code consistency over human stylistic preferences:

* **No "YOLO" Data Probing:** Validate all data boundaries. Rely on typed SDKs and explicit schemas so subsequent agent runs do not accidentally build on guessed or inferred shapes.
* **Internalized Abstractions:** Prefer highly composable and API-stable technologies. If a public library is too opaque, implement a cleanly scoped, tested version in-repo so it can be mechanically reasoned about.
* **Continuous Observability:** Emit structured logs and metrics for all critical paths. Utilize local observability stacks to dynamically validate latency and reliability during task execution.

## 4. Execution Protocol

1. **Plan:** Read relevant `docs/` artifacts. Create a lightweight execution plan in `docs/exec-plans/active/` if modifying core domains.
2. **Execute:** Write application code, infrastructure, and tests simultaneously.
3. **Verify:** You are responsible for QA. Use headless runtime tools to validate Next.js UI behavior and verify Python outputs mechanically. Ensure your code passes all structural linters.
4. **Document:** If you make a design decision, update `docs/design-docs/`. If you leave a known issue, immediately update `docs/exec-plans/tech-debt-tracker.md`. Code changes must be self-documenting for future agents.

---

### Key Takeaways for Starting Your Project

* **Mechanical Enforcement:** As noted by Harness Engineering, document guidelines aren't enough. Build custom linters to enforce the `ARCHITECTURE.md` boundaries (like ensuring UI components never directly call a backend provider).
* **Doc Gardening:** Set up an automated agent run that routinely scans your `docs/` folder to flag or update stale schema documentation and completed execution plans. This functions as a continuous "garbage collection" for context decay.
* **No Human Code Philosophy:** Transition from writing code to designing the environment. Your primary focus as the architect is specifying intent, configuring the CI/CD pipeline, and defining the bounds so that the agent has a fully legible environment to execute within.