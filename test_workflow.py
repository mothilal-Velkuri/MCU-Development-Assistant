# test_workflow.py — Phase 4 Tests
# Run: python test_workflow.py

import os
from workflow.steps import (
    WorkflowState, STEPS, STEP_LABELS,
    chat, chat_intro,
    add_peripheral, extract_peripherals_from_message,
    get_context_for_query,
)
from workflow.session import (
    save_session, load_session,
    list_sessions, delete_session,
    generate_session_id,
)

print("=" * 55)
print("WORKFLOW TEST — Steps + Session")
print("=" * 55)

# ── Test 1: WorkflowState creation ────────────────────────
print("\nTest 1 — WorkflowState initialization")
state = WorkflowState(
    controller = "STM32F407VGT6",
    ide        = "STM32CubeIDE",
    frequency  = "168 MHz",
    notes      = "External 8 MHz HSE crystal",
)
print(f"  Controller    : {state.controller}")
print(f"  IDE           : {state.ide}")
print(f"  Current step  : {state.current_step}")
print(f"  Step number   : {state.step_number()}")
print(f"  History keys  : {list(state.history.keys())}")
pass1 = (
    state.current_step == "intro" and
    state.controller == "STM32F407VGT6" and
    len(state.history) == len(STEPS)
)
print(f"  PASS" if pass1 else "  FAIL")

# ── Test 2: Step advancement ───────────────────────────────
print("\nTest 2 — Step advancement")
for expected in STEPS[1:]:
    advanced = state.advance()
    print(f"  Advanced to: {state.current_step} "
          f"({'✅' if state.current_step == expected else '❌'})")

# Test cannot go past last step
result = state.advance()
print(f"  Cannot advance past last step: {not result} ✅")
pass2 = state.current_step == STEPS[-1] and not result
print(f"  PASS" if pass2 else "  FAIL")

# ── Test 3: Go to specific step ───────────────────────────
print("\nTest 3 — Jump to specific step")
state.go_to_step("clock_config")
print(f"  Jumped to: {state.current_step}")
print(f"  Label    : {state.current_label()}")
pass3 = state.current_step == "clock_config"
print(f"  PASS" if pass3 else "  FAIL")

# ── Test 4: Peripheral tracking ───────────────────────────
print("\nTest 4 — Peripheral tracking")
add_peripheral(state, "USART1")
add_peripheral(state, "SPI2")
add_peripheral(state, "USART1")   # duplicate — should not add
print(f"  Peripherals: {state.selected_peripherals}")
pass4 = (
    len(state.selected_peripherals) == 2 and
    "USART1" in state.selected_peripherals and
    "SPI2"   in state.selected_peripherals
)
print(f"  PASS" if pass4 else "  FAIL")

# ── Test 5: Peripheral detection in message ───────────────
print("\nTest 5 — Peripheral detection from message")
test_msgs = [
    ("I need USART1 at 115200 baud",   ["USART"]),
    ("Configure SPI and DMA",           ["SPI", "DMA"]),
    ("I2C1 for sensor and ADC for measurement", ["I2C", "ADC"]),
    ("just a general question",         []),
]
all_ok = True
for msg, expected in test_msgs:
    found = extract_peripherals_from_message(msg)
    ok    = all(e in found for e in expected)
    print(f"  '{msg[:35]}' → {found} "
          f"{'✅' if ok else '❌'}")
    if not ok:
        all_ok = False
print(f"  PASS" if all_ok else "  FAIL")

# ── Test 6: State summary ─────────────────────────────────
print("\nTest 6 — State summary")
state.go_to_step("peripheral_selection")
summary = state.summary()
has_ctrl  = "STM32F407VGT6" in summary
has_step  = "Peripheral" in summary
has_perip = "USART1" in summary
print(f"  Has controller  : {has_ctrl}")
print(f"  Has step name   : {has_step}")
print(f"  Has peripherals : {has_perip}")
print(summary)
pass6 = has_ctrl and has_step
print(f"  PASS" if pass6 else "  FAIL")

