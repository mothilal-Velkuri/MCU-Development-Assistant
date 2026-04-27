# =============================================================
# workflow/session.py
# Saves and loads workflow sessions to disk.
#
# Why sessions?
#   You may need to stop mid-way through configuring a
#   complex peripheral. Sessions let you resume exactly
#   where you left off — same history, same state.
#
# Format: JSON file in ./sessions/ folder
# =============================================================

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from workflow.steps import WorkflowState

SESSIONS_FOLDER = "./sessions"


def _ensure_sessions_folder() -> None:
    """Create sessions folder if it does not exist."""
    Path(SESSIONS_FOLDER).mkdir(exist_ok=True)


def generate_session_id() -> str:
    """Generate a unique session ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id  = str(uuid.uuid4())[:8]
    return f"session_{timestamp}_{short_id}"


def save_session(state: WorkflowState) -> str:
    """
    Save current workflow state to a JSON file.

    Parameters
    ----------
    state : current WorkflowState

    Returns
    -------
    Path to the saved session file.
    """
    _ensure_sessions_folder()

    if not state.session_id:
        state.session_id = generate_session_id()

    session_data = {
        "session_id"          : state.session_id,
        "saved_at"            : datetime.now().isoformat(),
        "controller"          : state.controller,
        "ide"                 : state.ide,
        "frequency"           : state.frequency,
        "notes"               : state.notes,
        "current_step"        : state.current_step,
        "selected_peripherals": state.selected_peripherals,
        "generated_code"      : state.generated_code,
        "docs_indexed"        : state.docs_indexed,
        "history"             : state.history,
    }

    filepath = os.path.join(
        SESSIONS_FOLDER,
        f"{state.session_id}.json"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    print(f"  Session saved: {filepath}")
    return filepath


def load_session(session_id: str) -> WorkflowState:
    """
    Load a previously saved session from disk.

    Parameters
    ----------
    session_id : the session ID string

    Returns
    -------
    WorkflowState restored from file.
    """
    filepath = os.path.join(
        SESSIONS_FOLDER,
        f"{session_id}.json"
    )

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Session not found: {session_id}\n"
            f"Looked in: {filepath}"
        )

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    state = WorkflowState(
        controller           = data["controller"],
        ide                  = data["ide"],
        frequency            = data["frequency"],
        notes                = data.get("notes", ""),
        current_step         = data["current_step"],
        selected_peripherals = data.get("selected_peripherals", []),
        generated_code       = data.get("generated_code", {}),
        session_id           = data["session_id"],
        docs_indexed         = data.get("docs_indexed", 0),
        history              = data.get("history", {}),
    )

    print(f"  Session loaded: {session_id}")
    print(f"  Controller    : {state.controller}")
    print(f"  Current step  : {state.current_label()}")
    return state


def list_sessions() -> list[dict]:
    """
    List all saved sessions with their metadata.

    Returns
    -------
    List of dicts with session info — newest first.
    """
    _ensure_sessions_folder()

    sessions = []
    for filename in os.listdir(SESSIONS_FOLDER):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(SESSIONS_FOLDER, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id" : data.get("session_id", "unknown"),
                "controller" : data.get("controller", "unknown"),
                "ide"        : data.get("ide", "unknown"),
                "saved_at"   : data.get("saved_at", "unknown"),
                "step"       : data.get("current_step", "unknown"),
                "filepath"   : filepath,
            })
        except Exception:
            continue

    # Sort newest first
    sessions.sort(key=lambda x: x["saved_at"], reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """
    Delete a saved session file.
    Returns True if deleted, False if not found.
    """
    filepath = os.path.join(
        SESSIONS_FOLDER,
        f"{session_id}.json"
    )
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"  Session deleted: {session_id}")
        return True
    return False