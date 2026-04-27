# test_main.py — Phase 6 Smoke Test
# Tests that main.py imports and functions are accessible.
# Does NOT run the full interactive CLI.
# Run: python test_main.py

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

print("=" * 55)
print("MAIN.PY SMOKE TEST — Phase 6")
print("=" * 55)

# ── Test 1: All imports work ───────────────────────────────
print("\nTest 1 — All imports from main.py")
try:
    from main import (
        ingest_documents,
        check_prerequisites,
        setup_new_session,
        try_resume_session,
        handle_command,
        run_step_loop,
        main,
    )
    print("  All functions imported ✅")
    pass1 = True
except ImportError as e:
    print(f"  Import error ❌: {e}")
    pass1 = False

# ── Test 2: handle_command with mock state ─────────────────
print("\nTest 2 — Command handler")
from workflow.steps import WorkflowState

state = WorkflowState(
    controller = "STM32F407VGT6",
    ide        = "STM32CubeIDE",
    frequency  = "168 MHz",
)
state.session_id = "test_session_smoke"

# Test each command
commands = {
    "help"    : "continue",
    "status"  : "continue",
    "save"    : "continue",
    "docs"    : "continue",
    "files"   : "continue",
    ""        : "continue",
    "next"    : "next",
    "quit"    : "quit",
    "What is PLLM?" : "question",
}

all_ok = True
for cmd, expected in commands.items():
    # Skip save for test (creates file)
    if cmd == "save":
        continue
    result = handle_command(cmd, state)
    ok     = result == expected
    print(
        f"  '{cmd[:20]:<20}' → "
        f"'{result}' {'✅' if ok else f'❌ expected {expected}'}"
    )
    if not ok:
        all_ok = False
pass2 = all_ok
print(f"  PASS ✅" if pass2 else "  FAIL ❌")

# ── Test 3: docs/ folder exists ───────────────────────────
print("\nTest 3 — docs/ folder exists")
from Config import DOCS_FOLDER
exists = os.path.exists(DOCS_FOLDER)
print(f"  docs/ folder    : {'exists ✅' if exists else 'missing ❌'}")
if exists:
    pdfs = [f for f in os.listdir(DOCS_FOLDER) if f.endswith('.pdf')]
    print(f"  PDFs available  : {len(pdfs)}")
    for p in pdfs:
        print(f"    → {p}")
pass3 = exists
print(f"  PASS ✅" if pass3 else "  FAIL ❌")

# ── Test 4: generated/ and sessions/ folders ──────────────
print("\nTest 4 — Output folders exist")
from Config import GENERATED_CODE_PATH
folders = {
    "generated/" : GENERATED_CODE_PATH,
    "sessions/"  : "./sessions",
}
all_exist = True
for name, path in folders.items():
    if not os.path.exists(path):
        os.makedirs(path)
    exists = os.path.exists(path)
    print(f"  {name:<15} : {'✅' if exists else '❌'}")
    if not exists:
        all_exist = False
pass4 = all_exist
print(f"  PASS ✅" if pass4 else "  FAIL ❌")

# ── Test 5: Vector DB status ───────────────────────────────
print("\nTest 5 — Vector DB status")
from retrieval.vector_store import (
    get_chunk_count, list_indexed_sources,
    list_indexed_doc_types,
)
count   = get_chunk_count()
sources = list_indexed_sources()
types   = list_indexed_doc_types()
print(f"  Chunks indexed  : {count}")
print(f"  Sources         : {sources}")
print(f"  Doc types       : {types}")
pass5 = True   # not a failure if empty — just informational
print(f"  PASS ✅")

# ── Test 6: Ollama check ───────────────────────────────────
print("\nTest 6 — Ollama availability")
from llm.client import check_ollama_running, check_model_available
ollama_ok = check_ollama_running()
model_ok  = check_model_available("mistral")
print(f"  Ollama running  : {'✅' if ollama_ok else '❌ not running'}")
print(f"  Mistral model   : {'✅' if model_ok  else '❌ not found'}")
pass6 = ollama_ok and model_ok
print(f"  PASS ✅" if pass6 else "  FAIL ❌")

# ── Test 7: Argparse works ─────────────────────────────────
print("\nTest 7 — Argument parsing")
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--resume",  action="store_true")
parser.add_argument("--reindex", action="store_true")
args = parser.parse_args([])
print(f"  --resume  default : {args.resume}  (should be False)")
print(f"  --reindex default : {args.reindex} (should be False)")
args2 = parser.parse_args(["--resume"])
print(f"  --resume  flag    : {args2.resume}  (should be True)")
pass7 = (
    not args.resume and
    not args.reindex and
    args2.resume
)
print(f"  PASS ✅" if pass7 else "  FAIL ❌")

# ── Test 8: Workflow state → full run ready ────────────────
print("\nTest 8 — WorkflowState ready for main loop")
from workflow.steps import STEPS, STEP_LABELS
state2 = WorkflowState(
    controller   = "STM32F407VGT6",
    ide          = "STM32CubeIDE",
    frequency    = "168 MHz",
    docs_indexed = count,
)
print(f"  Steps defined   : {len(STEPS)}")
print(f"  Labels defined  : {len(STEP_LABELS)}")
print(f"  Initial step    : {state2.current_step}")
print(f"  Docs indexed    : {state2.docs_indexed}")
pass8 = (
    len(STEPS) == 5 and
    state2.current_step == "intro"
)
print(f"  PASS ✅" if pass8 else "  FAIL ❌")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
results = [
    pass1, pass2, pass3, pass4,
    pass5, pass6, pass7, pass8,
]
passed = sum(results)
total  = len(results)
print(f"  Tests passed : {passed}/{total}")

if passed == total:
    print("RESULT: main.py OK ✅")
    print("\n  Ready to run:")
    print("  [green]python main.py[/green]")
    print("  python main.py --resume    ← resume last session")
    print("  python main.py --reindex   ← re-index docs")
else:
    print(f"RESULT: main.py PARTIAL — {total-passed} failed ❌")
    print("  Fix failures above before running python main.py")

print("=" * 55)