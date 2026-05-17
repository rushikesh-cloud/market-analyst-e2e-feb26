from __future__ import annotations

from pathlib import Path

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "09_rag_eval_case_builder.ipynb"


def build_notebook() -> nbf.NotebookNode:
    notebook = nbf.v4.new_notebook()
    notebook.metadata.update(
        {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.13",
            },
        }
    )
    notebook.cells = [
        nbf.v4.new_markdown_cell(
            "# 09 RAG Eval Case Builder\n\n"
            "Extract the two annual reports with Azure Document Intelligence, save the raw markdown, "
            "build 10 broad coverage windows, and review the curated 10-question financial eval set "
            "before wiring the questions into vector DB retrieval evaluation."
        ),
        nbf.v4.new_markdown_cell(
            "## Scope\n\n"
            "- Target reports: `bandhan_annual_report.pdf` and `emcure_annual_report.pdf`\n"
            "- Output markdown: `artifacts/rag_eval/raw_markdown/`\n"
            "- Output eval set: `data/evals/fundamental_rag_eval_cases.json`\n"
            "- This notebook does not score retrieval yet; it prepares the grounded question-answer cases."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import os\n"
            "import sys\n\n"
            "PROJECT_ROOT = Path.cwd()\n"
            "if PROJECT_ROOT.name == 'notebooks':\n"
            "    PROJECT_ROOT = PROJECT_ROOT.parent\n"
            "if str(PROJECT_ROOT) not in sys.path:\n"
            "    sys.path.insert(0, str(PROJECT_ROOT))\n\n"
            "from IPython.display import Markdown, display\n"
            "import pandas as pd\n\n"
            "from market_analyst.services.rag_eval import (\n"
            "    build_broad_eval_chunks,\n"
            "    build_eval_markdown_reports,\n"
            "    eval_cases_as_rows,\n"
            "    eval_chunks_as_rows,\n"
            "    export_markdown_reports,\n"
            "    load_rag_eval_cases,\n"
            ")\n"
        ),
        nbf.v4.new_markdown_cell(
            "## Run Configuration\n\n"
            "Set `DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY = 'false'` only when this machine cannot validate "
            "the Azure endpoint certificate chain. If the environment already trusts the certificate chain, "
            "leave it empty and the provider will use normal TLS verification."
        ),
        nbf.v4.new_code_cell(
            "DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY = os.getenv('DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY', '')\n"
            "MAX_PAGES = None\n"
            "TARGET_CHUNKS_PER_REPORT = 5\n"
            "MARKDOWN_OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'rag_eval' / 'raw_markdown'\n\n"
            "os.environ['DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY'] = DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY\n"
            "MARKDOWN_OUTPUT_DIR"
        ),
        nbf.v4.new_code_cell(
            "markdown_reports = build_eval_markdown_reports(PROJECT_ROOT / 'reports', max_pages=MAX_PAGES)\n"
            "written_markdown_paths = export_markdown_reports(markdown_reports, MARKDOWN_OUTPUT_DIR)\n\n"
            "markdown_summary = pd.DataFrame(\n"
            "    [\n"
            "        {\n"
            "            'company_name': report.report.company_name,\n"
            "            'report_file': report.report.path.name,\n"
            "            'page_count': report.page_count,\n"
            "            'markdown_characters': len(report.markdown),\n"
            "            'markdown_path': str(path.relative_to(PROJECT_ROOT)),\n"
            "        }\n"
            "        for report, path in zip(markdown_reports, written_markdown_paths, strict=True)\n"
            "    ]\n"
            ")\n"
            "markdown_summary"
        ),
        nbf.v4.new_markdown_cell("## Raw Markdown Preview"),
        nbf.v4.new_code_cell(
            "for report in markdown_reports:\n"
            "    print(report.report.path.name)\n"
            "    display(Markdown(report.markdown[:4000]))\n"
            "    print('-' * 80)\n"
        ),
        nbf.v4.new_markdown_cell(
            "## Broad Coverage Windows\n\n"
            "These are intentionally larger windows built from consecutive markdown pages so the next eval step can "
            "check whether retrieval covers broad report regions rather than only tiny snippets."
        ),
        nbf.v4.new_code_cell(
            "broad_chunks = build_broad_eval_chunks(markdown_reports, target_chunks_per_report=TARGET_CHUNKS_PER_REPORT)\n"
            "broad_chunks_df = pd.DataFrame(eval_chunks_as_rows(broad_chunks))\n"
            "broad_chunks_df[['company_name', 'report_file', 'chunk_index', 'start_page', 'end_page', 'page_count', 'character_count']]"
        ),
        nbf.v4.new_code_cell(
            "for company_name in broad_chunks_df['company_name'].unique():\n"
            "    chunk = next(item for item in broad_chunks if item.company_name == company_name)\n"
            "    print(company_name, f'pages {chunk.start_page}-{chunk.end_page}')\n"
            "    display(Markdown(chunk.content[:3500]))\n"
            "    print('-' * 80)\n"
        ),
        nbf.v4.new_markdown_cell("## Curated Financial Eval Cases"),
        nbf.v4.new_code_cell(
            "eval_cases = load_rag_eval_cases(PROJECT_ROOT / 'data' / 'evals' / 'fundamental_rag_eval_cases.json')\n"
            "eval_cases_df = pd.DataFrame(eval_cases_as_rows(eval_cases))\n"
            "eval_cases_df[['case_id', 'company_name', 'question_style', 'evaluation_focus', 'question', 'expected_answer', 'source_pages']]"
        ),
        nbf.v4.new_code_cell(
            "eval_cases_df.groupby(['company_name', 'question_style']).size().rename('case_count').reset_index()"
        ),
        nbf.v4.new_markdown_cell("## Validation"),
        nbf.v4.new_code_cell(
            "assert len(markdown_reports) == 2\n"
            "assert all(path.exists() for path in written_markdown_paths)\n"
            "assert len(broad_chunks) == 10\n"
            "assert len(eval_cases) == 10\n"
            "assert set(eval_cases_df['company_name']) == {'Bandhan', 'Emcure'}\n"
            "print('RAG eval notebook prepared markdown outputs, broad chunks, and 10 curated eval cases.')"
        ),
    ]
    return notebook


def main() -> None:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    NOTEBOOK_PATH.write_text(nbf.writes(notebook), encoding="utf-8")
    print(f"Wrote {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
