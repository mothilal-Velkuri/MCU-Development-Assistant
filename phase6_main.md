in phase 6 create main file.
# =============================================================
# main.py — MCU Dev Assistant Entry Point
#
# Connects all phases into one working CLI:
#   Phase 1 → ingestion (pdf_parser, chunker)
#   Phase 2 → retrieval (embedder, vector_store)
#   Phase 3 → llm (prompts, client)
#   Phase 4 → workflow (steps, session)
#   Phase 5 → output (formatter, code_writer)
#
# Usage:
#   python main.py              ← start new session
#   python main.py --resume     ← resume last session
#   python main.py --reindex    ← re-index docs and start
# =============================================================

import os
import sys
import argparse

os.environ["ANONYMIZED_TELEMETRY"] = "False"

from rich.prompt   import Prompt, Confirm
from rich.console  import Console

# ── Project modules ───────────────────────────────────────
from config import (
    DOCS_FOLDER, CHROMA_DB_PATH,
    DOC_TYPES, OUTPUT_MODE
)
from ingestion.pdf_parser   import parse_pdf
from ingestion.chunker      import chunk_pages
from retrieval.vector_store import (
    index_chunks, get_chunk_count,
    list_indexed_sources, list_indexed_doc_types,
    clear_collection,
)
from workflow.steps import (
    WorkflowState, STEPS, STEP_LABELS,
    chat, chat_intro,
    add_peripheral, extract_peripherals_from_message,
)
from workflow.session import (
    save_session, load_session,
    list_sessions, generate_session_id,
)
from output.formatter import (
    console, print_welcome, print_session_header,
    print_step_banner, format_response,
    print_user_message, print_thinking,
    print_streaming_start, format_response_stream_end,
    print_error, print_success, print_info,
    print_warning, print_help, print_sources,
    print_index_summary,
)
from output.code_writer import (
    extract_c_code, save_c_file,
    save_h_file, list_generated_files,
)
from llm.client import check_ollama_running, check_model_available


# =============================================================
# DOCUMENT INGESTION
# =============================================================

def ingest_documents(force_reindex: bool = False) -> int:
    """
    Parse and index all PDFs in the docs/ folder.

    Parameters
    ----------
    force_reindex : if True clear DB and re-index everything

    Returns
    -------
    Total number of chunks indexed.
    """
    # Check if docs/ folder exists and has PDFs
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)

    pdf_files = [
        f for f in os.listdir(DOCS_FOLDER)
        if f.lower().endswith('.pdf')
    ]

    if not pdf_files:
        print_warning(
            f"No PDFs found in {DOCS_FOLDER}/\n"
            f"  Add your datasheet, reference manual, or errata PDF\n"
            f"  then restart the application."
        )
        return 0

    console.print(
        f"\n[bold green]Found {len(pdf_files)} PDF(s) "
        f"in docs/[/bold green]"
    )

    # Ask user to label each PDF
    doc_type_map = {}
    for pdf in pdf_files:
        console.print(
            f"\n  [cyan]{pdf}[/cyan]"
        )
        doc_type = Prompt.ask(
            "  Label this document",
            choices = DOC_TYPES,
            default = "Datasheet",
        )
        doc_type_map[pdf] = doc_type

    # Parse and chunk all PDFs
    all_chunks = []
    for pdf_name, doc_type in doc_type_map.items():
        pdf_path = os.path.join(DOCS_FOLDER, pdf_name)
        console.print(
            f"\n  [dim]Parsing {pdf_name}...[/dim]"
        )
        pages  = parse_pdf(pdf_path, doc_type)
        chunks = chunk_pages(pages)
        all_chunks.extend(chunks)
        print_success(
            f"Parsed {pdf_name}: "
            f"{len(pages)} pages → {len(chunks)} chunks"
        )

    if not all_chunks:
        print_error("No content extracted from PDFs.")
        return 0

    # Index into ChromaDB
    console.print(
        f"\n  [dim]Indexing {len(all_chunks)} chunks "
        f"into vector DB...[/dim]"
    )
    total = index_chunks(
        all_chunks,
        clear_existing = force_reindex
    )

    print_success(f"Indexed {total} total chunks in vector DB.")
    return total


