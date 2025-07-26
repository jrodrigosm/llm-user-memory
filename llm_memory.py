import llm
import click
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import os
import atexit


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
            # Start background monitoring when memory is first used
            ensure_monitoring_started()
            
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


def get_llm_database_path():
    """
    Get the path to LLM's conversation database using `llm logs path`.
    Returns Path object or None if unable to get path.
    """
    try:
        result = subprocess.run(
            ["llm", "logs", "path"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            db_path = Path(result.stdout.strip())
            if db_path.exists():
                return db_path
        return None
    except Exception:
        # Silent failure
        return None


def get_latest_conversation(since_timestamp=None):
    """
    Get the most recent conversation from LLM database.
    Returns dict with conversation info or None if no conversation found.
    """
    try:
        db_path = get_llm_database_path()
        if not db_path:
            return None
            
        conn = sqlite3.connect(str(db_path))
        
        # Query for latest response
        if since_timestamp:
            cursor = conn.execute("""
                SELECT prompt, model, datetime_utc, id
                FROM responses 
                WHERE datetime_utc > ?
                ORDER BY datetime_utc DESC 
                LIMIT 1
            """, (since_timestamp,))
        else:
            cursor = conn.execute("""
                SELECT prompt, model, datetime_utc, id
                FROM responses 
                ORDER BY datetime_utc DESC 
                LIMIT 1
            """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'prompt': result[0],
                'model': result[1], 
                'datetime_utc': result[2],
                'id': result[3]
            }
        return None
    except Exception:
        # Silent failure
        return None


def update_profile_with_conversation(conversation_data):
    """
    Send profile update request to LLM model using conversation data.
    Returns True if profile was updated, False otherwise.
    """
    try:
        current_profile = load_user_profile()
        if not current_profile:
            # Create initial profile structure if none exists
            current_profile = """# User Profile

## Personal Information
- Role: [Not specified]

## Interests
- [No interests recorded yet]

## Current Projects
- [No current projects recorded]

## Preferences
- [No preferences recorded yet]
"""

        # Create update prompt
        update_prompt = f"""Current user profile:
{current_profile}

User's latest interaction:
{conversation_data['prompt']}

Please update the user profile based on this new information. Only include relevant, factual information about the user. If no update is needed, respond exactly with "NO_UPDATE".

Return the complete updated profile in the same markdown format."""

        # Use the same model that was used in the conversation
        model_name = conversation_data['model']
        model = llm.get_model(model_name)
        
        response = model.prompt(update_prompt)
        response_text = response.text().strip()
        
        # Check if update is needed
        if response_text != "NO_UPDATE" and response_text != current_profile.strip():
            if save_user_profile(response_text):
                return True
                
        return False
    except Exception:
        # Silent failure - never break main functionality
        return False


# Global variables for background monitoring
_monitor_thread = None
_monitor_running = False
_last_check_timestamp = None


class ProfileMonitor:
    """Background monitoring service for profile updates."""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_check_timestamp = None
        
    def start(self):
        """Start the background monitoring thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        # Register cleanup on exit
        atexit.register(self.stop)
    
    def stop(self):
        """Stop the background monitoring thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in background thread."""
        while self.running:
            try:
                self._check_for_updates()
            except Exception:
                # Silent failure - never break
                pass
            
            # Wait 5 seconds before next check
            for _ in range(50):  # Check every 0.1 seconds for early exit
                if not self.running:
                    break
                time.sleep(0.1)
    
    def _check_for_updates(self):
        """Check for new conversations and update profile if needed."""
        try:
            # Get latest conversation since last check
            conversation = get_latest_conversation(self.last_check_timestamp)
            
            if conversation:
                # Update timestamp to prevent reprocessing
                self.last_check_timestamp = conversation['datetime_utc']
                
                # Only update if this is a user prompt (not empty)
                if conversation['prompt'] and conversation['prompt'].strip():
                    # Attempt to update profile
                    if update_profile_with_conversation(conversation):
                        # Profile was updated - could show notification in future
                        pass
                        
        except Exception:
            # Silent failure
            pass


# Global monitor instance
_profile_monitor = ProfileMonitor()


def ensure_monitoring_started():
    """Ensure background monitoring is started. Called when memory is first used."""
    global _profile_monitor
    if not _profile_monitor.running:
        _profile_monitor.start()


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
            
            # Check database access
            db_path = get_llm_database_path()
            click.echo(f"  Database access: {'Yes' if db_path else 'No'}")
            if db_path:
                click.echo(f"  Database location: {db_path}")
            
            # Check monitoring status
            global _profile_monitor
            monitor_status = "Running" if _profile_monitor.running else "Stopped"
            click.echo(f"  Background monitoring: {monitor_status}")
            
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