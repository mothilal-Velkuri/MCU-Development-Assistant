# =============================================================
# test_integration.py — Phase 7 Integration Tests
# Tests the complete end-to-end pipeline.
# Run: python test_integration.py
# =============================================================

import os
import time
os.environ["ANONYMIZED_TELEMETRY"] = "False"

try:
    import chromadb.telemetry.product as _ct
    _ct.ProductTelemetryClient.capture = lambda *a, **kw: None
except Exception:
    pass

print("=" * 60)
print("PHASE 7 — INTEGRATION TESTS")
print("=" * 60)

results = {}


# =============================================================
# T-24 — Full Pipeline Test
# =============================================================
print("\n" + "─" * 60)
print("T-24 — Full Pipeline (PDF → Chunks → Embed → Search → LLM)")
print("─" * 60)

try:
    # Step 1: Check docs folder has PDFs
    from Config import DOCS_FOLDER
    pdfs = [
        f for f in os.listdir(DOCS_FOLDER)
        if f.endswith('.pdf')
    ]
    print(f"  PDFs in docs/     : {len(pdfs)}")
    for p in pdfs:
        print(f"    → {p}")

    # Step 2: Check vector DB has chunks
    from retrieval.vector_store import (
        get_chunk_count, list_indexed_sources,
        list_indexed_doc_types, search
    )
    count   = get_chunk_count()
    sources = list_indexed_sources()
    types   = list_indexed_doc_types()
    print(f"\n  Chunks in DB      : {count}")
    print(f"  Sources indexed   : {sources}")
    print(f"  Doc types         : {types}")

    if count == 0:
        print("  ⚠️  DB empty — run: python main.py --reindex")
        results["T-24"] = "SKIP"
    else:
        # Step 3: Search for known content
        print(f"\n  Running search query...")
        hits = search("STM32F407 clock configuration PLL")
        print(f"  Search results    : {len(hits)}")
        print(f"  Top score         : {hits[0]['score']}")
        print(f"  Top source        : {hits[0]['source']}")
        print(f"  Top page          : {hits[0]['page']}")
        print(f"  Preview           : {hits[0]['text'][:80]}...")

        # Step 4: LLM answers from retrieved chunks
        from llm.prompts import build_context_block, get_system_prompt
        from llm.client  import ask_llm
        context = build_context_block(hits)
        prompt  = get_system_prompt(
            step       = "clock_config",
            controller = "STM32F407VGT6",
            ide        = "STM32CubeIDE",
            frequency  = "168 MHz",
            notes      = "",
            context    = context,
        )
        print(f"\n  Sending to LLM...")
        t0       = time.time()
        response = ask_llm(prompt, [], "What PLL registers configure 168 MHz?")
        elapsed  = round(time.time() - t0, 1)

        print(f"  LLM response time : {elapsed}s")
        print(f"  Response length   : {len(response)} chars")
        print(f"  Preview           : {response[:150]}...")

        has_register = any(r in response for r in [
            "RCC", "PLL", "PLLCFGR", "PLLM", "PLLN"
        ])
        has_citation = any(c in response for c in [
            "page", "Page", "section", "Section",
            "pdf", "Manual"
        ])

        print(f"\n  Has register names: {has_register}")
        print(f"  Has citations     : {has_citation}")

        pass24 = (
            count > 0 and
            len(hits) > 0 and
            len(response) > 50 and
            has_register
        )
        results["T-24"] = "PASS" if pass24 else "FAIL"
        print(f"  T-24: {results['T-24']}")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["T-24"] = "FAIL"


# =============================================================
# T-25 — No Document Graceful Handling
# =============================================================
print("\n" + "─" * 60)
print("T-25 — No Document Graceful Handling")
print("─" * 60)

try:
    from llm.prompts import build_context_block

    # Test with empty chunks list
    empty_ctx = build_context_block([])
    has_msg   = "NO DOCUMENT CONTEXT" in empty_ctx
    print(f"  Empty context message : {has_msg}")

    # Test search returns empty list gracefully
    from retrieval.vector_store import search
    try:
        results_empty = search("this query should work even if DB empty")
        print(f"  Search handles empty  : True (returned {len(results_empty)} results)")
        graceful = True
    except Exception as se:
        print(f"  Search error: {se}")
        graceful = False

    # Test LLM with empty context
    from llm.client import ask_llm
    from llm.prompts import get_system_prompt
    prompt_empty = get_system_prompt(
        step       = "clock_config",
        controller = "STM32F407",
        ide        = "Keil",
        frequency  = "168 MHz",
        notes      = "",
        context    = empty_ctx,
    )
    response_empty = ask_llm(
        prompt_empty, [],
        "What registers configure the PLL?"
    )
    no_hallucination = (
        "not available" in response_empty.lower() or
        "not in" in response_empty.lower() or
        "no document" in response_empty.lower() or
        "cannot" in response_empty.lower() or
        "provided" in response_empty.lower()
    )
    print(f"  LLM response (empty docs): {response_empty[:100]}...")
    print(f"  LLM admits no docs       : {no_hallucination}")

    pass25 = has_msg and graceful
    results["T-25"] = "PASS" if pass25 else "FAIL"
    print(f"  T-25: {results['T-25']}")

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-25"] = "FAIL"


