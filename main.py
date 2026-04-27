# =============================================================
# main.py — MCU Dev Assistant Entry Point
# =============================================================

import os
import sys
import argparse

os.environ["ANONYMIZED_TELEMETRY"] = "False"

from rich.prompt   import Prompt, Confirm
from rich.console  import Console

from Config import (
    DOCS_FOLDER, CHROMA_DB_PATH,
    DOC_TYPES, OUTPUT_MODE, CODE_STYLE
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
    get_context_for_query,
)
from workflow.session import (
    save_session, load_session,
    list_sessions, generate_session_id,
)
from Output.formatter import (
    console, print_welcome, print_session_header,
    print_step_banner, format_response,
    print_user_message, print_thinking,
    print_streaming_start, format_response_stream_end,
    print_error, print_success, print_info,
    print_warning, print_help, print_sources,
    print_index_summary,
)
from Output.code_writer import (
    extract_c_code, save_c_file,
    save_h_file, list_generated_files,
)
from llm.prompts import get_system_prompt
from llm.client import (
    check_ollama_running, check_model_available,
    stream_llm, ask_llm,
)


# =============================================================
# DOCUMENT INGESTION
# =============================================================

def ingest_documents(force_reindex: bool = False) -> int:
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)

    pdf_files = [
        f for f in os.listdir(DOCS_FOLDER)
        if f.lower().endswith('.pdf')
    ]

    if not pdf_files:
        print_warning(
            f"No PDFs found in {DOCS_FOLDER}/\n"
            f"  Add your datasheet, reference manual, "
            f"or errata PDF then restart."
        )
        return 0

    console.print(
        f"\n[bold green]Found {len(pdf_files)} PDF(s) "
        f"in docs/[/bold green]"
    )

    doc_type_map = {}
    for pdf in pdf_files:
        console.print(f"\n  [cyan]{pdf}[/cyan]")
        doc_type = Prompt.ask(
            "  Label this document",
            choices = DOC_TYPES,
            default = "Datasheet",
        )
        doc_type_map[pdf] = doc_type

    all_chunks = []
    for pdf_name, doc_type in doc_type_map.items():
        pdf_path = os.path.join(DOCS_FOLDER, pdf_name)
        console.print(f"\n  [dim]Parsing {pdf_name}...[/dim]")
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

    console.print(
        f"\n  [dim]Indexing {len(all_chunks)} chunks...[/dim]"
    )
    total = index_chunks(
        all_chunks,
        clear_existing = force_reindex
    )
    print_success(f"Indexed {total} total chunks.")
    return total


# =============================================================
# STARTUP CHECKS
# =============================================================

def check_prerequisites() -> bool:
    console.print("\n[dim]Checking prerequisites...[/dim]")

    if not check_ollama_running():
        print_error(
            "Ollama is not running.\n"
            "  Start it: ollama serve"
        )
        return False
    print_success("Ollama is running")

    if not check_model_available("mistral"):
        print_error(
            "Mistral model not found.\n"
            "  Download: ollama pull mistral"
        )
        return False
    print_success("Mistral model available")

    return True


# =============================================================
# SESSION SETUP
# =============================================================

