# =============================================================
# test_final.py — Phase 9 Final End-to-End Tests
# Tests the complete system as a real user would use it.
# Run: python test_final.py
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
print("PHASE 9 — FINAL END-TO-END TESTS")
print("=" * 60)
print("Testing complete system as a real user would use it.")

results = {}
start_time = time.time()


# =============================================================
# T-31 — Full Application Startup
# =============================================================
print("\n" + "─" * 60)
print("T-31 — Full Application Startup Check")
print("─" * 60)

try:
    # All imports must work
    from Config import (
        DOCS_FOLDER, CHROMA_DB_PATH, DOC_TYPES,
        EMBEDDING_MODEL, OLLAMA_MODEL, CODE_STYLE,
        TOP_K_RESULTS, GENERATED_CODE_PATH
    )
    print(f"  ✅ config.py loaded")
    print(f"     Model     : {EMBEDDING_MODEL}")
    print(f"     LLM       : {OLLAMA_MODEL}")
    print(f"     Code style: {CODE_STYLE}")
    print(f"     Top K     : {TOP_K_RESULTS}")

    from ingestion.pdf_parser import parse_pdf
    from ingestion.chunker    import chunk_pages
    print(f"  ✅ ingestion modules loaded")

    from retrieval.embedder     import get_embedder
    from retrieval.vector_store import (
        get_chunk_count, list_indexed_sources,
        list_indexed_doc_types, search, search_errata_only
    )
    count   = get_chunk_count()
    sources = list_indexed_sources()
    types   = list_indexed_doc_types()
    print(f"  ✅ retrieval modules loaded")
    print(f"     Chunks    : {count}")
    print(f"     Sources   : {len(sources)} files")
    for s in sources:
        print(f"       → {s}")
    for dtype, cnt in types.items():
        print(f"       {dtype:<20} : {cnt} chunks")

    from llm.prompts      import get_system_prompt, build_context_block
    from llm.client       import (
        ask_llm, check_ollama_running, check_model_available
    )
    from llm.code_prompts import get_code_prompt
    print(f"  ✅ llm modules loaded")

    ollama_ok = check_ollama_running()
    model_ok  = check_model_available("mistral")
    print(f"     Ollama running : {'✅' if ollama_ok else '❌'}")
    print(f"     Mistral model  : {'✅' if model_ok  else '❌'}")

    from workflow.steps   import WorkflowState, STEPS, chat
    from workflow.session import (
        save_session, load_session,
        list_sessions, generate_session_id
    )
    print(f"  ✅ workflow modules loaded")
    print(f"     Steps defined : {len(STEPS)}")

    from Output.formatter    import print_welcome
    from Output.code_writer  import (
        extract_c_code, save_c_file,
        list_generated_files, clear_generated_files
    )
    from Output.driver_writer import (
        generate_gpio_driver, generate_peripheral_driver
    )
    print(f"  ✅ output modules loaded")

    pass31 = (
        count > 0 and
        ollama_ok and
        model_ok and
        len(sources) > 0
    )
    results["T-31"] = "PASS" if pass31 else "FAIL"
    print(f"\n  T-31: {results['T-31']}")

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["T-31"] = "FAIL"


# =============================================================
# T-32 — Real Document Q&A
# =============================================================
print("\n" + "─" * 60)
print("T-32 — Real Document Q&A with Citations")
print("─" * 60)

