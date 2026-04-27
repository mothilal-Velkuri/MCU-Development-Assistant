# test_output.py — Phase 5 Tests
# Run: python test_output.py

import os
from Output.formatter import (
    print_welcome, print_session_header, print_step_banner,
    print_response, format_response, print_error,
    print_success, print_info, print_warning,
    print_help, print_sources, print_user_message,
    print_index_summary,
)
from Output.code_writer import (
    save_c_file, save_h_file, extract_c_code,
    list_generated_files, clear_generated_files,
    _sanitize_name,
)

print("=" * 55)
print("OUTPUT LAYER TEST — Formatter + Code Writer")
print("=" * 55)

# ── Test 1: Welcome screen ─────────────────────────────────
print("\nTest 1 — Welcome screen renders")
try:
    print_welcome()
    print("  PASS ✅")
    pass1 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass1 = False

# ── Test 2: Session header ─────────────────────────────────
print("\nTest 2 — Session header renders")
try:
    print_session_header(
        controller   = "STM32F407VGT6",
        ide          = "STM32CubeIDE",
        frequency    = "168 MHz",
        docs_indexed = 429,
        step_label   = "02 · Clock Configuration",
    )
    print("  PASS ✅")
    pass2 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass2 = False

# ── Test 3: Step banner ────────────────────────────────────
print("\nTest 3 — Step banner renders")
try:
    print_step_banner("03 · Peripheral Selection", "3 of 5")
    print("  PASS ✅")
    pass3 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass3 = False

# ── Test 4: Q&A response formatting ───────────────────────
print("\nTest 4 — Q&A response formatting")
try:
    format_response(
        "Based on Section 6.3.2 (RM0090.pdf, Page 148):\n"
        "Set PLLM = 8, PLLN = 168, PLLP = 0 (divide by 2).\n"
        "The RCC_PLLCFGR register must be configured before\n"
        "enabling the PLL. Flash latency: 5 wait states.",
        step = "Clock Configuration"
    )
    print("  PASS ✅")
    pass4 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass4 = False

# ── Test 5: Errata response formatting ────────────────────
print("\nTest 5 — Errata warning formatting")
try:
    format_response(
        "⚠️ ERRATA 2.2.13: Delay after RCC peripheral clock\n"
        "enabling (STM32F407_ERRATE.pdf, Page 12).\n"
        "Workaround: Insert DSB instruction or dummy read\n"
        "after enabling peripheral clock.",
        step = "Clock Configuration"
    )
    print("  PASS ✅")
    pass5 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass5 = False

# ── Test 6: Info/Error/Warning messages ───────────────────
print("\nTest 6 — Message types")
try:
    print_success("Session saved successfully")
    print_error("Vector DB is empty")
    print_warning("Errata document not indexed")
    print_info("Add more PDFs to docs/ for better results")
    print("  PASS ✅")
    pass6 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass6 = False

# ── Test 7: Help display ───────────────────────────────────
print("\nTest 7 — Help panel")
try:
    print_help("Clock Configuration")
    print("  PASS ✅")
    pass7 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass7 = False

# ── Test 8: Source list display ───────────────────────────
print("\nTest 8 — Sources display")
try:
    sample_chunks = [
        {"source": "RM0090.pdf",           "page": 148,
         "doc_type": "Reference Manual",   "score": 0.92},
        {"source": "STM32F407_ERRATE.pdf", "page": 12,
         "doc_type": "Errata",             "score": 0.78},
        {"source": "RM0090.pdf",           "page": 152,
         "doc_type": "Reference Manual",   "score": 0.71},
    ]
    print_sources(sample_chunks)
    print("  PASS ✅")
    pass8 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass8 = False

# ── Test 9: Index summary ──────────────────────────────────
print("\nTest 9 — Index summary display")
try:
    print_index_summary(
        sources        = ["RM0090.pdf", "STM32F407_ERRATE.pdf"],
        doc_type_counts= {"Reference Manual": 850, "Errata": 429},
        total_chunks   = 1279,
    )
    print("  PASS ✅")
    pass9 = True
except Exception as e:
    print(f"  FAIL ❌ — {e}")
    pass9 = False

