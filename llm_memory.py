import llm
from pathlib import Path


@llm.hookimpl
def register_fragment_loaders(register):
    register("memory", memory_fragment_loader)


def memory_fragment_loader(argument):
    """
    Fragment loader for memory system.
    Called when user runs: llm -f memory:argument "prompt"
    Returns text content to inject into prompt.
    """
    try:
        if argument == "auto":
            profile_content = load_user_profile()
            if profile_content:
                # Return Fragment object with source attribution
                return llm.Fragment(profile_content, source="memory:profile")
            return ""
        elif argument == "test":
            return llm.Fragment("TEST FRAGMENT: This memory fragment system is working correctly!", source="memory:test")
        return ""
    except Exception:
        # Silent failure - never break user's main command
        return ""


def load_user_profile():
    """
    Load user profile from ~/.config/llm/memory/profile.md
    Returns profile content or empty string if no profile exists.
    """
    try:
        profile_path = get_profile_path()
        if profile_path.exists():
            return profile_path.read_text(encoding='utf-8')
        return ""
    except Exception:
        # Silent failure
        return ""


def get_profile_path():
    """
    Get the path to the user profile file.
    Creates memory directory if it doesn't exist.
    """
    memory_dir = llm.user_dir() / "memory"
    memory_dir.mkdir(exist_ok=True)
    return memory_dir / "profile.md"


def save_user_profile(content):
    """
    Save content to user profile file.
    Creates directory and file if they don't exist.
    """
    try:
        profile_path = get_profile_path()
        profile_path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        # Silent failure
        return False