# =============================================================
# STARTUP CHECKS
# =============================================================

def check_prerequisites() -> bool:
    """
    Verify Ollama is running and model is available.
    Returns True if all checks pass.
    """
    console.print("\n[dim]Checking prerequisites...[/dim]")

    # Check Ollama
    if not check_ollama_running():
        print_error(
            "Ollama is not running.\n"
            "  Start it with: ollama serve\n"
            "  Then restart this application."
        )
        return False
    print_success("Ollama is running")

    # Check mistral model
    if not check_model_available("mistral"):
        print_error(
            "Mistral model not found.\n"
            "  Download it with: ollama pull mistral"
        )
        return False
    print_success("Mistral model available")

    return True


# =============================================================
# SESSION SETUP
# =============================================================

def setup_new_session() -> WorkflowState:
    """
    Collect controller details from user and create
    a new WorkflowState.
    """
    console.print(
        "\n[bold blue]Step 1 — Controller & IDE Setup"
        "[/bold blue]"
    )
    console.print(
        "[dim]Enter your microcontroller details below.[/dim]\n"
    )

    controller = Prompt.ask(
        "  Controller / MCU part number",
        default = "STM32F407VGT6"
    )
    ide = Prompt.ask(
        "  IDE / Toolchain",
        default = "STM32CubeIDE"
    )
    frequency = Prompt.ask(
        "  Target system clock (e.g. 168 MHz)",
        default = "168 MHz"
    )
    notes = Prompt.ask(
        "  Additional notes (optional)",
        default = ""
    )

    state = WorkflowState(
        controller   = controller,
        ide          = ide,
        frequency    = frequency,
        notes        = notes,
        session_id   = generate_session_id(),
        docs_indexed = get_chunk_count(),
    )

    print_success(
        f"Session created: {controller} | {ide} | {frequency}"
    )
    return state


def try_resume_session() -> WorkflowState | None:
    """
    Let user choose a saved session to resume.
    Returns WorkflowState if resumed, None if starting fresh.
    """
    sessions = list_sessions()
    if not sessions:
        return None

    console.print(
        "\n[bold]Saved sessions found:[/bold]"
    )
    for i, s in enumerate(sessions[:5], 1):
        console.print(
            f"  [{i}] {s['controller']} | "
            f"{s['step']} | "
            f"{s['saved_at'][:16]}"
        )

    choice = Prompt.ask(
        "\n  Resume a session? (enter number or N)",
        default = "N"
    )

    if choice.upper() == "N":
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            state = load_session(sessions[idx]["session_id"])
            state.docs_indexed = get_chunk_count()
            print_success(
                f"Resumed: {state.controller} — "
                f"{state.current_label()}"
            )
            return state
    except (ValueError, FileNotFoundError):
        print_error("Invalid choice. Starting new session.")

    return None


# =============================================================
# COMMAND HANDLER
# =============================================================