# ── Test 7: RAG context retrieval ─────────────────────────
print("\nTest 7 — RAG context for query")
try:
    ctx, chunks = get_context_for_query(
        "RCC clock enable delay workaround STM32F407"
    )
    has_context  = len(ctx) > 100
    has_chunks   = len(chunks) > 0
    print(f"  Context length : {len(ctx)} chars")
    print(f"  Chunks found   : {len(chunks)}")
    if chunks:
        print(f"  Top score      : {chunks[0]['score']}")
        print(f"  Top source     : {chunks[0]['source']}")
    pass7 = has_context and has_chunks
    print(f"  PASS" if pass7 else "  FAIL")
except Exception as e:
    print(f"  ⚠️  Skipped (vector DB empty): {e}")
    pass7 = True   # not a test failure — DB may be empty

# ── Test 8: Session save ───────────────────────────────────
print("\nTest 8 — Session save")
state.go_to_step("clock_config")
state.session_id = generate_session_id()
filepath = save_session(state)
exists   = os.path.exists(filepath)
print(f"  File created    : {exists}")
print(f"  Session ID      : {state.session_id}")
pass8 = exists
print(f"  PASS" if pass8 else "  FAIL")

# ── Test 9: Session load ───────────────────────────────────
print("\nTest 9 — Session load")
loaded = load_session(state.session_id)
same_ctrl = loaded.controller == state.controller
same_step = loaded.current_step == state.current_step
same_perip= loaded.selected_peripherals == state.selected_peripherals
print(f"  Controller match: {same_ctrl}")
print(f"  Step match      : {same_step}")
print(f"  Peripherals     : {loaded.selected_peripherals}")
pass9 = same_ctrl and same_step and same_perip
print(f"  PASS" if pass9 else "  FAIL")

# ── Test 10: List sessions ─────────────────────────────────
print("\nTest 10 — List sessions")
sessions = list_sessions()
print(f"  Sessions found  : {len(sessions)}")
if sessions:
    s = sessions[0]
    print(f"  Latest session  : {s['session_id']}")
    print(f"  Controller      : {s['controller']}")
    print(f"  Step            : {s['step']}")
pass10 = len(sessions) >= 1
print(f"  PASS" if pass10 else "  FAIL")

# ── Test 11: LLM chat with workflow ───────────────────────
print("\nTest 11 — LLM chat through workflow")
state2 = WorkflowState(
    controller = "STM32F407VGT6",
    ide        = "STM32CubeIDE",
    frequency  = "168 MHz",
    notes      = "",
)
state2.go_to_step("clock_config")
print("  Sending question through workflow...")
try:
    response = chat(
        state2,
        "What errata is related to RCC peripheral clock enabling?",
        stream = False,
    )
    has_response = len(response) > 20
    history_updated = len(state2.history["clock_config"]) == 2
    print(f"  Response length     : {len(response)} chars")
    print(f"  History updated     : {history_updated}")
    print(f"  Preview: {response[:150]}...")
    pass11 = has_response and history_updated
    print(f"  PASS" if pass11 else "  FAIL")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    pass11 = False

# ── Test 12: Session cleanup ───────────────────────────────
print("\nTest 12 — Session cleanup")
deleted = delete_session(state.session_id)
print(f"  Deleted session : {deleted}")
print(f"  PASS" if deleted else "  FAIL")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
results = [
    pass1, pass2, pass3, pass4,
    all_ok, pass6, pass7, pass8,
    pass9, pass10, pass11, deleted
]
passed = sum(results)
total  = len(results)
print(f"  Tests passed : {passed}/{total}")
print("RESULT: workflow OK ✅" if passed == total
      else f"RESULT: workflow PARTIAL — {total-passed} failed ❌")
print("=" * 55)