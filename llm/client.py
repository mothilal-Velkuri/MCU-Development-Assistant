# =============================================================
# llm/client.py
# Ollama LLM API wrapper.
#
# Sends system prompt + conversation history + user message
# to the local Ollama mistral model and returns the response.
#
# Architecture:
#   ask_llm()  → single response
#   stream_llm() → streaming response (token by token)
#
# To switch to Anthropic API later:
#   Change LLM_BACKEND = "anthropic" in config.py
#   The rest of the code stays the same.
# =============================================================

import requests
import json
from Config import (
    LLM_BACKEND,
    OLLAMA_MODEL,
    OLLAMA_URL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
)


# =============================================================
# OLLAMA CLIENT
# =============================================================

def _ask_ollama(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.1,
) -> str:
    """
    Send a message to local Ollama LLM.

    Parameters
    ----------
    system_prompt        : instructions for the LLM
    conversation_history : list of past messages
                           [{"role": "user"|"assistant",
                             "content": "text"}]
    user_message         : current user question
    temperature          : 0.0 = deterministic, 1.0 = creative
                           Keep low (0.1) for technical answers

    Returns
    -------
    LLM response as a string
    """
    # Build message list
    messages = (
        [{"role": "system", "content": system_prompt}]
        + conversation_history
        + [{"role": "user", "content": user_message}]
    )

    payload = {
        "model"   : OLLAMA_MODEL,
        "messages": messages,
        "stream"  : False,
        "options" : {
            "temperature"  : temperature,
            "num_predict"  : 2048,    # max tokens in response
            "top_p"        : 0.9,
            "repeat_penalty": 1.1,   # reduce repetition
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json    = payload,
            timeout = 120,    # 2 minutes — mistral can be slow
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    except requests.exceptions.ConnectionError:
        return (
            "❌ ERROR: Cannot connect to Ollama.\n"
            "Make sure Ollama is running.\n"
            "Start it with: ollama serve"
        )
    except requests.exceptions.Timeout:
        return (
            "❌ ERROR: Ollama response timed out.\n"
            "The model is taking too long.\n"
            "Try a shorter question or restart Ollama."
        )
    except KeyError:
        return (
            f"❌ ERROR: Unexpected Ollama response format.\n"
            f"Response: {response.text[:200]}"
        )


def _stream_ollama(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.1,
):
    """
    Stream tokens from Ollama as they are generated.
    Yields each token string one at a time.
    Used for real-time display in the terminal.
    """
    messages = (
        [{"role": "system", "content": system_prompt}]
        + conversation_history
        + [{"role": "user", "content": user_message}]
    )

    payload = {
        "model"   : OLLAMA_MODEL,
        "messages": messages,
        "stream"  : True,
        "options" : {
            "temperature": temperature,
            "num_predict": 2048,
        }
    }

    try:
        with requests.post(
            OLLAMA_URL,
            json    = payload,
            stream  = True,
            timeout = 120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.ConnectionError:
        yield "\n❌ ERROR: Cannot connect to Ollama."


# =============================================================
# ANTHROPIC CLIENT (future use)
# =============================================================

def _ask_anthropic(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.1,
) -> str:
    """
    Send a message to Anthropic Claude API.
    Activated when LLM_BACKEND = "anthropic" in config.py.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        messages = (
            conversation_history
            + [{"role": "user", "content": user_message}]
        )

        response = client.messages.create(
            model      = ANTHROPIC_MODEL,
            max_tokens = 2048,
            system     = system_prompt,
            messages   = messages,
        )
        return response.content[0].text

    except ImportError:
        return (
            "❌ ERROR: anthropic package not installed.\n"
            "Run: pip install anthropic"
        )
    except Exception as e:
        return f"❌ ERROR: Anthropic API error: {str(e)}"


# =============================================================
# PUBLIC API — Use these in your workflow
# =============================================================

def ask_llm(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.1,
) -> str:
    """
    Send a message to the configured LLM backend.
    Returns the complete response as a string.

    Parameters
    ----------
    system_prompt        : instructions for the LLM
    conversation_history : past Q&A turns for this step
    user_message         : current user question
    temperature          : keep at 0.1 for technical accuracy

    Returns
    -------
    Complete LLM response as a string.
    """
    if LLM_BACKEND == "anthropic":
        return _ask_anthropic(
            system_prompt,
            conversation_history,
            user_message,
            temperature,
        )
    else:
        return _ask_ollama(
            system_prompt,
            conversation_history,
            user_message,
            temperature,
        )


def stream_llm(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.1,
):
    """
    Stream tokens from the LLM one at a time.
    Use this for real-time terminal display.

    Usage:
        for token in stream_llm(prompt, history, question):
            print(token, end="", flush=True)
        print()  # newline at end
    """
    if LLM_BACKEND == "anthropic":
        # Anthropic streaming — fall back to non-streaming for now
        yield ask_llm(
            system_prompt,
            conversation_history,
            user_message,
            temperature,
        )
    else:
        yield from _stream_ollama(
            system_prompt,
            conversation_history,
            user_message,
            temperature,
        )


def check_ollama_running() -> bool:
    """
    Check if Ollama server is running and accessible.
    Returns True if running, False otherwise.
    """
    try:
        r = requests.get(
            "http://localhost:11434",
            timeout = 3
        )
        return r.status_code == 200
    except Exception:
        return False


def check_model_available(model: str = OLLAMA_MODEL) -> bool:
    """
    Check if the specified model is downloaded in Ollama.
    Returns True if available, False otherwise.
    """
    try:
        r = requests.get(
            "http://localhost:11434/api/tags",
            timeout = 5
        )
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return any(model in m for m in models)
        return False
    except Exception:
        return False