phase4 has following steps.

workflow\steps.py    ← Step 1  (state machine + chat orchestration)
workflow\session.py  ← Step 2  (saves session to disk)
test_workflow.py     ← Step 3
**Step 1:**  **steps.py**
  # =============================================================
  # workflow/steps.py
  # State machine controlling the step-by-step conversation.
  #
  # Flow:
  #   intro → clock_config → peripheral_selection
  #         → peripheral_config → code_generation
  #
  # Each step has:
  #   - Its own system prompt (from llm/prompts.py)
  #   - Its own conversation history
  #   - RAG search for every user message
  #   - Automatic errata check
  # =============================================================
  
  from dataclasses import dataclass, field
  from retrieval.vector_store import search, search_errata_only
  from llm.prompts import build_context_block, get_system_prompt
  from llm.client import ask_llm, stream_llm
  from config import TOP_K_RESULTS, OUTPUT_MODE, CODE_STYLE
  
  
  # =============================================================
  # STEP DEFINITIONS
  # =============================================================
  
  STEPS = [
      "intro",
      "clock_config",
      "peripheral_selection",
      "peripheral_config",
      "code_generation",
  ]
  
  STEP_LABELS = {
      "intro"               : "01 · Controller & IDE Setup",
      "clock_config"        : "02 · Clock Configuration",
      "peripheral_selection": "03 · Peripheral Selection",
      "peripheral_config"   : "04 · Peripheral Configuration",
      "code_generation"     : "05 · Code Generation",
  }
  
  
  # =============================================================
  # WORKFLOW STATE
  # =============================================================
  
  @dataclass
  class WorkflowState:
      """
      Holds the complete state of a developer session.
      Passed through the entire workflow lifecycle.
      """
      # Developer configuration
      controller  : str = ""
      ide         : str = ""
      frequency   : str = ""
      notes       : str = ""
  
      # Current position in the workflow
      current_step: str = "intro"
  
      # Conversation history per step
      # Each step maintains its own history for context
      history: dict = field(
          default_factory=lambda: {s: [] for s in STEPS}
      )
  
      # Peripherals the developer has selected
      selected_peripherals: list = field(default_factory=list)
  
      # Generated code snippets (Phase 8)
      generated_code: dict = field(default_factory=dict)
  
      # Session metadata
      session_id   : str = ""
      docs_indexed : int = 0
  
      def advance(self) -> bool:
          """
          Move to the next workflow step.
          Returns True if advanced, False if already at last step.
          """
          try:
              idx = STEPS.index(self.current_step)
          except ValueError:
              return False
  
          if idx < len(STEPS) - 1:
              self.current_step = STEPS[idx + 1]
              print(f"\n  ▶ Moved to: "
                    f"{STEP_LABELS[self.current_step]}\n")
              return True
          return False
  
      def go_to_step(self, step: str) -> bool:
          """
          Jump to a specific step by name.
          Returns True if successful.
          """
          if step in STEPS:
              self.current_step = step
              return True
          return False
  
      def current_label(self) -> str:
          """Return the display label for the current step."""
          return STEP_LABELS.get(self.current_step, self.current_step)
  
      def step_number(self) -> str:
          """Return current step as '2 of 5' string."""
          try:
              idx = STEPS.index(self.current_step)
              return f"{idx + 1} of {len(STEPS)}"
          except ValueError:
              return "? of 5"
  
      def is_last_step(self) -> bool:
          """Check if we are on the final step."""
          return self.current_step == STEPS[-1]
  
      def summary(self) -> str:
          """Return a text summary of current state."""
          lines = [
              f"Controller  : {self.controller or 'not set'}",
              f"IDE         : {self.ide or 'not set'}",
              f"Frequency   : {self.frequency or 'not set'}",
              f"Current Step: {self.current_label()}",
              f"Step        : {self.step_number()}",
              f"Docs Indexed: {self.docs_indexed}",
          ]
          if self.selected_peripherals:
              lines.append(
                  f"Peripherals : {', '.join(self.selected_peripherals)}"
              )
          return "\n".join(lines)
  
  
  # =============================================================
  # RAG SEARCH FOR CURRENT STEP
  # =============================================================
  
  def get_context_for_query(
      query: str,
      top_k: int = TOP_K_RESULTS,
      include_errata: bool = True
  ) -> tuple[str, list[dict]]:
      """
      Search the vector store for chunks relevant to the query.
      Optionally appends errata-specific results.
  
      Returns
      -------
      context_text : formatted string for injection into prompt
      all_chunks   : raw list of chunk dicts for logging
      """
      # Main semantic search
      chunks = search(query, top_k=top_k)
  
      # Errata auto-check — always check for known bugs
      if include_errata:
          errata_chunks = search_errata_only(query, top_k=2)
  
          # Add errata results that are not already in main results
          existing_texts = {c["text"] for c in chunks}
          for ec in errata_chunks:
              if ec["text"] not in existing_texts:
                  chunks.append(ec)
  
      context = build_context_block(chunks)
      return context, chunks
  
  
  # =============================================================
  # CHAT — Main conversation handler
  # =============================================================
  
  def chat(
      state: WorkflowState,
      user_message: str,
      stream: bool = False,
  ) -> str:
      """
      Process a user message in the current workflow step.
  
      Steps:
      1. Search vector store for relevant chunks
      2. Build system prompt with retrieved context
      3. Send to LLM with conversation history
      4. Update history and return response
  
      Parameters
      ----------
      state        : current workflow state
      user_message : what the user typed
      stream       : if True, print tokens as they arrive
  
      Returns
      -------
      Complete LLM response as string
      """
      # ── Step 1: Build search query ─────────────────────────
      # Combine user message with controller context for
      # better retrieval — e.g. "STM32F407 PLL 168 MHz"
      search_query = user_message
      if state.controller:
          search_query = f"{state.controller} {user_message}"
  
      # ── Step 2: Retrieve relevant chunks ───────────────────
      context, chunks = get_context_for_query(search_query)
  
      # ── Step 3: Build system prompt ────────────────────────
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
  
      # ── Step 4: Call LLM ───────────────────────────────────
      history = state.history[state.current_step]
  
      if stream:
          # Collect streamed tokens into full response
          response = ""
          for token in stream_llm(system_prompt, history, user_message):
              print(token, end="", flush=True)
              response += token
          print()  # newline after streaming
      else:
          response = ask_llm(system_prompt, history, user_message)
  
      # ── Step 5: Update history ─────────────────────────────
      state.history[state.current_step].extend([
          {"role": "user",      "content": user_message},
          {"role": "assistant", "content": response},
      ])
  
      return response
  
  
  def chat_intro(state: WorkflowState) -> str:
      """
      Special handler for the intro step.
      Uses a generic query since no user input yet.
      """
      intro_query = (
          f"{state.controller} {state.ide} "
          f"clock peripheral configuration"
      )
      context, _ = get_context_for_query(intro_query)
  
      system_prompt = get_system_prompt(
          step       = "intro",
          controller = state.controller,
          ide        = state.ide,
          frequency  = state.frequency,
          notes      = state.notes,
          context    = context,
      )
  
      response = ask_llm(system_prompt, [], "Begin session.")
      state.history["intro"].extend([
          {"role": "user",      "content": "Begin session."},
          {"role": "assistant", "content": response},
      ])
      return response
  
  
  # =============================================================
  # PERIPHERAL TRACKING
  # =============================================================
  
  def add_peripheral(state: WorkflowState, peripheral: str) -> None:
      """Add a peripheral to the selected list if not already there."""
      p = peripheral.strip().upper()
      if p and p not in state.selected_peripherals:
          state.selected_peripherals.append(p)
          print(f"  Added peripheral: {p}")
  
  
  def extract_peripherals_from_message(message: str) -> list[str]:
      """
      Attempt to detect peripheral names in user messages.
      Simple keyword detection — not NLP.
      """
      keywords = [
          "USART", "UART", "SPI", "I2C", "I2S",
          "ADC", "DAC", "TIM", "TIMER", "DMA",
          "CAN", "USB", "ETH", "GPIO", "SDIO",
          "RTC", "IWDG", "WWDG", "PWM", "EXTI",
      ]
      found = []
      msg_upper = message.upper()
      for kw in keywords:
          if kw in msg_upper and kw not in found:
              found.append(kw)
      return found