def handle_command(
    command: str,
    state: WorkflowState
) -> str:
    """
    Handle special CLI commands.

    Returns
    -------
    "continue" → keep the current step loop running
    "next"     → advance to next step
    "back"     → go back one step
    "quit"     → exit the application
    """
    cmd = command.strip().lower()

    if cmd == "next":
        if state.is_last_step():
            print_info("Already on the last step.")
            return "continue"
        save_session(state)
        state.advance()
        print_step_banner(
            state.current_label(),
            state.step_number()
        )
        return "next"

    elif cmd == "back":
        try:
            idx = STEPS.index(state.current_step)
            if idx > 0:
                state.go_to_step(STEPS[idx - 1])
                print_step_banner(
                    state.current_label(),
                    state.step_number()
                )
            else:
                print_info("Already on the first step.")
        except ValueError:
            pass
        return "continue"

    elif cmd == "save":
        path = save_session(state)
        print_success(f"Session saved: {path}")
        return "continue"

    elif cmd == "status":
        console.print(
            f"\n[bold]Session Status[/bold]\n"
            f"{state.summary()}"
        )
        return "continue"

    elif cmd == "docs":
        sources = list_indexed_sources()
        types   = list_indexed_doc_types()
        total   = get_chunk_count()
        if sources:
            print_index_summary(sources, types, total)
        else:
            print_warning("No documents indexed yet.")
        return "continue"

    elif cmd == "files":
        files = list_generated_files()
        if files:
            console.print(
                "\n[bold]Generated Files:[/bold]"
            )
            for f in files:
                console.print(f"  [cyan]{f}[/cyan]")
        else:
            print_info("No generated files yet.")
        return "continue"

    elif cmd == "clear":
        os.system("cls" if os.name == "nt" else "clear")
        print_session_header(
            state.controller,
            state.ide,
            state.frequency,
            state.docs_indexed,
            state.current_label(),
        )
        return "continue"

    elif cmd == "help":
        print_help(state.current_label())
        return "continue"

    elif cmd in ("quit", "exit", "q"):
        return "quit"

    elif cmd == "":
        return "continue"

    # Not a command — treat as a question
    return "question"


# =============================================================
# STEP CHAT LOOP
# =============================================================

def run_step_loop(state: WorkflowState) -> str:
    """
    Run the interactive Q&A loop for the current step.

    Returns
    -------
    "next" → user wants to advance
    "quit" → user wants to exit
    """
    print_step_banner(
        state.current_label(),
        state.step_number()
    )

    # Auto-generate intro message on first step
    if state.current_step == "intro":
        if not state.history["intro"]:
            console.print(
                "[dim]Analyzing your documents...[/dim]"
            )
            try:
                response = chat_intro(state)
                format_response(response, "Introduction")
            except Exception as e:
                print_error(f"Could not generate intro: {e}")

    while True:
        try:
            # Get user input
            user_input = Prompt.ask(
                f"\n[bold cyan]You[/bold cyan] "
                f"[dim]({state.current_label()})[/dim]"
            )
        except KeyboardInterrupt:
            console.print()
            return "quit"

        # Handle commands
        action = handle_command(user_input, state)

        if action == "quit":
            return "quit"
        elif action == "next":
            return "next"
        elif action == "continue":
            continue
        # action == "question" → fall through to LLM

        # Detect peripherals mentioned in message
        found = extract_peripherals_from_message(user_input)
        for p in found:
            add_peripheral(state, p)

        # Get LLM response
        print_thinking()
        try:
            # Use streaming for better UX
            print_streaming_start()
            response = ""
            from llm.client import stream_llm
            from llm.prompts import build_context_block, get_system_prompt
            from workflow.steps import get_context_for_query
            from config import CODE_STYLE

            search_query = (
                f"{state.controller} {user_input}"
            )
            context, chunks = get_context_for_query(search_query)
            system_prompt = get_system_prompt(
                step       = state.current_step,
                controller = state.controller,
                ide        = state.ide,
                frequency  = state.frequency,
                notes      = state.notes,
                context    = context,
                peripheral = (
                    state.selected_peripherals[-1]
                    if state.selected_peripherals else ""
                ),
                code_style = CODE_STYLE,
            )
            history = state.history[state.current_step]
            for token in stream_llm(
                system_prompt, history, user_input
            ):
                console.print(token, end="")
            console.print()
            format_response_stream_end()

            # Save full response to history
            # (streaming already printed it)
            response = chat(state, user_input, stream=False)

            # Show sources
            print_sources(chunks)

            # If code generation step — offer to save
            if state.current_step == "code_generation":
                code = extract_c_code(response)
                if (
                    "void " in code and
                    state.selected_peripherals
                ):
                    if Confirm.ask(
                        "\n  Save generated code to file?",
                        default = True
                    ):
                        peripheral = state.selected_peripherals[-1]
                        filepath = save_c_file(
                            code       = code,
                            peripheral = peripheral,
                            controller = state.controller,
                            ide        = state.ide,
                        )
                        state.generated_code[peripheral] = filepath
                        print_success(f"Saved: {filepath}")

                        # Update header file
                        func_name = (
                            f"{peripheral.replace(' ','_')}_Init"
                        )
                        save_h_file(
                            declarations = [
                                f"void {func_name}(void);"
                            ],
                            controller   = state.controller,
                        )

        except Exception as e:
            print_error(f"LLM error: {str(e)}")
            print_info(
                "Make sure Ollama is running: ollama serve"
            )

        # Auto-save after every response
        save_session(state)


