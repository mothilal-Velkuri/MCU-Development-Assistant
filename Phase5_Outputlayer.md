Phase 5 has following steps
output\formatter.py    ← Step 1  (formats Q&A answers for terminal)
output\code_writer.py  ← Step 2  (saves generated C code to files)

**Step 1:**  **formatter.py**
  # =============================================================
  # output/formatter.py
  # Formats LLM responses for clean terminal display.
  #
  # Handles:
  #   - Q&A answers with citation highlighting
  #   - Errata warnings with visual emphasis
  #   - Register tables with alignment
  #   - Session status panels
  #   - Step transition banners
  # =============================================================
  
  from rich.console import Console
  from rich.panel   import Panel
  from rich.table   import Table
  from rich.text    import Text
  from rich.rule    import Rule
  from rich         import box
  
  console = Console()
  
  
  # =============================================================
  # COLOURS AND STYLES
  # =============================================================
  
  STYLE_HEADER    = "bold green"
  STYLE_RESPONSE  = "white"
  STYLE_CITATION  = "bold cyan"
  STYLE_ERRATA    = "bold red"
  STYLE_WARNING   = "yellow"
  STYLE_SUCCESS   = "bold green"
  STYLE_ERROR     = "bold red"
  STYLE_DIM       = "dim white"
  STYLE_STEP      = "bold blue"
  STYLE_USER      = "bold cyan"
  STYLE_ASSISTANT = "bold green"
  
  
  # =============================================================
  # RESPONSE FORMATTER
  # =============================================================
  
  def format_response(response: str, step: str = "") -> None:
      """
      Print a formatted LLM response to the terminal.
  
      Highlights:
      - Citations in cyan
      - ⚠️ ERRATA warnings in red panel
      - Register names in yellow
      - Section numbers in bold
      """
      # Check for errata warnings in response
      has_errata = (
          "⚠️" in response or
          "ERRATA" in response.upper() or
          "errata" in response.lower()
      )
  
      # Split response into errata and non-errata sections
      if has_errata:
          _print_errata_warning()
  
      # Print main response in a panel
      panel_title = f"[{STYLE_ASSISTANT}]Assistant[/{STYLE_ASSISTANT}]"
      if step:
          panel_title += f" [dim]— {step}[/dim]"
  
      console.print(Panel(
          response,
          title        = panel_title,
          border_style = "green",
          padding      = (1, 2),
      ))
  
  
  def format_response_stream_end(step: str = "") -> None:
      """
      Print a separator after a streamed response.
      Called after all tokens have been printed.
      """
      console.print()
      console.print(Rule(style="dim green"))
  
  
  def _print_errata_warning() -> None:
      """Print a visual errata warning banner."""
      console.print(Panel(
          "[bold red]⚠️  ERRATA DETECTED[/bold red]\n"
          "[yellow]This response contains information about "
          "known silicon bugs.\n"
          "Review the errata section carefully before "
          "implementing.[/yellow]",
          border_style = "red",
          padding      = (0, 2),
      ))
  
  
  # =============================================================
  # SESSION DISPLAY
  # =============================================================
  
  def print_session_header(
      controller: str,
      ide: str,
      frequency: str,
      docs_indexed: int,
      step_label: str,
  ) -> None:
      """
      Print the session status header at startup.
      Shows controller, IDE, docs loaded, current step.
      """
      console.print()
      console.print(Rule(
          "[bold green]MCU DEV ASSISTANT[/bold green]",
          style = "green"
      ))
  
      table = Table(
          box             = box.SIMPLE,
          show_header     = False,
          padding         = (0, 2),
          border_style    = "dim",
      )
      table.add_column("Field", style="dim")
      table.add_column("Value", style="bold white")
  
      table.add_row("Controller",   controller or "not set")
      table.add_row("IDE",          ide or "not set")
      table.add_row("Frequency",    frequency or "not set")
      table.add_row("Docs Indexed", f"{docs_indexed} chunks")
      table.add_row("Current Step", f"[bold blue]{step_label}[/bold blue]")
  
      console.print(table)
      console.print(Rule(style="dim green"))
      console.print()
  
  
  def print_step_banner(step_label: str, step_number: str) -> None:
      """
      Print a banner when transitioning to a new step.
      """
      console.print()
      console.print(Panel(
          f"[bold blue]{step_label}[/bold blue]\n"
          f"[dim]Step {step_number}[/dim]",
          border_style = "blue",
          padding      = (0, 2),
      ))
      console.print()
  
  
  def print_welcome() -> None:
      """Print the welcome screen at application startup."""
      console.print()
      console.print(Panel(
          "[bold green]MCU DEV ASSISTANT[/bold green]\n\n"
          "[white]Document-Grounded Embedded Systems Assistant[/white]\n"
          "[dim]• Answers only from your uploaded documents\n"
          "• Cites exact page numbers and register names\n"
          "• Automatically checks errata for silicon bugs\n"
          "• Supports Q&A and C code generation[/dim]",
          border_style = "green",
          padding      = (1, 4),
      ))
      console.print()
  
  
  # =============================================================
  # USER INPUT DISPLAY
  # =============================================================
  
  def print_user_message(message: str) -> None:
      """Display the user's message with styling."""
      console.print(
          f"\n[{STYLE_USER}]You:[/{STYLE_USER}] {message}"
      )
  
  
  def print_thinking() -> None:
      """Show a thinking indicator while waiting for LLM."""
      console.print(
          f"[dim]Searching documents and generating response...[/dim]"
      )
  
  
  def print_streaming_start() -> None:
      """Print the assistant label before streaming starts."""
      console.print(
          f"\n[{STYLE_ASSISTANT}]Assistant:[/{STYLE_ASSISTANT}]"
      )
  
  
  # =============================================================
  # DOCUMENT INDEX DISPLAY
  # =============================================================
  
  def print_index_summary(
      sources: list[str],
      doc_type_counts: dict,
      total_chunks: int,
  ) -> None:
      """
      Print a summary of indexed documents.
      """
      console.print(Panel(
          "[bold green]Documents Indexed[/bold green]",
          border_style = "green",
          padding      = (0, 2),
      ))
  
      table = Table(
          box          = box.SIMPLE_HEAVY,
          border_style = "dim",
          padding      = (0, 1),
      )
      table.add_column("Document",  style="cyan", no_wrap=True)
      table.add_column("Type",      style="yellow")
      table.add_column("Chunks",    style="white", justify="right")
  
      for dtype, count in doc_type_counts.items():
          table.add_row("", dtype, str(count))
  
      console.print(table)
      console.print(
          f"[dim]Total: {total_chunks} chunks from "
          f"{len(sources)} file(s)[/dim]"
      )
      console.print()
  
  
  # =============================================================
  # ERROR AND INFO MESSAGES
  # =============================================================
  
  def print_error(message: str) -> None:
      """Print an error message."""
      console.print(
          f"[{STYLE_ERROR}]❌ ERROR:[/{STYLE_ERROR}] {message}"
      )
  
  
  def print_success(message: str) -> None:
      """Print a success message."""
      console.print(
          f"[{STYLE_SUCCESS}]✅[/{STYLE_SUCCESS}] {message}"
      )
  
  
  def print_info(message: str) -> None:
      """Print an informational message."""
      console.print(
          f"[{STYLE_WARNING}]ℹ[/{STYLE_WARNING}]  {message}"
      )
  
  
  def print_warning(message: str) -> None:
      """Print a warning message."""
      console.print(
          f"[{STYLE_WARNING}]⚠️[/{STYLE_WARNING}]  {message}"
      )
  
  
  # =============================================================
  # HELP AND COMMANDS
  # =============================================================
  
  def print_help(current_step: str) -> None:
      """
      Print available commands for the current step.
      """
      console.print(Panel(
          "[bold]Available Commands[/bold]\n\n"
          "[cyan]next[/cyan]     → advance to next step\n"
          "[cyan]back[/cyan]     → go to previous step\n"
          "[cyan]save[/cyan]     → save session to disk\n"
          "[cyan]status[/cyan]   → show current session info\n"
          "[cyan]docs[/cyan]     → show indexed documents\n"
          "[cyan]clear[/cyan]    → clear screen\n"
          "[cyan]help[/cyan]     → show this help\n"
          "[cyan]quit[/cyan]     → exit (session auto-saved)\n\n"
          "[dim]Or just type your question about "
          f"the current step: {current_step}[/dim]",
          border_style = "dim",
          padding      = (0, 2),
      ))
  
  
  def print_sources(chunks: list[dict]) -> None:
      """
      Print a compact source list from retrieved chunks.
      Shown after each response so user knows where to verify.
      """
      if not chunks:
          return
  
      seen = set()
      sources = []
      for c in chunks:
          key = f"{c['source']}::{c['page']}"
          if key not in seen:
              seen.add(key)
              sources.append(c)
  
      console.print(
          f"\n[dim]Sources consulted: "
          + " | ".join(
              f"{c['source']} p.{c['page']}"
              for c in sources[:4]
          )
          + "[/dim]"
      )

