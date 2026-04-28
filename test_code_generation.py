# =============================================================
# test_code_generation.py — Phase 8 Tests
# Run: python test_code_generation.py
# =============================================================

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
try:
    import chromadb.telemetry.product as _ct
    _ct.ProductTelemetryClient.capture = lambda *a, **kw: None
except Exception:
    pass

print("=" * 55)
print("PHASE 8 — CODE GENERATION TESTS")
print("=" * 55)

from Output.driver_writer import (
    generate_clock_driver,
    generate_gpio_driver,
    generate_peripheral_driver,
    generate_driver_header,
)
from Output.code_writer import (
    list_generated_files,
    clear_generated_files,
    extract_c_code,
)
from llm.code_prompts import get_code_prompt
from retrieval.vector_store import get_chunk_count

results = {}

# ── Check DB has content ───────────────────────────────────
count = get_chunk_count()
print(f"\n  Chunks in DB: {count}")
if count == 0:
    print("  ⚠️  DB empty — run: python main.py --reindex")
    exit()

# ── Test 1: Code prompts build correctly ──────────────────
print("\n" + "─" * 55)
print("Test 1 — Code prompts build correctly")
print("─" * 55)

from retrieval.vector_store import search
from llm.prompts import build_context_block

hits    = search("STM32F407 clock PLL configuration")
context = build_context_block(hits)

try:
    prompts_to_test = {
        "clock"     : {"frequency": "168 MHz"},
        "gpio"      : {"port": "D", "pins": [12,13,14,15], "mode": "output"},
        "peripheral": {"peripheral": "USART1", "config": {"baud_rate": "115200"}},
        "header"    : {"peripherals": ["USART1", "SPI2"]},
    }
    all_ok = True
    for ptype, kwargs in prompts_to_test.items():
        p = get_code_prompt(
            prompt_type = ptype,
            controller  = "STM32F407VGT6",
            ide         = "STM32CubeIDE",
            context     = context,
            **kwargs
        )
        has_rules   = "CODE GENERATION" in p
        has_context = "RETRIEVED DOCUMENT" in p
        ok = has_rules and has_context and len(p) > 300
        print(f"  {ptype:<12} : {'✅' if ok else '❌'} ({len(p)} chars)")
        if not ok:
            all_ok = False
    results["Test 1"] = "PASS" if all_ok else "FAIL"
    print(f"  Result: {results['Test 1']}")
except Exception as e:
    print(f"  ERROR: {e}")
    results["Test 1"] = "FAIL"

# ── Test 2: GPIO driver generation ────────────────────────
print("\n" + "─" * 55)
print("Test 2 — GPIO driver generation")
print("─" * 55)

