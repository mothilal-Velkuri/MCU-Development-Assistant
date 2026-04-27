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
from Config import TOP_K_RESULTS, OUTPUT_MODE, CODE_STYLE


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
    include_errata: bool = True,
    doc_type_filter: str = None,
) -> tuple[str, list[dict]]:
    """
    Search the vector store for chunks relevant to the query.

    Parameters
    ----------
    query           : user question or search terms
    top_k           : number of main results to retrieve
    include_errata  : always append errata check results
    doc_type_filter : optional — restrict to one doc type
                      e.g. "Reference Manual" or "Datasheet"

    Returns
    -------
    context_text : formatted string for LLM prompt injection
    all_chunks   : raw list of chunk dicts for logging
    """
    # Main semantic search — all docs or filtered by type
    if doc_type_filter:
        from retrieval.vector_store import search_by_doc_type
        chunks = search_by_doc_type(
            query, doc_type_filter, top_k=top_k
        )
    else:
        chunks = search(query, top_k=top_k)

    # Errata auto-check — always check for silicon bugs
    # even when a doc_type_filter is active
    if include_errata:
        errata_chunks = search_errata_only(query, top_k=2)

        # Add errata results not already in main results
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