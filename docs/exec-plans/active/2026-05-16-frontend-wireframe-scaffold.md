# Frontend Wireframe Scaffold

## Goal

Add a clean Next.js/Tailwind/Lucide clickable scaffold for the market analyst workflow UI before real backend streaming routes are available.

## Scope

- Create a standalone `frontend/` Next.js app.
- Add the one-user workflow history page, new workflow form, stock-run detail page, supervisor timeline, vertically stacked collapsible agent panels, floating technical chart window, supervisor outcome panel, and contextual follow-up chat.
- Add company master and document library pages with plus-button creation flows backed by browser-local mock state until FastAPI contracts are finalized.
- Keep the first pass mock-driven through a local stream adapter that can later be replaced by FastAPI streaming transport.
- Update `specs.md` with the workflow-history, company master, document library, streaming visibility, and chat-session behavior.

## Verification

- Install frontend dependencies.
- Run the frontend production build.
- Start the dev server and inspect the primary workflow, company master, document library, and run detail screens.