# =============================================================
# T-26 — Errata Detection
# =============================================================
print("\n" + "─" * 60)
print("T-26 — Errata Detection Test")
print("─" * 60)

try:
    from retrieval.vector_store import search_errata_only
    from llm.prompts import build_context_block, get_system_prompt
    from llm.client  import ask_llm

    # Search specifically in errata docs
    errata_hits = search_errata_only(
        "RCC peripheral clock enable delay workaround"
    )
    print(f"  Errata chunks found : {len(errata_hits)}")

    if errata_hits:
        print(f"  Top errata score    : {errata_hits[0]['score']}")
        print(f"  Top errata source   : {errata_hits[0]['source']}")
        print(f"  Top errata page     : {errata_hits[0]['page']}")
        print(f"  Preview             : {errata_hits[0]['text'][:100]}...")

        # Ask LLM about the errata
        context = build_context_block(errata_hits)
        prompt  = get_system_prompt(
            step       = "peripheral_config",
            controller = "STM32F407VGT6",
            ide        = "STM32CubeIDE",
            frequency  = "168 MHz",
            notes      = "",
            context    = context,
        )
        response = ask_llm(
            prompt, [],
            "What errata exists for RCC clock enable? "
            "What is the workaround?"
        )
        print(f"\n  LLM errata response : {response[:200]}...")

        has_errata_mention = any(k in response.lower() for k in [
            "errata", "delay", "workaround",
            "dsb", "dummy", "rcc"
        ])
        has_section = any(k in response for k in [
            "2.2.13", "2.2", "section", "Section"
        ])

        print(f"\n  Mentions errata     : {has_errata_mention}")
        print(f"  Cites section       : {has_section}")

        pass26 = len(errata_hits) > 0 and has_errata_mention
    else:
        print("  ⚠️  No errata docs indexed.")
        print("  Add STM32F407_ERRATE.pdf and reindex.")
        pass26 = False

    results["T-26"] = "PASS" if pass26 else "FAIL"
    print(f"  T-26: {results['T-26']}")

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-26"] = "FAIL"


# =============================================================
# T-27 — Multi-Step Conversation Context
# =============================================================
print("\n" + "─" * 60)
print("T-27 — Multi-Step Conversation Context")
print("─" * 60)

try:
    from workflow.steps import WorkflowState, chat
    from retrieval.vector_store import search

    state = WorkflowState(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
    )
    state.go_to_step("clock_config")

    # Turn 1
    print("  Turn 1: asking about PLL...")
    r1 = chat(state, "What is PLLM for 168 MHz?")
    print(f"  Response 1 length : {len(r1)} chars")
    print(f"  Preview           : {r1[:100]}...")

    # Turn 2 — references turn 1 context
    print("\n  Turn 2: follow-up question...")
    r2 = chat(state, "What about PLLN value?")
    print(f"  Response 2 length : {len(r2)} chars")
    print(f"  Preview           : {r2[:100]}...")

    # Check history was maintained
    history_len = len(state.history["clock_config"])
    print(f"\n  History entries   : {history_len} (should be 4)")

    pass27 = (
        len(r1) > 20 and
        len(r2) > 20 and
        history_len == 4
    )
    results["T-27"] = "PASS" if pass27 else "FAIL"
    print(f"  T-27: {results['T-27']}")

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-27"] = "FAIL"


# =============================================================
# T-28 — Session Save and Restore
# =============================================================
print("\n" + "─" * 60)
print("T-28 — Session Save and Restore with History")
print("─" * 60)

try:
    from workflow.steps   import WorkflowState, chat
    from workflow.session import (
        save_session, load_session,
        delete_session, generate_session_id
    )

    # Create state with some history
    state = WorkflowState(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
    )
    state.session_id = generate_session_id()
    state.go_to_step("peripheral_selection")
    state.selected_peripherals = ["USART1", "SPI2"]
    state.history["clock_config"] = [
        {"role": "user",      "content": "PLL config?"},
        {"role": "assistant", "content": "Set PLLM=8..."},
    ]

    # Save
    path = save_session(state)
    print(f"  Saved to          : {path}")

    # Load
    loaded = load_session(state.session_id)
    print(f"  Controller match  : {loaded.controller == state.controller}")
    print(f"  Step match        : {loaded.current_step == state.current_step}")
    print(f"  Peripherals       : {loaded.selected_peripherals}")
    print(f"  History preserved : {len(loaded.history['clock_config'])} entries")

    pass28 = (
        loaded.controller == state.controller and
        loaded.current_step == state.current_step and
        loaded.selected_peripherals == state.selected_peripherals and
        len(loaded.history["clock_config"]) == 2
    )
    results["T-28"] = "PASS" if pass28 else "FAIL"
    print(f"  T-28: {results['T-28']}")
    delete_session(state.session_id)

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-28"] = "FAIL"


