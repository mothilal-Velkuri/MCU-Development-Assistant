# =============================================================
# llm/code_prompts.py
# Specialized prompts for C code generation.
#
# Design:
#   Same RAG pipeline as Q&A mode.
#   Different prompt instructs LLM to output C code
#   instead of explanatory text.
#
# Code styles supported:
#   bare_metal → direct register access (CMSIS)
#   hal        → STM32 HAL library
#   cmsis      → CMSIS-Driver API
# =============================================================

from Config import CODE_STYLE


# =============================================================
# CODE GENERATION RULES
# =============================================================

CODE_STRICT_RULES = """
╔══════════════════════════════════════════════════════╗
║         CODE GENERATION — STRICT RULES              ║
╚══════════════════════════════════════════════════════╝

RULE 1 — DOCUMENT GROUNDED ONLY:
  Every register write MUST have a comment citing:
  // RegisterName — Source: FileName.pdf | Page N | Section X.X.X
  Example:
  RCC->AHB1ENR |= RCC_AHB1ENR_GPIODEN;
  // RCC_AHB1ENR bit 3 — RM0090.pdf | Page 180 | Section 6.3.10

RULE 2 — COMPLETE SEQUENCES ONLY:
  Always include ALL of these in order:
  1. Clock enable (RCC register)
  2. GPIO configuration (if peripheral uses pins)
  3. Peripheral register configuration
  4. Error handling (timeout loops for flag polling)

RULE 3 — ERRATA WORKAROUNDS:
  If errata context mentions a bug for this peripheral:
  Include the workaround in the code with comment:
  // ⚠️ ERRATA Section X.X.X — workaround: ...

RULE 4 — MISSING INFORMATION:
  If a register value is NOT in the provided documents:
  Add a TODO comment:
  // TODO: Verify value — not found in provided documents

RULE 5 — OUTPUT FORMAT:
  Output ONLY valid C code.
  No prose explanation before or after the code block.
  Use markdown code fence: ```c ... ```
"""


# =============================================================
# CLOCK CODE PROMPT
# =============================================================

def clock_code_prompt(
    controller: str,
    ide: str,
    frequency: str,
    context: str,
) -> str:
    """
    Generate complete clock initialization C code.
    Configures PLL, bus prescalers, flash wait states.
    """
    return f"""You are an expert embedded C code generator
for {controller} using {ide}.

TARGET FREQUENCY: {frequency}

{CODE_STRICT_RULES}

DOCUMENT CONTEXT:
{context}

Generate a complete clock_init.c file containing:

1. File header comment with controller and frequency
2. #include statements
3. void SystemClock_Config(void) function that:
   a. Configures HSE or HSI clock source
   b. Sets PLL multipliers and dividers (PLLM, PLLN, PLLP)
      for exactly {frequency} system clock
   c. Sets AHB prescaler (HPRE)
   d. Sets APB1 prescaler (PPRE1) — max 42 MHz
   e. Sets APB2 prescaler (PPRE2) — max 84 MHz
   f. Sets Flash wait states for {frequency}
   g. Switches system clock to PLL
   h. Waits for clock switch confirmation
   i. Includes errata workaround if found in documents

Every register write must have a comment citing the
source document, page number, and section number.

Output ONLY the C code in a ```c code fence.
"""


# =============================================================
# GPIO CODE PROMPT
# =============================================================

def gpio_code_prompt(
    controller: str,
    ide: str,
    port: str,
    pins: list[int],
    mode: str,
    context: str,
) -> str:
    """
    Generate GPIO initialization C code.

    Parameters
    ----------
    port  : e.g. "D" for GPIOD
    pins  : e.g. [12, 13, 14, 15]
    mode  : "output", "input", "alternate", "analog"
    """
    pins_str = ", ".join(f"Pin {p}" for p in pins)
    pin_mask = " | ".join(f"GPIO_PIN_{p}" for p in pins)

    return f"""You are an expert embedded C code generator
for {controller} using {ide}.

{CODE_STRICT_RULES}

DOCUMENT CONTEXT:
{context}

Generate complete GPIO initialization code for:
  Port     : GPIO{port}
  Pins     : {pins_str}
  Mode     : {mode}

The function must configure ALL of these registers
from the GPIO chapter of the provided documents:
  1. RCC clock enable for GPIO{port}
  2. MODER   — pin mode ({mode})
  3. OTYPER  — output type (push-pull for output)
  4. OSPEEDR — output speed (high speed)
  5. PUPDR   — pull-up/pull-down (none for output)

If mode is "alternate":
  6. AFR[0] or AFR[1] — alternate function number
     (from GPIO alternate function table in documents)

Include:
  void GPIO{port}_Init(void) function
  void GPIO{port}_WritePin(uint8_t pin, uint8_t state)
  uint8_t GPIO{port}_ReadPin(uint8_t pin)

Every register cite source document and page number.
Output ONLY the C code in a ```c code fence.
"""


