# test_session.py — Phase 4 Session Tests
# Run: python test_session.py

import os
import json
from workflow.steps import WorkflowState
from workflow.session import (
    save_session, load_session,
    list_sessions, delete_session,
    generate_session_id,
)

print("=" * 55)
print("SESSION.PY TEST")
print("=" * 55)

# ── Test 1: Session ID generation ─────────────────────────
print("\nTest 1 — Session ID generation")
id1 = generate_session_id()
id2 = generate_session_id()
print(f"  ID 1 : {id1}")
print(f"  ID 2 : {id2}")
print(f"  Unique    : {id1 != id2}")
print(f"  Has prefix: {'session_' in id1}")
pass1 = id1 != id2 and id1.startswith("session_")
print(f"  PASS" if pass1 else "  FAIL")

# ── Test 2: Save full session ──────────────────────────────
print("\nTest 2 — Save complete session state")
state = WorkflowState(
    controller           = "STM32F407VGT6",
    ide                  = "STM32CubeIDE",
    frequency            = "168 MHz",
    notes                = "External 8 MHz HSE crystal",
    current_step         = "clock_config",
    selected_peripherals = ["USART1", "SPI2", "I2C1"],
    docs_indexed         = 429,
)
state.session_id = generate_session_id()

# Add some conversation history
state.history["clock_config"] = [
    {"role": "user",      "content": "How to configure PLL?"},
    {"role": "assistant", "content": "Set PLLN=168, PLLM=8..."},
    {"role": "user",      "content": "What about flash latency?"},
    {"role": "assistant", "content": "Set 5 wait states..."},
]
state.history["peripheral_selection"] = [
    {"role": "user",      "content": "I need USART1"},
    {"role": "assistant", "content": "USART1 is on APB2..."},
]

filepath = save_session(state)
print(f"  Saved to  : {filepath}")
print(f"  File exists: {os.path.exists(filepath)}")

# Verify JSON content
with open(filepath, "r") as f:
    saved = json.load(f)

has_controller = saved["controller"] == "STM32F407VGT6"
has_history    = len(saved["history"]["clock_config"]) == 4
has_peripherals= len(saved["selected_peripherals"]) == 3
has_docs       = saved["docs_indexed"] == 429
print(f"  Controller saved : {has_controller}")
print(f"  History saved    : {has_history} (4 messages)")
print(f"  Peripherals saved: {has_peripherals} (3 items)")
print(f"  Docs count saved : {has_docs} (429)")
pass2 = all([has_controller, has_history, has_peripherals, has_docs])
print(f"  PASS" if pass2 else "  FAIL")

# ── Test 3: Load session exactly ──────────────────────────
print("\nTest 3 — Load session and verify all fields")
loaded = load_session(state.session_id)
checks = {
    "controller"    : loaded.controller == state.controller,
    "ide"           : loaded.ide == state.ide,
    "frequency"     : loaded.frequency == state.frequency,
    "notes"         : loaded.notes == state.notes,
    "current_step"  : loaded.current_step == state.current_step,
    "peripherals"   : loaded.selected_peripherals == state.selected_peripherals,
    "docs_indexed"  : loaded.docs_indexed == state.docs_indexed,
    "session_id"    : loaded.session_id == state.session_id,
    "clock_history" : (
        len(loaded.history["clock_config"]) ==
        len(state.history["clock_config"])
    ),
    "periph_history": (
        len(loaded.history["peripheral_selection"]) ==
        len(state.history["peripheral_selection"])
    ),
}
for field_name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {field_name}")
pass3 = all(checks.values())
print(f"  PASS" if pass3 else "  FAIL")

# ── Test 4: Save second session ───────────────────────────
print("\nTest 4 — Multiple sessions")
state2 = WorkflowState(
    controller   = "PIC32MX795",
    ide          = "MPLAB X",
    frequency    = "80 MHz",
    current_step = "peripheral_selection",
)
state2.session_id = generate_session_id()
save_session(state2)

sessions = list_sessions()
print(f"  Sessions in folder: {len(sessions)}")
controllers = [s["controller"] for s in sessions]
print(f"  Controllers found : {controllers}")
has_stm32 = "STM32F407VGT6" in controllers
has_pic   = "PIC32MX795" in controllers
print(f"  Has STM32 session : {has_stm32}")
print(f"  Has PIC session   : {has_pic}")
pass4 = has_stm32 and has_pic and len(sessions) >= 2
print(f"  PASS" if pass4 else "  FAIL")

# ── Test 5: Sessions sorted newest first ──────────────────
print("\nTest 5 — Sessions sorted newest first")
sessions = list_sessions()
if len(sessions) >= 2:
    newest = sessions[0]["saved_at"]
    oldest = sessions[-1]["saved_at"]
    sorted_ok = newest >= oldest
    print(f"  Newest: {newest}")
    print(f"  Oldest: {oldest}")
    print(f"  Correctly sorted: {sorted_ok}")
    print(f"  PASS" if sorted_ok else "  FAIL")
    pass5 = sorted_ok
else:
    print("  Only one session — skipping sort check")
    pass5 = True

# ── Test 6: Load non-existent session ─────────────────────
print("\nTest 6 — Load non-existent session raises error")
try:
    load_session("session_does_not_exist_xyz")
    print("  FAIL — should have raised FileNotFoundError")
    pass6 = False
except FileNotFoundError as e:
    print(f"  FileNotFoundError raised correctly")
    print(f"  Message: {str(e)[:60]}")
    pass6 = True
    print(f"  PASS")

# ── Test 7: Delete sessions ───────────────────────────────
print("\nTest 7 — Delete sessions")
del1 = delete_session(state.session_id)
del2 = delete_session(state2.session_id)
del3 = delete_session("nonexistent_session")
print(f"  Deleted session 1 : {del1}")
print(f"  Deleted session 2 : {del2}")
print(f"  Delete nonexistent: {del3} (should be False)")
sessions_after = list_sessions()
print(f"  Sessions remaining: {len(sessions_after)}")
pass7 = del1 and del2 and not del3
print(f"  PASS" if pass7 else "  FAIL")

# ── Test 8: Session step label ────────────────────────────
print("\nTest 8 — Loaded session has correct step label")
state3 = WorkflowState(
    controller   = "STM32F407",
    ide          = "Keil",
    frequency    = "168 MHz",
    current_step = "peripheral_config",
)
state3.session_id = generate_session_id()
save_session(state3)
loaded3 = load_session(state3.session_id)
label = loaded3.current_label()
print(f"  Step      : {loaded3.current_step}")
print(f"  Label     : {label}")
pass8 = "Peripheral Configuration" in label
print(f"  PASS" if pass8 else "  FAIL")
delete_session(state3.session_id)

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
results = [pass1, pass2, pass3, pass4, pass5, pass6, pass7, pass8]
passed  = sum(results)
total   = len(results)
print(f"  Tests passed : {passed}/{total}")
print("RESULT: session.py OK ✅" if passed == total
      else f"RESULT: session.py FAILED — {total-passed} failed ❌")
print("=" * 55)