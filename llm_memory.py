import llm
import click
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


@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def memory():
        """Memory management commands"""
        pass
    
    @memory.command()
    def show():
        """Display current user profile"""
        try:
            profile_content = load_user_profile()
            if profile_content.strip():
                click.echo(profile_content)
            else:
                click.echo("No memory profile found. Profile will be created automatically when you start using LLM with memory.")
        except Exception as e:
            click.echo(f"Error reading profile: {e}", err=True)
    
    @memory.command()
    def clear():
        """Clear user profile and create empty one"""
        try:
            profile_path = get_profile_path()
            
            # Create empty profile with basic structure
            empty_profile = """# User Profile

## Personal Information
- Role: [Not specified]

## Interests
- [No interests recorded yet]

## Current Projects
- [No current projects recorded]

## Preferences
- [No preferences recorded yet]
"""
            
            if save_user_profile(empty_profile):
                click.echo(f"Memory profile cleared and reset to empty state.")
                click.echo(f"Location: {profile_path}")
            else:
                click.echo("Error: Failed to clear profile", err=True)
        except Exception as e:
            click.echo(f"Error clearing profile: {e}", err=True)
    
    @memory.command()
    def status():
        """Show if memory system is active"""
        try:
            profile_path = get_profile_path()
            profile_exists = profile_path.exists()
            
            click.echo("Memory System Status:")
            click.echo(f"  Profile location: {profile_path}")
            click.echo(f"  Profile exists: {'Yes' if profile_exists else 'No'}")
            
            if profile_exists:
                profile_size = profile_path.stat().st_size
                click.echo(f"  Profile size: {profile_size} bytes")
                click.echo(f"  Memory system: Active")
                click.echo(f"  Usage: llm -f memory:auto \"your prompt\"")
            else:
                click.echo(f"  Memory system: Inactive (no profile)")
                click.echo(f"  The profile will be created automatically when you start using memory fragments.")
                
        except Exception as e:
            click.echo(f"Error checking status: {e}", err=True)
    
    @memory.command()
    def path():
        """Show profile file location"""
        try:
            profile_path = get_profile_path()
            click.echo(str(profile_path))
        except Exception as e:
            click.echo(f"Error getting path: {e}", err=True)