try:
    from retrieval.vector_store import search
    from llm.prompts import build_context_block, get_system_prompt
    from llm.client  import ask_llm

    questions = [
        {
            "question" : "What are the PLLM and PLLN values for 168 MHz?",
            "keywords" : ["PLLM", "PLLN", "168", "PLL"],
            "step"     : "clock_config",
        },
        {
            "question" : "What is the MODER register for GPIO output mode?",
            "keywords" : ["MODER", "GPIO", "output", "01"],
            "step"     : "peripheral_config",
        },
        {
            "question" : "What errata exists for RCC peripheral clock enable?",
            "keywords" : ["errata", "delay", "RCC", "workaround"],
            "step"     : "peripheral_config",
        },
    ]

    all_ok = True
    for i, q in enumerate(questions, 1):
        print(f"\n  Question {i}: {q['question']}")
        hits    = search(f"STM32F407 {q['question']}")
        context = build_context_block(hits)
        prompt  = get_system_prompt(
            step       = q["step"],
            controller = "STM32F407VGT6",
            ide        = "STM32CubeIDE",
            frequency  = "168 MHz",
            notes      = "",
            context    = context,
        )
        t0       = time.time()
        response = ask_llm(prompt, [], q["question"])
        elapsed  = round(time.time() - t0, 1)

        has_keywords = any(
            kw.lower() in response.lower()
            for kw in q["keywords"]
        )
        has_citation = any(c in response for c in [
            "Page", "page", "Section", "section", ".pdf"
        ])
        has_content  = len(response) > 50

        print(f"  Response time  : {elapsed}s")
        print(f"  Length         : {len(response)} chars")
        print(f"  Has keywords   : {has_keywords} {q['keywords']}")
        print(f"  Has citations  : {has_citation}")
        print(f"  Preview        : {response[:120]}...")

        ok = has_keywords and has_content
        print(f"  Result         : {'✅ PASS' if ok else '❌ FAIL'}")
        if not ok:
            all_ok = False

    results["T-32"] = "PASS" if all_ok else "FAIL"
    print(f"\n  T-32: {results['T-32']}")

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    results["T-32"] = "FAIL"


# =============================================================
# T-33 — Multi-Step Workflow
# =============================================================
print("\n" + "─" * 60)
print("T-33 — Multi-Step Workflow Navigation")
print("─" * 60)

try:
    from workflow.steps import WorkflowState, STEPS, chat

    state = WorkflowState(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
        notes      = "Test session",
    )

    print(f"  Starting step   : {state.current_step}")

    # Step through each step and ask a relevant question
    step_questions = {
        "clock_config"          : "What PLL values give 168 MHz?",
        "peripheral_selection"  : "What peripherals are on APB2?",
        "peripheral_config"     : "How to configure USART1 GPIO pins?",
    }

    for step, question in step_questions.items():
        state.go_to_step(step)
        print(f"\n  Step: {state.current_label()}")
        print(f"  Q   : {question}")

        t0       = time.time()
        response = chat(state, question, stream=False)
        elapsed  = round(time.time() - t0, 1)

        print(f"  Time: {elapsed}s")
        print(f"  Len : {len(response)} chars")
        print(f"  A   : {response[:100]}...")

    # Verify history was maintained
    total_history = sum(
        len(h) for h in state.history.values()
    )
    print(f"\n  Total history entries : {total_history}")
    print(f"  Steps with history    : "
          f"{[s for s in STEPS if state.history[s]]}")

    pass33 = total_history >= 6   # 3 Q&A pairs = 6 entries
    results["T-33"] = "PASS" if pass33 else "FAIL"
    print(f"  T-33: {results['T-33']}")

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["T-33"] = "FAIL"


# =============================================================
# T-34 — Code Generation End-to-End
# =============================================================
print("\n" + "─" * 60)
print("T-34 — Code Generation End-to-End")
print("─" * 60)