def setup_new_session() -> WorkflowState:
    console.print(
        "\n[bold blue]Step 1 — Controller & IDE Setup"
        "[/bold blue]"
    )
    console.print(
        "[dim]Enter your microcontroller details.[/dim]\n"
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
        "  Target system clock",
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
    sessions = list_sessions()
    if not sessions:
        return None

    console.print("\n[bold]Saved sessions found:[/bold]")
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
            console.print("\n[bold]Generated Files:[/bold]")
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

    return "question"


# =============================================================
# STEP CHAT LOOP
# =============================================================

def run_step_loop(state: WorkflowState) -> str:
    """Run the interactive Q&A loop for the current step."""

    print_step_banner(
        state.current_label(),
        state.step_number()
    )

    # Auto intro on first step
    if (state.current_step == "intro" and
            not state.history["intro"]):
        print("Analyzing your documents...", flush=True)
        try:
            response = chat_intro(state)
            print(f"\nAssistant:\n{response}\n", flush=True)
        except Exception as e:
            print(f"Intro error: {e}", flush=True)

    while True:
        try:
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

        # action == "question" — call LLM
        found = extract_peripherals_from_message(user_input)
        for p in found:
            add_peripheral(state, p)

        print("\nSearching documents...", flush=True)

        try:
            search_query = f"{state.controller} {user_input}"
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

            print("Generating response...", flush=True)

            full_response = ask_llm(
                system_prompt        = system_prompt,
                conversation_history = history,
                user_message         = user_input,
            )

            print("\n" + "=" * 60, flush=True)
            print("ASSISTANT:", flush=True)
            print("=" * 60, flush=True)
            print(full_response, flush=True)
            print("=" * 60 + "\n", flush=True)

            # Update history
            state.history[state.current_step].extend([
                {"role": "user",      "content": user_input},
                {"role": "assistant", "content": full_response},
            ])

            # Show sources
            if chunks:
                seen = set()
                src_list = []
                for c in chunks:
                    key = f"{c['source']}::{c['page']}"
                    if key not in seen:
                        seen.add(key)
                        src_list.append(
                            f"{c['source']} p.{c['page']}"
                        )
                print(
                    f"Sources: {' | '.join(src_list[:4])}\n",
                    flush=True
                )

            # Code save offer
            if state.current_step == "code_generation":
                code = extract_c_code(full_response)
                if "void " in code:
                    if Confirm.ask(
                        "  Save generated code to file?",
                        default=True
                    ):
                        peripheral = (
                            state.selected_peripherals[-1]
                            if state.selected_peripherals
                            else "peripheral"
                        )
                        filepath = save_c_file(
                            code       = code,
                            peripheral = peripheral,
                            controller = state.controller,
                            ide        = state.ide,
                        )
                        state.generated_code[peripheral] = filepath
                        print(
                            f"Saved: {filepath}", flush=True
                        )
                        save_h_file(
                            declarations=[
                                f"void {peripheral}_Init(void);"
                            ],
                            controller=state.controller,
                        )

        except Exception as e:
            print(f"\nERROR: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

        # Auto-save
        save_session(state)


# =============================================================
# MAIN
# =============================================================

def main():
    parser = argparse.ArgumentParser(
        description="MCU Dev Assistant"
    )
    parser.add_argument(
        "--resume",  action="store_true",
        help="Resume last session"
    )
    parser.add_argument(
        "--reindex", action="store_true",
        help="Re-index all documents"
    )
    args = parser.parse_args()

    print_welcome()

    if not check_prerequisites():
        sys.exit(1)

    chunk_count = get_chunk_count()

    if args.reindex or chunk_count == 0:
        if chunk_count == 0:
            console.print(
                "\n[yellow]Vector DB empty. "
                "Indexing documents...[/yellow]"
            )
        chunk_count = ingest_documents(
            force_reindex=args.reindex
        )
    else:
        sources = list_indexed_sources()
        types   = list_indexed_doc_types()
        console.print(
            f"\n[green]✅ Vector DB: {chunk_count} chunks "
            f"from {len(sources)} file(s)[/green]"
        )
        print_index_summary(sources, types, chunk_count)

        if Confirm.ask("  Re-index documents?", default=False):
            chunk_count = ingest_documents(force_reindex=True)

    state = None

    if args.resume:
        state = try_resume_session()

    if state is None:
        state = try_resume_session()

    if state is None:
        state = setup_new_session()

    state.docs_indexed = chunk_count

    print_session_header(
        state.controller,
        state.ide,
        state.frequency,
        state.docs_indexed,
        state.current_label(),
    )

    console.print(
        "\n[dim]Type your question or 'help' for commands."
        "[/dim]"
    )

    while True:
        result = run_step_loop(state)
        if result == "quit":
            break
        if result == "next" and state.is_last_step():
            break

    save_session(state)
    print_success("Session saved.")
    console.print(
        "\n[bold green]Thank you for using "
        "MCU Dev Assistant.[/bold green]"
    )

    files = list_generated_files()
    if files:
        console.print("\n[bold]Generated Files:[/bold]")
        for f in files:
            console.print(f"  [cyan]generated/{f}[/cyan]")


if __name__ == "__main__":
    main()