# ── Test 10: Name sanitizer ────────────────────────────────
print("\nTest 10 — Filename sanitizer")
cases = [
    ("USART1",          "usart1"),
    ("SPI @ 10MHz",     "spi_10mhz"),
    ("I2C-1 sensor",    "i2c_1_sensor"),
    ("clock config",    "clock_config"),
]
all_ok = True
for input_name, expected in cases:
    result = _sanitize_name(input_name)
    ok     = result == expected
    print(f"  '{input_name}' → '{result}' "
          f"{'✅' if ok else f'❌ expected {expected}'}")
    if not ok:
        all_ok = False
pass10 = all_ok
print(f"  PASS ✅" if pass10 else "  FAIL ❌")

# ── Test 11: C code extraction ────────────────────────────
print("\nTest 11 — C code extraction from LLM response")
llm_with_fence = """
Here is the initialization code:

```c
void USART1_Init(void) {
    // Enable USART1 clock — RCC_APB2ENR, bit 4, Page 148
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    // Set baud rate — BRR register, Page 871
    USART1->BRR = 0x0683;
    // Enable USART — CR1 register, UE bit
    USART1->CR1 |= USART_CR1_UE;
}
```

The above code enables USART1 at 115200 baud.
"""
extracted = extract_c_code(llm_with_fence)
has_func    = "void USART1_Init" in extracted
has_comment = "RCC_APB2ENR" in extracted
no_fence    = "```" not in extracted
print(f"  Function found   : {has_func}")
print(f"  Comments present : {has_comment}")
print(f"  Fences removed   : {no_fence}")
pass11 = has_func and has_comment and no_fence
print(f"  PASS ✅" if pass11 else "  FAIL ❌")

# ── Test 12: Save C file ───────────────────────────────────
print("\nTest 12 — Save C code file")
test_code = """
void USART1_Test_Init(void) {
    // Test initialization — Section 27.3.2, Page 871
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    USART1->BRR   = 0x0683;
    USART1->CR1  |= USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}
"""
filepath = save_c_file(
    code       = test_code,
    peripheral = "USART1 Test",
    controller = "STM32F407VGT6",
    ide        = "STM32CubeIDE",
)
exists    = os.path.exists(filepath)
has_hdr   = "MCU Dev Assistant" in open(filepath).read()
print(f"  File created     : {exists}")
print(f"  Has file header  : {has_hdr}")
print(f"  Path             : {filepath}")
pass12 = exists and has_hdr
print(f"  PASS ✅" if pass12 else "  FAIL ❌")

# ── Test 13: Save H file ───────────────────────────────────
print("\nTest 13 — Save combined header file")
h_filepath = save_h_file(
    declarations = [
        "void Clock_Init(void);",
        "void USART1_Init(void);",
        "void SPI2_Init(void);",
    ],
    controller = "STM32F407VGT6",
)
h_exists  = os.path.exists(h_filepath)
h_content = open(h_filepath).read()
has_guard = "#ifndef MCU_CONFIG_H" in h_content
has_decl  = "void USART1_Init(void);" in h_content
print(f"  File created     : {h_exists}")
print(f"  Has include guard: {has_guard}")
print(f"  Has declarations : {has_decl}")
pass13 = h_exists and has_guard and has_decl
print(f"  PASS ✅" if pass13 else "  FAIL ❌")

# ── Test 14: List generated files ─────────────────────────
print("\nTest 14 — List generated files")
files = list_generated_files()
print(f"  Files found : {files}")
pass14 = len(files) >= 2
print(f"  PASS ✅" if pass14 else "  FAIL ❌")

# ── Test 15: Clear generated files ────────────────────────
print("\nTest 15 — Clear generated files")
count = clear_generated_files()
remaining = list_generated_files()
print(f"  Deleted count   : {count}")
print(f"  Remaining files : {remaining}")
pass15 = count >= 2 and len(remaining) == 0
print(f"  PASS ✅" if pass15 else "  FAIL ❌")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
results = [
    pass1,  pass2,  pass3,  pass4,  pass5,
    pass6,  pass7,  pass8,  pass9,  pass10,
    pass11, pass12, pass13, pass14, pass15,
]
passed = sum(results)
total  = len(results)
print(f"  Tests passed : {passed}/{total}")
print("RESULT: output layer OK ✅" if passed == total
      else f"RESULT: output PARTIAL — {total-passed} failed ❌")
print("=" * 55)