**Step 2:**  **session.py**
  # =============================================================
  # workflow/session.py
  # Saves and loads workflow sessions to disk.
  #
  # Why sessions?
  #   You may need to stop mid-way through configuring a
  #   complex peripheral. Sessions let you resume exactly
  #   where you left off — same history, same state.
  #
  # Format: JSON file in ./sessions/ folder
  # =============================================================
  
  import json
  import os
  import uuid
  from datetime import datetime
  from pathlib import Path
  from workflow.steps import WorkflowState
  
  SESSIONS_FOLDER = "./sessions"
  
  
  def _ensure_sessions_folder() -> None:
      """Create sessions folder if it does not exist."""
      Path(SESSIONS_FOLDER).mkdir(exist_ok=True)
  
  
  def generate_session_id() -> str:
      """Generate a unique session ID."""
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      short_id  = str(uuid.uuid4())[:8]
      return f"session_{timestamp}_{short_id}"
  
  
  def save_session(state: WorkflowState) -> str:
      """
      Save current workflow state to a JSON file.
  
      Parameters
      ----------
      state : current WorkflowState
  
      Returns
      -------
      Path to the saved session file.
      """
      _ensure_sessions_folder()
  
      if not state.session_id:
          state.session_id = generate_session_id()
  
      session_data = {
          "session_id"          : state.session_id,
          "saved_at"            : datetime.now().isoformat(),
          "controller"          : state.controller,
          "ide"                 : state.ide,
          "frequency"           : state.frequency,
          "notes"               : state.notes,
          "current_step"        : state.current_step,
          "selected_peripherals": state.selected_peripherals,
          "generated_code"      : state.generated_code,
          "docs_indexed"        : state.docs_indexed,
          "history"             : state.history,
      }
  
      filepath = os.path.join(
          SESSIONS_FOLDER,
          f"{state.session_id}.json"
      )
  
      with open(filepath, "w", encoding="utf-8") as f:
          json.dump(session_data, f, indent=2, ensure_ascii=False)
  
      print(f"  Session saved: {filepath}")
      return filepath
  
  
  def load_session(session_id: str) -> WorkflowState:
      """
      Load a previously saved session from disk.
  
      Parameters
      ----------
      session_id : the session ID string
  
      Returns
      -------
      WorkflowState restored from file.
      """
      filepath = os.path.join(
          SESSIONS_FOLDER,
          f"{session_id}.json"
      )
  
      if not os.path.exists(filepath):
          raise FileNotFoundError(
              f"Session not found: {session_id}\n"
              f"Looked in: {filepath}"
          )
  
      with open(filepath, "r", encoding="utf-8") as f:
          data = json.load(f)
  
      state = WorkflowState(
          controller           = data["controller"],
          ide                  = data["ide"],
          frequency            = data["frequency"],
          notes                = data.get("notes", ""),
          current_step         = data["current_step"],
          selected_peripherals = data.get("selected_peripherals", []),
          generated_code       = data.get("generated_code", {}),
          session_id           = data["session_id"],
          docs_indexed         = data.get("docs_indexed", 0),
          history              = data.get("history", {}),
      )
  
      print(f"  Session loaded: {session_id}")
      print(f"  Controller    : {state.controller}")
      print(f"  Current step  : {state.current_label()}")
      return state
  
  
  def list_sessions() -> list[dict]:
      """
      List all saved sessions with their metadata.
  
      Returns
      -------
      List of dicts with session info — newest first.
      """
      _ensure_sessions_folder()
  
      sessions = []
      for filename in os.listdir(SESSIONS_FOLDER):
          if not filename.endswith(".json"):
              continue
  
          filepath = os.path.join(SESSIONS_FOLDER, filename)
          try:
              with open(filepath, "r", encoding="utf-8") as f:
                  data = json.load(f)
              sessions.append({
                  "session_id" : data.get("session_id", "unknown"),
                  "controller" : data.get("controller", "unknown"),
                  "ide"        : data.get("ide", "unknown"),
                  "saved_at"   : data.get("saved_at", "unknown"),
                  "step"       : data.get("current_step", "unknown"),
                  "filepath"   : filepath,
              })
          except Exception:
              continue
  
      # Sort newest first
      sessions.sort(key=lambda x: x["saved_at"], reverse=True)
      return sessions
  
  
  def delete_session(session_id: str) -> bool:
      """
      Delete a saved session file.
      Returns True if deleted, False if not found.
      """
      filepath = os.path.join(
          SESSIONS_FOLDER,
          f"{session_id}.json"
      )
      if os.path.exists(filepath):
          os.remove(filepath)
        print(f"  Session deleted: {session_id}")
        return True
    return False
