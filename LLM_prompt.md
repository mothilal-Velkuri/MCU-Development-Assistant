Phase 3 LLM prompt
has folllowing steps; 
llm\prompts.py    ← Step 1  (system prompts for each workflow step)
llm\client.py     ← Step 2  (Ollama API wrapper)
test_prompts.py   ← Step 3
test_client.py    ← Step 4

**Step 1:**  **prompts.py**
  create prompts.py file under llm and copy below script.
  # =============================================================
  # llm/prompts.py
  # System prompt builders for each workflow step.
  #
  # Design principles:
  #   1. Every prompt enforces document-only answers
  #   2. Retrieved chunks are injected as DOCUMENT CONTEXT
  #   3. Q&A and Code Generation use different prompt templates
  #      but the same RAG pipeline underneath
  #   4. Errata is always checked automatically
  # =============================================================
  
  from config import OUTPUT_MODE
  
  
  # =============================================================
  # STRICT RULES — Injected into every prompt
  # =============================================================
  
  STRICT_RULES = """
  ╔══════════════════════════════════════════════════════╗
  ║              STRICT DOCUMENT-ONLY RULES              ║
  ╚══════════════════════════════════════════════════════╝
  
  RULE 1 — SOURCE RESTRICTION (NON-NEGOTIABLE):
    You MUST only use information found in the DOCUMENT
    CONTEXT provided below. Never use your training
    knowledge, memory, or any external information.
  
  RULE 2 — CITATION REQUIRED:
    Every answer must cite the source. Format:
    (FileName.pdf | Doc Type | Page N | Section X.X.X)
    Example: (RM0090.pdf | Reference Manual | Page 148 | Section 6.3.2)
  
  RULE 3 — MISSING INFORMATION:
    If the answer is NOT in the provided context, say:
    "This information is not available in the provided
    documents. Please add the relevant datasheet or
    reference manual section."
    Never guess or assume register values.
  
  RULE 4 — ERRATA CHECK:
    Always check if any ERRATA document context mentions
    a known bug or limitation for the topic being discussed.
    If found, flag it clearly with ⚠️ ERRATA warning.
  
  RULE 5 — PRECISION:
    Use exact register names, bit field names, hex
    addresses, bit positions, and allowed values from
    the documents. Never approximate or paraphrase
    register values.
  """
  
  CODE_RULES = """
  ╔══════════════════════════════════════════════════════╗
  ║           CODE GENERATION RULES                      ║
  ╚══════════════════════════════════════════════════════╝
  
  RULE C1 — DOCUMENT GROUNDED CODE ONLY:
    Every register write must cite the document:
    // Section X.X.X, RegisterName, Page N
    RCC->CFGR |= value;
  
  RULE C2 — COMPLETE SEQUENCES:
    Always provide complete initialization sequences
    including clock enable, GPIO config, and peripheral
    config in the correct order as documented.
  
  RULE C3 — ERRATA WORKAROUNDS:
    If errata context mentions a workaround for this
    peripheral, include it in the generated code with
    a comment referencing the errata section.
  
  RULE C4 — IDE AWARENESS:
    Generated code must be compatible with the specified
    IDE and toolchain. Use appropriate CMSIS register
    names for the specified controller family.
  """
  
  
  # =============================================================
  # CONTEXT BLOCK BUILDER
  # =============================================================
  
  def build_context_block(retrieved_chunks: list[dict]) -> str:
      """
      Format retrieved document chunks into a readable
      context block for the LLM.
  
      Each chunk includes:
      - Source file and document type
      - Page number for citation
      - The actual text content
      """
      if not retrieved_chunks:
          return (
              "NO DOCUMENT CONTEXT RETRIEVED.\n"
              "Inform the user that no relevant documents "
              "were found and ask them to add the appropriate "
              "datasheet or reference manual."
          )
  
      lines = ["═" * 55]
      lines.append("RETRIEVED DOCUMENT CONTEXT")
      lines.append("═" * 55)
  
      for i, chunk in enumerate(retrieved_chunks, 1):
          lines.append(
              f"\n[{i}] {chunk['source']} | "
              f"{chunk['doc_type']} | "
              f"Page {chunk['page']} | "
              f"Relevance: {chunk['score']}"
          )
          lines.append("-" * 40)
          lines.append(chunk['text'])
  
      lines.append("\n" + "═" * 55)
      return "\n".join(lines)
  
  
  # =============================================================
  # STEP PROMPTS — Q&A MODE
  # =============================================================
  
  def controller_intro_prompt(
      controller: str,
      ide: str,
      frequency: str,
      notes: str,
      context: str
  ) -> str:
      """
      Step 1: Controller setup introduction prompt.
      Summarizes what documents are available and
      confirms the controller details.
      """
      return f"""You are an expert embedded systems assistant helping
  a developer configure their microcontroller.
  
  DEVELOPER CONFIGURATION:
    Controller  : {controller}
    IDE         : {ide}
    Target Freq : {frequency or "not specified — ask the user"}
    Notes       : {notes or "none"}
  
  {STRICT_RULES}
  
  DOCUMENT CONTEXT:
  {context}
  
  Your task:
  1. Confirm you have received the developer's controller details
  2. Summarize which documents are available in the context
  3. List what topics those documents cover
  4. Ask the user what they want to configure first:
     - Clock configuration
     - Peripheral selection
     - Peripheral configuration
     - Code generation
  
  Keep your response concise and professional.
  """
  
  
  def clock_config_prompt(
      controller: str,
      ide: str,
      frequency: str,
      context: str
  ) -> str:
      """
      Step 2: Clock configuration prompt.
      Guides through clock source, PLL, and bus prescaler setup.
      """
      return f"""You are an expert embedded systems clock configuration
  assistant for {controller} using {ide}.
  
  TARGET FREQUENCY: {frequency or "not yet specified — ask the user"}
  
  {STRICT_RULES}
  
  DOCUMENT CONTEXT:
  {context}
  
  CLOCK CONFIGURATION SCOPE:
  - Clock source selection: HSI, HSE, LSI, LSE, PLL
  - PLL configuration: multipliers, dividers, input range
  - System clock mux selection
  - AHB, APB1, APB2 bus prescalers
  - Flash wait states for target frequency
  - Clock security system (CSS) if documented
  - Any ERRATA affecting clock configuration
  
  Always structure your answer as:
  1. Document source citation
  2. Register name and address
  3. Bit field name and position
  4. Value to write and why
  5. ⚠️ ERRATA warning if applicable
  """
  
  
  def peripheral_selection_prompt(
      controller: str,
      ide: str,
      context: str
  ) -> str:
      """
      Step 3: Peripheral selection prompt.
      Helps identify available peripherals and potential conflicts.
      """
      return f"""You are an expert embedded systems peripheral selection
  assistant for {controller} using {ide}.
  
  {STRICT_RULES}
  
  DOCUMENT CONTEXT:
  {context}
  
  PERIPHERAL SELECTION SCOPE:
  - Which peripherals are available and how many instances
  - Pin availability and alternate function (AF) conflicts
  - DMA channel and stream assignments
  - IRQ numbers and NVIC priority requirements
  - Which APB/AHB bus each peripheral is on
  - Power and clock enable requirements
  - Any ERRATA affecting peripheral selection or availability
  
  When the user names a peripheral they need, provide:
  1. Available instances (e.g. USART1, USART2, USART3)
  2. Possible pins from AF table with page citation
  3. DMA assignment if needed
  4. IRQ number from vector table
  5. ⚠️ ERRATA warning if applicable
  """
  
  
  def peripheral_config_prompt(
      controller: str,
      ide: str,
      context: str
  ) -> str:
      """
      Step 4: Peripheral configuration — register level.
      Provides complete initialization sequences.
      """
      return f"""You are an expert embedded systems register-level
  configuration assistant for {controller} using {ide}.
  
  {STRICT_RULES}
  
  DOCUMENT CONTEXT:
  {context}
  
  CONFIGURATION SCOPE:
  - Complete register-by-register initialization sequence
  - GPIO configuration: MODER, OTYPER, OSPEEDR, PUPDR, AFR
  - Peripheral-specific registers with exact hex values
  - DMA setup: stream, channel, direction, priority
  - NVIC interrupt configuration: IRQ number, priority
  - Any mandatory wait states or ordering constraints
  - ERRATA workarounds embedded in the code sequence
  
  For every register write provide:
    RegisterName->BitField = VALUE;
    // Reason | Source: FileName | Page N | Section X.X.X
    ⚠️ ERRATA: section number if applicable
  """
  
  
  # =============================================================
  # CODE GENERATION PROMPTS — Phase 8
  # =============================================================
  
  def code_generation_prompt(
      controller: str,
      ide: str,
      peripheral: str,
      context: str,
      code_style: str = "bare_metal"
  ) -> str:
      """
      Phase 8: Generate actual C initialization code.
      Grounded strictly in the provided document context.
      """
      style_notes = {
          "bare_metal": "Direct register access using CMSIS definitions",
          "hal":        "STM32 HAL library function calls",
          "cmsis":      "CMSIS-Driver API compliant code",
      }
      style_desc = style_notes.get(code_style, style_notes["bare_metal"])
  
      return f"""You are an expert embedded C code generator for
  {controller} using {ide}.
  
  PERIPHERAL TO CONFIGURE: {peripheral}
  CODE STYLE: {code_style} — {style_desc}
  
  {STRICT_RULES}
  {CODE_RULES}
  
  DOCUMENT CONTEXT:
  {context}
  
  Generate a complete C initialization function including:
  1. File header with controller, peripheral, and source citations
  2. #include statements needed
  3. void {peripheral.replace(' ','_')}_Init(void) function
  4. Every register write commented with source citation
  5. Error handling for timeout-based flag polling
  6. Errata workaround code if applicable
  
  Output ONLY valid C code with comments. No prose explanation.
  """
  
  
  # =============================================================
  # PROMPT SELECTOR — Routes to correct prompt
  # =============================================================
  
  def get_system_prompt(
      step: str,
      controller: str,
      ide: str,
      frequency: str,
      notes: str,
      context: str,
      peripheral: str = "",
      code_style: str = "bare_metal"
  ) -> str:
      """
      Return the correct system prompt for the current step.
      Supports both Q&A mode and code generation mode.
      """
      prompts = {
          "intro": lambda: controller_intro_prompt(
              controller, ide, frequency, notes, context
          ),
          "clock_config": lambda: clock_config_prompt(
              controller, ide, frequency, context
          ),
          "peripheral_selection": lambda: peripheral_selection_prompt(
              controller, ide, context
          ),
          "peripheral_config": lambda: peripheral_config_prompt(
              controller, ide, context
          ),
          "code_generation": lambda: code_generation_prompt(
              controller, ide, peripheral, context, code_style
          ),
      }
  
      builder = prompts.get(step)
      if builder is None:
          raise ValueError(
              f"Unknown step: '{step}'. "
              f"Valid steps: {list(prompts.keys())}"

**Step 2:**  **client.py**
create client.py and copy below script.
  # =============================================================
  # llm/client.py
  # Ollama LLM API wrapper.
  #
  # Sends system prompt + conversation history + user message
  # to the local Ollama mistral model and returns the response.
  #
  # Architecture:
  #   ask_llm()  → single response
  #   stream_llm() → streaming response (token by token)
  #
  # To switch to Anthropic API later:
  #   Change LLM_BACKEND = "anthropic" in config.py
  #   The rest of the code stays the same.
  # =============================================================
  
  import requests
  import json
  from config import (
      LLM_BACKEND,
      OLLAMA_MODEL,
      OLLAMA_URL,
      ANTHROPIC_API_KEY,
      ANTHROPIC_MODEL,
  )
  
  
  # =============================================================
  # OLLAMA CLIENT
  # =============================================================
  
  def _ask_ollama(
      system_prompt: str,
      conversation_history: list[dict],
      user_message: str,
      temperature: float = 0.1,
  ) -> str:
      """
      Send a message to local Ollama LLM.
  
      Parameters
      ----------
      system_prompt        : instructions for the LLM
      conversation_history : list of past messages
                             [{"role": "user"|"assistant",
                               "content": "text"}]
      user_message         : current user question
      temperature          : 0.0 = deterministic, 1.0 = creative
                             Keep low (0.1) for technical answers
  
      Returns
      -------
      LLM response as a string
      """
      # Build message list
      messages = (
          [{"role": "system", "content": system_prompt}]
          + conversation_history
          + [{"role": "user", "content": user_message}]
      )
  
      payload = {
          "model"   : OLLAMA_MODEL,
          "messages": messages,
          "stream"  : False,
          "options" : {
              "temperature"  : temperature,
              "num_predict"  : 2048,    # max tokens in response
              "top_p"        : 0.9,
              "repeat_penalty": 1.1,   # reduce repetition
          }
      }
  
      try:
          response = requests.post(
              OLLAMA_URL,
              json    = payload,
              timeout = 120,    # 2 minutes — mistral can be slow
          )
          response.raise_for_status()
          data = response.json()
          return data["message"]["content"]
  
      except requests.exceptions.ConnectionError:
          return (
              "❌ ERROR: Cannot connect to Ollama.\n"
              "Make sure Ollama is running.\n"
              "Start it with: ollama serve"
          )
      except requests.exceptions.Timeout:
          return (
              "❌ ERROR: Ollama response timed out.\n"
              "The model is taking too long.\n"
              "Try a shorter question or restart Ollama."
          )
      except KeyError:
          return (
              f"❌ ERROR: Unexpected Ollama response format.\n"
              f"Response: {response.text[:200]}"
          )
  
  
  def _stream_ollama(
      system_prompt: str,
      conversation_history: list[dict],
      user_message: str,
      temperature: float = 0.1,
  ):
      """
      Stream tokens from Ollama as they are generated.
      Yields each token string one at a time.
      Used for real-time display in the terminal.
      """
      messages = (
          [{"role": "system", "content": system_prompt}]
          + conversation_history
          + [{"role": "user", "content": user_message}]
      )
  
      payload = {
          "model"   : OLLAMA_MODEL,
          "messages": messages,
          "stream"  : True,
          "options" : {
              "temperature": temperature,
              "num_predict": 2048,
          }
      }
  
      try:
          with requests.post(
              OLLAMA_URL,
              json    = payload,
              stream  = True,
              timeout = 120,
          ) as response:
              response.raise_for_status()
              for line in response.iter_lines():
                  if line:
                      try:
                          chunk = json.loads(line.decode("utf-8"))
                          token = chunk.get("message", {}).get("content", "")
                          if token:
                              yield token
                      except json.JSONDecodeError:
                          continue
  
      except requests.exceptions.ConnectionError:
          yield "\n❌ ERROR: Cannot connect to Ollama."
  
  
  # =============================================================
  # ANTHROPIC CLIENT (future use)
  # =============================================================
  
  def _ask_anthropic(
      system_prompt: str,
      conversation_history: list[dict],
      user_message: str,
      temperature: float = 0.1,
  ) -> str:
      """
      Send a message to Anthropic Claude API.
      Activated when LLM_BACKEND = "anthropic" in config.py.
      """
      try:
          import anthropic
          client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
  
          messages = (
              conversation_history
              + [{"role": "user", "content": user_message}]
          )
  
          response = client.messages.create(
              model      = ANTHROPIC_MODEL,
              max_tokens = 2048,
              system     = system_prompt,
              messages   = messages,
          )
          return response.content[0].text
  
      except ImportError:
          return (
              "❌ ERROR: anthropic package not installed.\n"
              "Run: pip install anthropic"
          )
      except Exception as e:
          return f"❌ ERROR: Anthropic API error: {str(e)}"
  
  
  # =============================================================
  # PUBLIC API — Use these in your workflow
  # =============================================================
  
  def ask_llm(
      system_prompt: str,
      conversation_history: list[dict],
      user_message: str,
      temperature: float = 0.1,
  ) -> str:
      """
      Send a message to the configured LLM backend.
      Returns the complete response as a string.
  
      Parameters
      ----------
      system_prompt        : instructions for the LLM
      conversation_history : past Q&A turns for this step
      user_message         : current user question
      temperature          : keep at 0.1 for technical accuracy
  
      Returns
      -------
      Complete LLM response as a string.
      """
      if LLM_BACKEND == "anthropic":
          return _ask_anthropic(
              system_prompt,
              conversation_history,
              user_message,
              temperature,
          )
      else:
          return _ask_ollama(
              system_prompt,
              conversation_history,
              user_message,
              temperature,
          )
  
  
  def stream_llm(
      system_prompt: str,
      conversation_history: list[dict],
      user_message: str,
      temperature: float = 0.1,
  ):
      """
      Stream tokens from the LLM one at a time.
      Use this for real-time terminal display.
  
      Usage:
          for token in stream_llm(prompt, history, question):
              print(token, end="", flush=True)
          print()  # newline at end
      """
      if LLM_BACKEND == "anthropic":
          # Anthropic streaming — fall back to non-streaming for now
          yield ask_llm(
              system_prompt,
              conversation_history,
              user_message,
              temperature,
          )
      else:
          yield from _stream_ollama(
              system_prompt,
              conversation_history,
              user_message,
              temperature,
          )
  
  
  def check_ollama_running() -> bool:
      """
      Check if Ollama server is running and accessible.
      Returns True if running, False otherwise.
      """
      try:
          r = requests.get(
              "http://localhost:11434",
              timeout = 3
          )
          return r.status_code == 200
      except Exception:
          return False
  
  
  def check_model_available(model: str = OLLAMA_MODEL) -> bool:
      """
      Check if the specified model is downloaded in Ollama.
      Returns True if available, False otherwise.
      """
      try:
          r = requests.get(
              "http://localhost:11434/api/tags",
              timeout = 5
          )
          if r.status_code == 200:
              models = [m["name"] for m in r.json().get("models", [])]
              return any(model in m for m in models)
          return False
      except Exception:
        return False          )
      return builder()