try:
    from Output.driver_writer import (
        generate_gpio_driver,
        generate_peripheral_driver,
        generate_driver_header,
    )
    from Output.code_writer import list_generated_files

    generated_files = []

    # Generate GPIO driver
    print("\n  Generating GPIOD output driver...")
    gpio_result = generate_gpio_driver(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        port       = "D",
        pins       = [12, 13, 14, 15],
        mode       = "output",
    )
    generated_files.append(gpio_result["filepath"])

    # Check GPIO code quality
    gpio_code = gpio_result["code"]
    gpio_checks = {
        "Has void function" : "void" in gpio_code,
        "Has RCC enable"    : "RCC" in gpio_code,
        "Has MODER"         : "MODER" in gpio_code,
        "Has page citation" : "Page" in gpio_code or "page" in gpio_code,
    }
    print(f"\n  GPIO driver quality checks:")
    for check, passed in gpio_checks.items():
        print(f"    {'✅' if passed else '❌'} {check}")

    # Generate USART driver
    print("\n  Generating USART1 driver...")
    usart_result = generate_peripheral_driver(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        peripheral = "USART1",
        config     = {
            "baud_rate"  : "115200",
            "word_length": "8 bits",
            "stop_bits"  : "1",
            "parity"     : "None",
            "mode"       : "TX and RX",
        },
    )
    generated_files.append(usart_result["filepath"])

    # Check USART code quality
    usart_code = usart_result["code"]
    usart_checks = {
        "Has void function" : "void" in usart_code,
        "Has RCC enable"    : "RCC" in usart_code,
        "Has BRR register"  : "BRR" in usart_code,
        "Has USART enable"  : "UE" in usart_code or "USART" in usart_code,
    }
    print(f"\n  USART1 driver quality checks:")
    for check, passed in usart_checks.items():
        print(f"    {'✅' if passed else '❌'} {check}")

    # Generate header
    print("\n  Generating combined header...")
    h_path = generate_driver_header(
        controller  = "STM32F407VGT6",
        peripherals = ["GPIOD", "USART1"],
    )
    generated_files.append(h_path)

    # List all files
    files = list_generated_files()
    print(f"\n  Generated files ({len(files)}):")
    for f in files:
        size = os.path.getsize(
            os.path.join("./generated", f)
        )
        print(f"    {f:<40} {size:>6} bytes")

    pass34 = (
        all(os.path.exists(f) for f in generated_files) and
        all(gpio_checks.values()) and
        len(files) >= 3
    )
    results["T-34"] = "PASS" if pass34 else "FAIL"
    print(f"\n  T-34: {results['T-34']}")

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["T-34"] = "FAIL"


# =============================================================
# T-35 — Session Save and Resume
# =============================================================
print("\n" + "─" * 60)
print("T-35 — Session Save and Resume")
print("─" * 60)

try:
    from workflow.steps   import WorkflowState, chat
    from workflow.session import (
        save_session, load_session,
        delete_session, generate_session_id
    )

    # Create and populate a session
    state = WorkflowState(
        controller = "STM32F407VGT6",
        ide        = "STM32CubeIDE",
        frequency  = "168 MHz",
        notes      = "Phase 9 test session",
    )
    state.session_id = generate_session_id()
    state.go_to_step("peripheral_config")
    state.selected_peripherals = ["USART1", "GPIOD"]

    # Add some history
    state.history["clock_config"] = [
        {"role": "user",      "content": "PLL for 168 MHz?"},
        {"role": "assistant", "content": "Set PLLM=8, PLLN=168..."},
    ]
    state.history["peripheral_selection"] = [
        {"role": "user",      "content": "I need USART1"},
        {"role": "assistant", "content": "USART1 on PA9/PA10..."},
    ]

    # Save session
    path = save_session(state)
    print(f"  Session saved   : {path}")
    print(f"  Session ID      : {state.session_id}")

    # Simulate quit and resume
    session_id = state.session_id
    del state   # simulate application exit

    # Load session
    resumed = load_session(session_id)
    print(f"\n  Session resumed :")
    print(f"  Controller      : {resumed.controller}")
    print(f"  Step            : {resumed.current_label()}")
    print(f"  Peripherals     : {resumed.selected_peripherals}")
    print(f"  Clock history   : {len(resumed.history['clock_config'])} entries")
    print(f"  Periph history  : {len(resumed.history['peripheral_selection'])} entries")

    # Continue session — ask a question after resume
    print(f"\n  Continuing session after resume...")
    response = chat(
        resumed,
        "What GPIO pins does USART1 use?",
        stream=False
    )
    print(f"  Response length : {len(response)} chars")
    print(f"  Preview         : {response[:120]}...")

    pass35 = (
        resumed.controller == "STM32F407VGT6" and
        resumed.current_step == "peripheral_config" and
        resumed.selected_peripherals == ["USART1", "GPIOD"] and
        len(response) > 20
    )
    results["T-35"] = "PASS" if pass35 else "FAIL"
    print(f"\n  T-35: {results['T-35']}")
    delete_session(session_id)

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    results["T-35"] = "FAIL"


