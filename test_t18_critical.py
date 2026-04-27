# =============================================================
# test_t18_critical.py — Test Case T-18
# CRITICAL: Verifies strict document-only rules are present
# in EVERY prompt template.
#
# Why this is critical:
#   If any prompt is missing the document-only restriction,
#   the LLM will answer from its training knowledge instead
#   of your uploaded documents — giving uncited, potentially
#   wrong register values for your specific controller.
#
# Run: python test_t18_critical.py
# =============================================================

from llm.prompts import get_system_prompt, build_context_block

print("=" * 60)
print("T-18 CRITICAL — Strict Rules Present in ALL Prompts")
print("=" * 60)

# ── Sample context for testing ─────────────────────────────
sample_chunks = [
    {
        "text"    : "Section 6.3.2: PLL configuration register.",
        "source"  : "RM0090.pdf",
        "doc_type": "Reference Manual",
        "page"    : 148,
        "score"   : 0.92,
    },
    {
        "text"    : "Errata 2.2.13: Delay after RCC clock enable.",
        "source"  : "STM32F407_ERRATE.pdf",
        "doc_type": "Errata",
        "page"    : 12,
        "score"   : 0.78,
    },
]
ctx = build_context_block(sample_chunks)

# ── All workflow steps to test ─────────────────────────────
steps = [
    "intro",
    "clock_config",
    "peripheral_selection",
    "peripheral_config",
    "code_generation",
]

# ── Critical phrases that MUST appear in every prompt ──────
# These are the exact phrases that prevent the LLM from
# using its own training knowledge instead of your documents.
CRITICAL_PHRASES = [
    ("Document restriction",
     "only use information",
     "LLM may answer from training knowledge"),

    ("Citation requirement",
     "cite",
     "LLM may not cite sources — answers unverifiable"),

    ("Missing info instruction",
     "not available in the provided",
     "LLM may guess instead of admitting gaps"),

    ("Errata check",
     "errata",
     "LLM may miss known silicon bugs"),

    ("Strict rules header",
     "STRICT DOCUMENT-ONLY RULES",
     "Rules block may be missing entirely"),

    ("Context injection",
     "RETRIEVED DOCUMENT CONTEXT",
     "Document context may not be reaching the LLM"),
]

# ── Run the check ──────────────────────────────────────────
all_passed   = True
total_checks = 0
failed_checks= []

print(f"\nChecking {len(steps)} steps × "
      f"{len(CRITICAL_PHRASES)} critical phrases "
      f"= {len(steps)*len(CRITICAL_PHRASES)} checks total\n")

for step in steps:
    print(f"  Step: '{step}'")

    prompt = get_system_prompt(
        step       = step,
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
        notes      = "External 8 MHz HSE crystal",
        context    = ctx,
        peripheral = "USART1",
        code_style = "bare_metal",
    )

    prompt_lower = prompt.lower()
    step_passed  = True

    for desc, phrase, risk in CRITICAL_PHRASES:
        total_checks += 1
        found = phrase.lower() in prompt_lower

        status = "✅" if found else "❌"
        print(f"    {status} {desc}: '{phrase}'")

        if not found:
            step_passed  = False
            all_passed   = False
            failed_checks.append({
                "step"  : step,
                "phrase": phrase,
                "desc"  : desc,
                "risk"  : risk,
            })

    print(f"    {'PASS ✅' if step_passed else 'FAIL ❌'}\n")

# ── Detailed failure report ────────────────────────────────
if failed_checks:
    print("=" * 60)
    print("❌ FAILURES FOUND — MUST FIX BEFORE PROCEEDING")
    print("=" * 60)
    for f in failed_checks:
        print(f"\n  Step     : {f['step']}")
        print(f"  Missing  : '{f['phrase']}'")
        print(f"  Desc     : {f['desc']}")
        print(f"  Risk     : {f['risk']}")
        print(f"  Fix      : Add this phrase to the prompt "
              f"builder in llm/prompts.py")

# ── Prompt length check ────────────────────────────────────
print("=" * 60)
print("PROMPT LENGTH CHECK")
print("=" * 60)
print("(Too short = rules may be truncated by the model)\n")

min_safe_length = 500
length_ok = True

for step in steps:
    prompt = get_system_prompt(
        step       = step,
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
        notes      = "",
        context    = ctx,
        peripheral = "USART1",
    )
    length = len(prompt)
    ok     = length >= min_safe_length
    if not ok:
        length_ok = False
    print(f"  {'✅' if ok else '❌'} {step:<25} : "
          f"{length} chars "
          f"{'(OK)' if ok else f'(TOO SHORT — min {min_safe_length})'}")

# ── Rules isolation test ───────────────────────────────────
print("\n" + "=" * 60)
print("RULES ISOLATION TEST")
print("(Verifies STRICT_RULES is self-contained)")
print("=" * 60)

from llm.prompts import STRICT_RULES
rules_lower = STRICT_RULES.lower()

isolation_checks = [
    ("only use information",   "Source restriction present"),
    ("never use",              "Explicit prohibition present"),
    ("cite",                   "Citation requirement present"),
    ("not available",          "Missing info instruction present"),
    ("errata",                 "Errata check present"),
    ("never guess",            "Anti-hallucination present"),
]

rules_ok = True
for phrase, desc in isolation_checks:
    found  = phrase.lower() in rules_lower
    status = "✅" if found else "⚠️ "
    print(f"  {status} {desc}")
    if not found and phrase == "only use information":
        rules_ok = False   # Only fail on the most critical one

# ── Final summary ──────────────────────────────────────────
print("\n" + "=" * 60)
print("T-18 SUMMARY")
print("=" * 60)
print(f"  Total checks run    : {total_checks}")
print(f"  Failed checks       : {len(failed_checks)}")
print(f"  Prompt length OK    : {length_ok}")

if all_passed and length_ok:
    print(f"\n  RESULT: T-18 PASS ✅")
    print(f"  All {total_checks} critical phrase checks passed.")
    print(f"  Document-only restriction confirmed in ALL prompts.")
    print(f"  Safe to proceed to Phase 4.")
else:
    print(f"\n  RESULT: T-18 FAIL ❌")
    print(f"  Fix the issues above in llm/prompts.py")
    print(f"  before proceeding to Phase 4.")

print("=" * 60)