**Step 2:**  **code_writer.py**
  # =============================================================
  # output/code_writer.py
  # Saves generated C code to files in the generated/ folder.
  #
  # Phase 8 feature — used when OUTPUT_MODE includes "code".
  # Designed now so Phase 8 slots in without changes.
  #
  # Output structure:
  #   generated/
  #   ├── clock_config.c
  #   ├── usart1_config.c
  #   ├── spi2_config.c
  #   └── mcu_config.h     ← combined header
  # =============================================================
  
  import os
  import re
  from datetime import datetime
  from pathlib  import Path
  from config   import GENERATED_CODE_PATH
  
  
  # =============================================================
  # FOLDER SETUP
  # =============================================================
  
  def _ensure_generated_folder() -> None:
      """Create the generated/ folder if it does not exist."""
      Path(GENERATED_CODE_PATH).mkdir(exist_ok=True)
  
  
  def _sanitize_name(name: str) -> str:
      """
      Convert a peripheral name to a safe filename.
      e.g. "USART1 @ 115200" → "usart1_115200"
      """
      name = name.lower()
      name = re.sub(r'[^a-z0-9_]', '_', name)
      name = re.sub(r'_+', '_', name)
      return name.strip('_')
  
  
  # =============================================================
  # CODE FILE WRITER
  # =============================================================
  
  def save_c_file(
      code: str,
      peripheral: str,
      controller: str,
      ide: str,
  ) -> str:
      """
      Save generated C code to a .c file.
  
      Parameters
      ----------
      code       : the generated C code string
      peripheral : e.g. "USART1", "SPI2", "clock"
      controller : e.g. "STM32F407VGT6"
      ide        : e.g. "STM32CubeIDE"
  
      Returns
      -------
      Path to the saved file.
      """
      _ensure_generated_folder()
  
      filename = f"{_sanitize_name(peripheral)}_config.c"
      filepath = os.path.join(GENERATED_CODE_PATH, filename)
  
      # Add file header if not already present
      if not code.strip().startswith("/*"):
          header = _build_file_header(peripheral, controller, ide)
          code = header + "\n" + code
  
      with open(filepath, "w", encoding="utf-8") as f:
          f.write(code)
  
      print(f"  ✅ Saved: {filepath}")
      return filepath
  
  
  def save_h_file(
      declarations: list[str],
      controller: str,
  ) -> str:
      """
      Save or update the combined header file.
      Adds function declarations for all generated init functions.
  
      Parameters
      ----------
      declarations : list of function declaration strings
                     e.g. ["void USART1_Init(void);"]
      controller   : e.g. "STM32F407VGT6"
  
      Returns
      -------
      Path to the saved header file.
      """
      _ensure_generated_folder()
  
      guard   = "MCU_CONFIG_H"
      filepath = os.path.join(GENERATED_CODE_PATH, "mcu_config.h")
  
      lines = [
          f"/* mcu_config.h — Generated by MCU Dev Assistant",
          f" * Controller : {controller}",
          f" * Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
          f" */",
          f"",
          f"#ifndef {guard}",
          f"#define {guard}",
          f"",
          f"#include <stdint.h>",
          f"",
          f"/* ── Generated Initialization Functions ──────────── */",
      ]
      for decl in declarations:
          lines.append(decl)
      lines += ["", f"#endif /* {guard} */", ""]
  
      with open(filepath, "w", encoding="utf-8") as f:
          f.write("\n".join(lines))
  
      print(f"  ✅ Saved header: {filepath}")
      return filepath
  
  
  def _build_file_header(
      peripheral: str,
      controller: str,
      ide: str,
  ) -> str:
      """Build a standard C file header comment block."""
      return (
          f"/*\n"
          f" * {_sanitize_name(peripheral)}_config.c\n"
          f" * Generated by MCU Dev Assistant\n"
          f" *\n"
          f" * Controller : {controller}\n"
          f" * IDE        : {ide}\n"
          f" * Generated  : "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
          f" *\n"
          f" * IMPORTANT: All register values are sourced from\n"
          f" * the documents you uploaded. Verify against your\n"
          f" * specific hardware revision before flashing.\n"
          f" */\n\n"
      )
  
  
  # =============================================================
  # CODE EXTRACTION
  # =============================================================
  
  def extract_c_code(llm_response: str) -> str:
      """
      Extract C code blocks from an LLM response.
  
      The LLM may wrap code in markdown fences:
  ```c
      void USART1_Init(void) { ... }
  ```
  
      This function extracts just the code.
  
      Parameters
      ----------
      llm_response : raw LLM response string
  
      Returns
      -------
      Clean C code string, or full response if no fence found.
      """
      # Try to find ```c ... ``` block
      pattern = re.compile(
          r'```(?:c|C)?\s*\n(.*?)```',
          re.DOTALL
      )
      matches = pattern.findall(llm_response)
  
      if matches:
          # Join multiple code blocks if present
          return "\n\n".join(m.strip() for m in matches)
  
      # No markdown fence — check if response looks like C code
      if (
          "void " in llm_response or
          "int "  in llm_response or
          "#include" in llm_response or
          "RCC->" in llm_response
      ):
          return llm_response.strip()
  
      # Return as-is — let the caller decide
      return llm_response.strip()
  
  
  def list_generated_files() -> list[str]:
      """
      List all files in the generated/ folder.
  
      Returns
      -------
      List of filenames e.g. ['clock_config.c', 'usart1_config.c']
      """
      _ensure_generated_folder()
      return [
          f for f in os.listdir(GENERATED_CODE_PATH)
          if f.endswith(('.c', '.h'))
      ]
  
  
  def clear_generated_files() -> int:
      """
      Delete all generated C/H files.
  
      Returns
      -------
      Number of files deleted.
      """
      _ensure_generated_folder()
      count = 0
      for filename in list_generated_files():
          filepath = os.path.join(GENERATED_CODE_PATH, filename)
          os.remove(filepath)
          count += 1
    print(f"  Cleared {count} generated file(s).")
    return count