# =============================================================
# MAIN APPLICATION
# =============================================================

def main():
    """
    Main application entry point.
    Parses CLI arguments, sets up session, runs step loops.
    """
    # ── Parse arguments ────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="MCU Dev Assistant — "
                    "Document-grounded embedded systems Q&A"
    )
    parser.add_argument(
        "--resume",
        action  = "store_true",
        help    = "Resume the most recent session"
    )
    parser.add_argument(
        "--reindex",
        action  = "store_true",
        help    = "Clear vector DB and re-index all documents"
    )
    args = parser.parse_args()

    # ── Welcome ────────────────────────────────────────────
    print_welcome()

    # ── Prerequisites ──────────────────────────────────────
    if not check_prerequisites():
        sys.exit(1)

    # ── Document ingestion ─────────────────────────────────
    chunk_count = get_chunk_count()

    if args.reindex or chunk_count == 0:
        if chunk_count == 0:
            console.print(
                "\n[yellow]Vector DB is empty. "
                "Indexing documents...[/yellow]"
            )
        else:
            console.print(
                "\n[yellow]Re-indexing all documents...[/yellow]"
            )
        chunk_count = ingest_documents(
            force_reindex = args.reindex
        )
    else:
        sources = list_indexed_sources()
        types   = list_indexed_doc_types()
        console.print(
            f"\n[green]✅ Vector DB loaded: "
            f"{chunk_count} chunks from "
            f"{len(sources)} file(s)[/green]"
        )
        print_index_summary(sources, types, chunk_count)

        if Confirm.ask(
            "  Re-index documents?",
            default = False
        ):
            chunk_count = ingest_documents(force_reindex=True)

    # ── Session setup ──────────────────────────────────────
    state = None

    if args.resume:
        state = try_resume_session()

    if state is None:
        # Check if there are saved sessions to offer
        if not args.resume:
            state = try_resume_session()

    if state is None:
        # Start fresh
        state = setup_new_session()

    state.docs_indexed = chunk_count

    # ── Show session header ────────────────────────────────
    print_session_header(
        state.controller,
        state.ide,
        state.frequency,
        state.docs_indexed,
        state.current_label(),
    )

    # ── Main workflow loop ─────────────────────────────────
    console.print(
        "\n[dim]Type your question or 'help' for commands.[/dim]"
    )

    while True:
        result = run_step_loop(state)

        if result == "quit":
            break

        if result == "next":
            if state.is_last_step():
                break
            # Loop continues with new step

    # ── Exit ───────────────────────────────────────────────
    save_session(state)
    print_success("Session saved.")
    console.print(
        "\n[bold green]Thank you for using MCU Dev Assistant."
        "[/bold green]"
    )

    # Print generated files summary if any
    files = list_generated_files()
    if files:
        console.print(
            f"\n[bold]Generated Files:[/bold]"
        )
        for f in files:
            console.print(
                f"  [cyan]generated/{f}[/cyan]"
            )


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    main()