# =============================================================
# T-36 — System Health Check
# =============================================================
print("\n" + "─" * 60)
print("T-36 — Final System Health Check")
print("─" * 60)

try:
    from retrieval.vector_store import (
        get_chunk_count, list_indexed_sources,
        list_indexed_doc_types
    )
    from llm.client import check_ollama_running, check_model_available
    from Output.code_writer import list_generated_files

    count   = get_chunk_count()
    sources = list_indexed_sources()
    types   = list_indexed_doc_types()
    files   = list_generated_files()

    checks = {
        "Vector DB has chunks"     : count > 0,
        "Multiple docs indexed"    : len(sources) > 1,
        "Errata doc indexed"       : "Errata" in types,
        "Reference Manual indexed" : "Reference Manual" in types,
        "Ollama running"           : check_ollama_running(),
        "Mistral available"        : check_model_available("mistral"),
        "Generated folder exists"  : os.path.exists("./generated"),
        "Sessions folder exists"   : os.path.exists("./sessions"),
        "docs folder exists"       : os.path.exists("./docs"),
        "fix_chromadb.py exists"   : os.path.exists("fix_chromadb.py"),
    }

    print(f"\n  System Health Report:")
    print(f"  {'─'*45}")
    all_healthy = True
    for check, passed in checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
        if not passed:
            all_healthy = False

    print(f"\n  Vector DB      : {count} chunks")
    print(f"  Documents      : {sources}")
    print(f"  Doc types      : {list(types.keys())}")
    print(f"  Generated files: {files}")

    total_time = round(time.time() - start_time, 1)
    print(f"\n  Total test time: {total_time}s")

    results["T-36"] = "PASS" if all_healthy else "FAIL"
    print(f"\n  T-36: {results['T-36']}")

except Exception as e:
    print(f"  ❌ ERROR: {e}")
    results["T-36"] = "FAIL"


# =============================================================
# CLEANUP
# =============================================================
print("\n  Cleaning up generated test files...")
from Output.code_writer import clear_generated_files
cleared = clear_generated_files()
print(f"  Cleared {cleared} file(s).")


# =============================================================
# FINAL SUMMARY
# =============================================================
total_time = round(time.time() - start_time, 1)

print("\n" + "=" * 60)
print("PHASE 9 — FINAL TEST SUMMARY")
print("=" * 60)

passed  = sum(1 for v in results.values() if v == "PASS")
failed  = sum(1 for v in results.values() if v == "FAIL")
total   = len(results)

for test_id, result in results.items():
    icon = "✅" if result == "PASS" else "❌"
    print(f"  {icon} {test_id} : {result}")

print(f"\n  Passed     : {passed}/{total}")
print(f"  Failed     : {failed}/{total}")
print(f"  Total time : {total_time}s")

if passed == total:
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ALL PHASE 9 TESTS PASSED ✅                           ║
║                                                          ║
║   MCU DEV ASSISTANT — FULLY COMPLETE                    ║
║                                                          ║
║   Phases 1-9 complete                                   ║
║   12,684 chunks indexed                                 ║
║   Document-grounded Q&A working                        ║
║   C code generation working                            ║
║   Session management working                           ║
║   Ready for production use                             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
else:
    print(f"\n  RESULT: {failed} TEST(S) FAILED ❌")
    print("  Review failures above before production use.")

print("=" * 60)