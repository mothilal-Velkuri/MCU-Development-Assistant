# test_prompts.py — Phase 3 Test 1
# Run: python test_prompts.py

from llm.prompts import (
    build_context_block,
    get_system_prompt,
    STRICT_RULES,
    CODE_RULES,
)

print("=" * 50)
print("PROMPTS.PY TEST")
print("=" * 50)

# ── Sample chunks (simulating RAG retrieval) ───────────────
sample_chunks = [
    {
        "text"    : "Section 6.3.2 RCC_PLLCFGR: Set PLLN=168, "
                    "PLLM=8, PLLP=2 for 168 MHz system clock. "
                    "HSE 8 MHz external crystal required.",
        "source"  : "RM0090.pdf",
        "doc_type": "Reference Manual",
        "page"    : 148,
        "score"   : 0.92,
    },
    {
        "text"    : "Errata 2.2.13: Delay after RCC peripheral "
                    "clock enabling. A delay may be observed "
                    "between RCC enable and peripheral readiness. "
                    "Workaround: insert dummy read or DSB.",
        "source"  : "STM32F407_ERRATE.pdf",
        "doc_type": "Errata",
        "page"    : 12,
        "score"   : 0.78,
    },
]

# ── Test 1: Context block ──────────────────────────────────
print("\nTest 1 — Context block builder")
ctx = build_context_block(sample_chunks)
has_header  = "RETRIEVED DOCUMENT CONTEXT" in ctx
has_source  = "RM0090.pdf" in ctx
has_errata  = "STM32F407_ERRATE.pdf" in ctx
has_page    = "Page 148" in ctx
has_score   = "0.92" in ctx
print(f"  Has header      : {has_header}")
print(f"  Has source      : {has_source}")
print(f"  Has errata file : {has_errata}")
print(f"  Has page number : {has_page}")
print(f"  Has score       : {has_score}")
pass1 = all([has_header, has_source, has_errata, has_page])
print(f"  PASS" if pass1 else "  FAIL")

# ── Test 2: Empty context ──────────────────────────────────
print("\nTest 2 — Empty context handling")
empty_ctx = build_context_block([])
has_no_docs_msg = "NO DOCUMENT CONTEXT" in empty_ctx
print(f"  Returns no-docs message: {has_no_docs_msg}")
print(f"  PASS" if has_no_docs_msg else "  FAIL")

# ── Test 3: Clock prompt ───────────────────────────────────
print("\nTest 3 — Clock configuration prompt")
clock_p = get_system_prompt(
    step       = "clock_config",
    controller = "STM32F407VGT6",
    ide        = "STM32CubeIDE",
    frequency  = "168 MHz",
    notes      = "External 8 MHz crystal",
    context    = ctx,
)
has_controller = "STM32F407VGT6" in clock_p
has_freq       = "168 MHz" in clock_p
has_rules      = "STRICT DOCUMENT-ONLY RULES" in clock_p
has_context    = "RETRIEVED DOCUMENT CONTEXT" in clock_p
has_pll        = "PLL" in clock_p
print(f"  Has controller  : {has_controller}")
print(f"  Has frequency   : {has_freq}")
print(f"  Has strict rules: {has_rules}")
print(f"  Has context     : {has_context}")
print(f"  Has PLL mention : {has_pll}")
pass3 = all([has_controller, has_freq, has_rules, has_context])
print(f"  PASS" if pass3 else "  FAIL")

# ── Test 4: All steps work ─────────────────────────────────
print("\nTest 4 — All workflow steps build correctly")
steps = [
    "intro", "clock_config",
    "peripheral_selection",
    "peripheral_config",
    "code_generation",
]
all_ok = True
for step in steps:
    try:
        p = get_system_prompt(
            step       = step,
            controller = "STM32F407",
            ide        = "Keil",
            frequency  = "168 MHz",
            notes      = "",
            context    = ctx,
            peripheral = "USART1",
        )
        has_rules = "STRICT DOCUMENT-ONLY RULES" in p
        has_ctx   = "RETRIEVED DOCUMENT CONTEXT" in p
        ok = has_rules and has_ctx and len(p) > 200
        print(f"  Step '{step}': {'✅' if ok else '❌'} "
              f"({len(p)} chars)")
        if not ok:
            all_ok = False
    except Exception as e:
        print(f"  Step '{step}': ❌ ERROR — {e}")
        all_ok = False
print(f"  PASS" if all_ok else "  FAIL")

# ── Test 5: Invalid step raises error ─────────────────────
print("\nTest 5 — Invalid step raises ValueError")
try:
    get_system_prompt(
        "invalid_step", "STM32", "Keil",
        "168", "", ctx
    )
    print("  FAIL — should have raised ValueError")
except ValueError as e:
    print(f"  ValueError raised correctly: {str(e)[:50]}")
    print(f"  PASS")

# ── Test 6: Code prompt has C-specific rules ───────────────
print("\nTest 6 — Code generation prompt has code rules")
code_p = get_system_prompt(
    step       = "code_generation",
    controller = "STM32F407",
    ide        = "Keil",
    frequency  = "168 MHz",
    notes      = "",
    context    = ctx,
    peripheral = "USART1",
    code_style = "bare_metal",
)
has_code_rules = "CODE GENERATION RULES" in code_p
has_c_style    = "bare_metal" in code_p
has_init_func  = "USART1_Init" in code_p
print(f"  Has code rules  : {has_code_rules}")
print(f"  Has style info  : {has_c_style}")
print(f"  Has init func   : {has_init_func}")
pass6 = all([has_code_rules, has_c_style, has_init_func])
print(f"  PASS" if pass6 else "  FAIL")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 50)
all_results = pass1 and has_no_docs_msg and pass3 and all_ok and pass6
print("RESULT: prompts.py OK ✅" if all_results
      else "RESULT: prompts.py FAILED ❌")
print("=" * 50)