# =============================================================
# PERIPHERAL CODE PROMPT
# =============================================================

def peripheral_code_prompt(
    controller: str,
    ide: str,
    peripheral: str,
    config: dict,
    context: str,
    code_style: str = "bare_metal",
) -> str:
    """
    Generate complete peripheral initialization C code.

    Parameters
    ----------
    peripheral : e.g. "USART1", "SPI2", "I2C1", "TIM2"
    config     : dict of peripheral settings e.g.
                 {"baud_rate": "115200", "word_length": "8"}
    code_style : "bare_metal", "hal", "cmsis"
    """
    style_notes = {
        "bare_metal": "Direct register access using CMSIS definitions",
        "hal"       : "STM32 HAL library function calls (HAL_xxx)",
        "cmsis"     : "CMSIS-Driver API compliant",
    }
    style_desc = style_notes.get(code_style, style_notes["bare_metal"])

    config_str = "\n".join(
        f"  {k}: {v}" for k, v in config.items()
    )

    return f"""You are an expert embedded C code generator
for {controller} using {ide}.

PERIPHERAL    : {peripheral}
CODE STYLE    : {code_style} — {style_desc}
CONFIGURATION :
{config_str}

{CODE_STRICT_RULES}

DOCUMENT CONTEXT:
{context}

Generate a COMPLETE {peripheral} driver file including:

1. File header comment
2. #include statements
3. #define constants for register values
4. void {peripheral}_Init(void) — complete init sequence:
   a. Enable peripheral clock (RCC register + page cite)
   b. Configure GPIO pins for this peripheral
      (from GPIO AF table in documents)
   c. Configure all peripheral registers
      (from {peripheral} chapter in documents)
   d. Apply errata workarounds if found
5. Transmit/Receive functions appropriate for peripheral
6. Error handling with timeout

Every register write must cite:
// RegisterName = VALUE;
// Source: FileName.pdf | Page N | Section X.X.X
⚠️ ERRATA: cite section if applicable

Output ONLY the C code in a ```c code fence.
"""


# =============================================================
# DRIVER HEADER PROMPT
# =============================================================

def driver_header_prompt(
    controller: str,
    peripherals: list[str],
    context: str,
) -> str:
    """
    Generate a combined driver header file.
    """
    func_list = "\n".join(
        f"  - {p}_Init(void)" for p in peripherals
    )

    return f"""You are an expert embedded C code generator
for {controller}.

{CODE_STRICT_RULES}

DOCUMENT CONTEXT:
{context}

Generate a clean mcu_drivers.h header file that:

1. Has proper include guard (#ifndef MCU_DRIVERS_H)
2. Includes stdint.h and stdbool.h
3. Declares all init functions for:
{func_list}
4. Declares common utility functions
5. Defines common return codes:
   #define MCU_OK    0
   #define MCU_ERROR 1
   #define MCU_TIMEOUT 2

Output ONLY the C header code in a ```c code fence.
"""


# =============================================================
# PROMPT SELECTOR
# =============================================================

def get_code_prompt(
    prompt_type: str,
    controller: str,
    ide: str,
    context: str,
    **kwargs,
) -> str:
    """
    Return the correct code generation prompt.

    Parameters
    ----------
    prompt_type : "clock", "gpio", "peripheral", "header"
    controller  : e.g. "STM32F407VGT6"
    ide         : e.g. "STM32CubeIDE"
    context     : RAG retrieved document context
    **kwargs    : prompt-specific arguments
    """
    if prompt_type == "clock":
        return clock_code_prompt(
            controller = controller,
            ide        = ide,
            frequency  = kwargs.get("frequency", "168 MHz"),
            context    = context,
        )
    elif prompt_type == "gpio":
        return gpio_code_prompt(
            controller = controller,
            ide        = ide,
            port       = kwargs.get("port", "A"),
            pins       = kwargs.get("pins", [0]),
            mode       = kwargs.get("mode", "output"),
            context    = context,
        )
    elif prompt_type == "peripheral":
        return peripheral_code_prompt(
            controller = controller,
            ide        = ide,
            peripheral = kwargs.get("peripheral", "USART1"),
            config     = kwargs.get("config", {}),
            context    = context,
            code_style = kwargs.get("code_style", CODE_STYLE),
        )
    elif prompt_type == "header":
        return driver_header_prompt(
            controller  = controller,
            peripherals = kwargs.get("peripherals", []),
            context     = context,
        )
    else:
        raise ValueError(
            f"Unknown prompt_type: '{prompt_type}'. "
            f"Valid: clock, gpio, peripheral, header"
        )