try:
    result = generate_gpio_driver(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        port       = "D",
        pins       = [12, 13, 14, 15],
        mode       = "output",
    )
    code     = result["code"]
    filepath = result["filepath"]

    has_func    = "void GPIO" in code
    has_rcc     = "RCC" in code
    has_moder   = "MODER" in code
    file_exists = os.path.exists(filepath)

    print(f"  File saved      : {file_exists}")
    print(f"  Has GPIO func   : {has_func}")
    print(f"  Has RCC enable  : {has_rcc}")
    print(f"  Has MODER reg   : {has_moder}")
    print(f"  Chunks used     : {result['chunks_used']}")
    print(f"  Code preview    :")
    for line in code.split("\n")[:10]:
        print(f"    {line}")

    pass2 = has_func and file_exists
    results["Test 2"] = "PASS" if pass2 else "FAIL"
    print(f"  Result: {results['Test 2']}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["Test 2"] = "FAIL"

# ── Test 3: Clock driver generation ───────────────────────
print("\n" + "─" * 55)
print("Test 3 — Clock driver generation")
print("─" * 55)

try:
    result = generate_clock_driver(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
    )
    code     = result["code"]
    filepath = result["filepath"]

    has_func    = "void" in code and "Clock" in code or "clock" in code
    has_pll     = "PLL" in code or "pll" in code.lower()
    has_rcc     = "RCC" in code
    file_exists = os.path.exists(filepath)

    print(f"  File saved      : {file_exists}")
    print(f"  Has clock func  : {has_func}")
    print(f"  Has PLL config  : {has_pll}")
    print(f"  Has RCC         : {has_rcc}")
    print(f"  Code length     : {len(code)} chars")

    pass3 = has_rcc and file_exists
    results["Test 3"] = "PASS" if pass3 else "FAIL"
    print(f"  Result: {results['Test 3']}")
except Exception as e:
    print(f"  ERROR: {e}")
    results["Test 3"] = "FAIL"

# ── Test 4: USART peripheral driver ───────────────────────
print("\n" + "─" * 55)
print("Test 4 — USART1 peripheral driver generation")
print("─" * 55)

try:
    result = generate_peripheral_driver(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        peripheral = "USART1",
        config     = {
            "baud_rate"  : "115200",
            "word_length": "8 bits",
            "stop_bits"  : "1",
            "parity"     : "None",
        },
    )
    code     = result["code"]
    filepath = result["filepath"]

    has_func    = "void" in code and "USART" in code
    has_brr     = "BRR" in code or "baud" in code.lower()
    has_rcc     = "RCC" in code
    file_exists = os.path.exists(filepath)

    print(f"  File saved      : {file_exists}")
    print(f"  Has USART func  : {has_func}")
    print(f"  Has BRR/baud    : {has_brr}")
    print(f"  Has RCC         : {has_rcc}")
    print(f"  Code length     : {len(code)} chars")
    print(f"  Code preview    :")
    for line in code.split("\n")[:12]:
        print(f"    {line}")

    pass4 = has_func and file_exists
    results["Test 4"] = "PASS" if pass4 else "FAIL"
    print(f"  Result: {results['Test 4']}")
except Exception as e:
    print(f"  ERROR: {e}")
    results["Test 4"] = "FAIL"

# ── Test 5: Header file generation ────────────────────────
print("\n" + "─" * 55)
print("Test 5 — Combined header file generation")
print("─" * 55)

try:
    h_path = generate_driver_header(
        controller  = "STM32F407VGT6",
        peripherals = ["USART1", "SPI2", "GPIOD", "clock_config"],
    )
    h_content   = open(h_path).read()
    has_guard   = "#ifndef" in h_content
    has_usart   = "USART" in h_content
    has_defines = "MCU_OK" in h_content or "define" in h_content
    h_exists    = os.path.exists(h_path)

    print(f"  File saved      : {h_exists}")
    print(f"  Has include guard: {has_guard}")
    print(f"  Has USART decl  : {has_usart}")
    print(f"  Has defines     : {has_defines}")
    print(f"  Header preview  :")
    for line in h_content.split("\n")[:15]:
        print(f"    {line}")

    pass5 = h_exists and has_guard
    results["Test 5"] = "PASS" if pass5 else "FAIL"
    print(f"  Result: {results['Test 5']}")
except Exception as e:
    print(f"  ERROR: {e}")
    results["Test 5"] = "FAIL"

# ── Test 6: List all generated files ──────────────────────
print("\n" + "─" * 55)
print("Test 6 — List all generated files")
print("─" * 55)

files = list_generated_files()
print(f"  Generated files ({len(files)}):")
for f in files:
    size = os.path.getsize(
        os.path.join("./generated", f)
    )
    print(f"    {f:<35} {size} bytes")

results["Test 6"] = "PASS" if len(files) >= 3 else "FAIL"
print(f"  Result: {results['Test 6']}")

# ── Cleanup ────────────────────────────────────────────────
print("\n  Cleaning up generated files...")
clear_generated_files()

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
print("PHASE 8 — CODE GENERATION TEST SUMMARY")
print("=" * 55)

passed = sum(1 for v in results.values() if v == "PASS")
total  = len(results)

for name, result in results.items():
    icon = "✅" if result == "PASS" else "❌"
    print(f"  {icon} {name} : {result}")

print(f"\n  Passed : {passed}/{total}")

if passed == total:
    print("\nRESULT: ALL CODE GENERATION TESTS PASSED ✅")
    print("Phase 8 complete — Code generation working.")
else:
    print(f"\nRESULT: {total-passed} TEST(S) FAILED ❌")

print("=" * 55)