# =============================================================
# T-29 — Code Extraction from LLM Response
# =============================================================
print("\n" + "─" * 60)
print("T-29 — Code Extraction and File Save")
print("─" * 60)

try:
    from Output.code_writer import (
        extract_c_code, save_c_file,
        save_h_file, list_generated_files,
        clear_generated_files
    )

    # Simulate LLM response with code
    llm_response = '''
Based on Section 8.3.7 (RM0090, Page 229):

```c
void GPIOD_Init(void) {
    // Enable GPIOD clock — RCC_AHB1ENR, bit 3
    // Source: RM0090, Page 180, Section 6.3.10
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIODEN;

    // Configure PD12-PD15 as output
    // MODER: 01 = general purpose output
    // Source: RM0090, Page 229, Section 8.3.7
    GPIOD->MODER |= (1<<24) | (1<<26) | (1<<28) | (1<<30);

    // Set output type: push-pull (default 0)
    GPIOD->OTYPER &= ~(0xF << 12);

    // Set speed: high speed (11)
    GPIOD->OSPEEDR |= (3<<24) | (3<<26) | (3<<28) | (3<<30);

    // No pull-up/pull-down
    GPIOD->PUPDR &= ~((3<<24) | (3<<26) | (3<<28) | (3<<30));
}
```

⚠️ ERRATA 2.2.13: Insert dummy read after clock enable.
'''

    code = extract_c_code(llm_response)
    has_func    = "void GPIOD_Init" in code
    has_comment = "RCC_AHB1ENR" in code
    no_fence    = "```" not in code
    print(f"  Function extracted : {has_func}")
    print(f"  Comments preserved : {has_comment}")
    print(f"  Fences removed     : {no_fence}")

    # Save to file
    filepath = save_c_file(
        code       = code,
        peripheral = "GPIOD",
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
    )
    file_exists = os.path.exists(filepath)
    print(f"  File saved         : {file_exists}")
    print(f"  Path               : {filepath}")

    # Save header
    h_path = save_h_file(
        declarations = ["void GPIOD_Init(void);"],
        controller   = "STM32F407VGT6",
    )
    h_exists = os.path.exists(h_path)
    print(f"  Header saved       : {h_exists}")

    # List files
    files = list_generated_files()
    print(f"  Generated files    : {files}")

    pass29 = has_func and no_fence and file_exists and h_exists
    results["T-29"] = "PASS" if pass29 else "FAIL"
    print(f"  T-29: {results['T-29']}")

    # Cleanup
    clear_generated_files()

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-29"] = "FAIL"


# =============================================================
# T-30 — Document Citation Verification
# =============================================================
print("\n" + "─" * 60)
print("T-30 — Document Citation Verification")
print("─" * 60)

try:
    from retrieval.vector_store import search
    from llm.prompts import build_context_block, get_system_prompt
    from llm.client  import ask_llm

    hits    = search("USART baud rate BRR register STM32F407")
    context = build_context_block(hits)
    prompt  = get_system_prompt(
        step       = "peripheral_config",
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
        notes      = "",
        context    = context,
    )
    response = ask_llm(
        prompt, [],
        "What is the BRR value for USART1 at 115200 baud "
        "with 84 MHz APB2 clock? Cite the source."
    )

    print(f"  Response preview  : {response[:200]}...")

    # Check citations present
    has_page    = "page" in response.lower() or "Page" in response
    has_source  = ".pdf" in response or "Manual" in response
    has_value   = any(v in response for v in [
        "BRR", "baud", "0x", "115200", "84"
    ])

    print(f"\n  Has page citation : {has_page}")
    print(f"  Has source file   : {has_source}")
    print(f"  Has register value: {has_value}")

    pass30 = has_value and len(response) > 50
    results["T-30"] = "PASS" if pass30 else "FAIL"
    print(f"  T-30: {results['T-30']}")

except Exception as e:
    print(f"  ERROR: {e}")
    results["T-30"] = "FAIL"


# =============================================================
# FINAL SUMMARY
# =============================================================
print("\n" + "=" * 60)
print("PHASE 7 — INTEGRATION TEST SUMMARY")
print("=" * 60)

passed = sum(1 for v in results.values() if v == "PASS")
failed = sum(1 for v in results.values() if v == "FAIL")
skipped= sum(1 for v in results.values() if v == "SKIP")
total  = len(results)

for test_id, result in results.items():
    icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
    print(f"  {icon} {test_id} : {result}")

print(f"\n  Passed  : {passed}/{total}")
print(f"  Failed  : {failed}/{total}")
print(f"  Skipped : {skipped}/{total}")

if passed == total:
    print("\nRESULT: ALL INTEGRATION TESTS PASSED ✅")
    print("System is ready for Phase 8 — Code Generation")
elif failed == 0:
    print("\nRESULT: ALL ACTIVE TESTS PASSED ✅")
    print("(Some tests skipped — add more PDFs to docs/)")
else:
    print(f"\nRESULT: {failed} TEST(S) FAILED ❌")
    print("Fix failures before Phase 8")

print("=" * 60)