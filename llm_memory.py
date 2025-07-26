import llm
import click
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import os
import atexit
import shutil
import fcntl
import contextlib
import logging


@llm.hookimpl
def register_fragment_loaders(register):
    register("memory", memory_fragment_loader)


def get_logger():
    """Get logger instance for debugging (optional, off by default)."""
    logger = logging.getLogger("llm-memory")
    
    # Only configure if not already configured
    if not logger.handlers:
        # Check if debug logging is enabled
        debug_enabled = os.environ.get('LLM_MEMORY_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if debug_enabled:
            logger.setLevel(logging.DEBUG)
            # Create debug log file in memory directory
            try:
                memory_dir = llm.user_dir() / "memory"
                memory_dir.mkdir(exist_ok=True)
                log_file = memory_dir / "debug.log"
                handler = logging.FileHandler(log_file)
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            except Exception:
                # If logging setup fails, continue without logging
                pass
        else:
            # Disable logging by default
            logger.setLevel(logging.CRITICAL)
    
    return logger


def is_memory_disabled():
    """Check if memory system is disabled via environment variable."""
    return os.environ.get('LLM_MEMORY_DISABLED', '').lower() in ('1', 'true', 'yes')


def memory_fragment_loader(argument):
    """
    Fragment loader for memory system.
    Called when user runs: llm -f memory:argument "prompt"
    Returns text content to inject into prompt.
    """
    try:
        # Check if memory system is disabled
        if is_memory_disabled():
            return ""
            
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
    except Exception as e:
        # Log error for debugging but never break user's main command
        logger = get_logger()
        logger.debug(f"Fragment loader error: {e}")
        return ""


def load_user_profile():
    """
    Load user profile from ~/.config/llm/memory/profile.md with file locking.
    Returns profile content or empty string if no profile exists.
    """
    try:
        profile_path = get_profile_path()
        if profile_path.exists():
            with locked_file(profile_path, 'r') as f:
                return f.read()
        return ""
    except Exception as e:
        # Log the error for debugging but continue silently
        logger = get_logger()
        logger.debug(f"Failed to load profile: {e}")
        return ""


def get_profile_path():
    """
    Get the path to the user profile file.
    Creates memory directory if it doesn't exist.
    """
    memory_dir = llm.user_dir() / "memory"
    memory_dir.mkdir(exist_ok=True)
    return memory_dir / "profile.md"


@contextlib.contextmanager
def locked_file(file_path, mode='r'):
    """Context manager for file locking to prevent concurrent access issues."""
    try:
        with open(file_path, mode, encoding='utf-8') as f:
            # Apply exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield f
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        # If locking fails, continue without lock but log the issue
        logger = get_logger()
        logger.debug(f"File locking failed for {file_path}, proceeding without lock")
        with open(file_path, mode, encoding='utf-8') as f:
            yield f


def save_user_profile(content):
    """
    Save content to user profile file with file locking for concurrent access safety.
    Creates directory and file if they don't exist.
    """
    try:
        profile_path = get_profile_path()
        
        # Use file locking to prevent concurrent access
        with locked_file(profile_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        # Log the error for debugging but continue silently
        logger = get_logger()
        logger.debug(f"Failed to save profile: {e}")
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
    except Exception as e:
        # Log error for debugging
        logger = get_logger()
        logger.debug(f"Failed to get database path: {e}")
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
    except Exception as e:
        # Log error for debugging
        logger = get_logger()
        logger.debug(f"Failed to get latest conversation: {e}")
        return None


def update_profile_with_conversation(conversation_data):
    """
    Send profile update request to LLM model using conversation data.
    Returns True if profile was updated, False otherwise.
    """
    try:
        # Check if updates are disabled
        if is_updates_disabled():
            return False
            
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
                logger = get_logger()
                logger.debug(f"Profile updated from conversation with model {model_name}")
                return True
                
        return False
    except Exception as e:
        # Log error for debugging but never break main functionality
        logger = get_logger()
        logger.debug(f"Profile update failed: {e}")
        return False


def detect_user_shell():
    """
    Detect the user's current shell.
    Returns shell name (bash, zsh, fish) or None if not detected.
    """
    try:
        # Get shell from SHELL environment variable
        shell_path = os.environ.get('SHELL', '')
        if shell_path:
            shell_name = Path(shell_path).name
            if shell_name in ['bash', 'zsh', 'fish']:
                return shell_name
        return None
    except Exception:
        return None


def get_shell_profile_paths(shell):
    """
    Get the profile file paths for a given shell.
    Returns list of Path objects that could contain shell configuration.
    """
    home = Path.home()
    
    if shell == 'bash':
        return [
            home / '.bashrc',
            home / '.bash_profile',
            home / '.profile'
        ]
    elif shell == 'zsh':
        return [
            home / '.zshrc',
            home / '.zprofile',
            home / '.profile'
        ]
    elif shell == 'fish':
        return [
            home / '.config' / 'fish' / 'config.fish'
        ]
    else:
        return []


def find_active_shell_profile(shell):
    """
    Find the shell profile file that should be modified.
    Returns Path object of the file to modify, or None if not found.
    """
    profile_paths = get_shell_profile_paths(shell)
    
    # For bash and zsh, prefer existing files in order of preference
    for path in profile_paths:
        if path.exists():
            return path
    
    # If no existing files, create the default one
    if profile_paths:
        # For fish, ensure the directory exists
        if shell == 'fish':
            profile_paths[0].parent.mkdir(parents=True, exist_ok=True)
        return profile_paths[0]
    
    return None


def get_shell_function():
    """
    Get the shell function code to inject.
    Returns the function as a string.
    """
    return '''
# LLM Memory Plugin Integration
# This function automatically injects memory context into all llm commands
llm() {
    command llm -f memory:auto "$@"
}
'''


def is_shell_function_installed(profile_path):
    """
    Check if the shell function is already installed in the profile file.
    Returns True if installed, False otherwise.
    """
    try:
        if not profile_path.exists():
            return False
        
        content = profile_path.read_text(encoding='utf-8')
        return 'llm() {' in content and 'command llm -f memory:auto' in content
    except Exception:
        return False


def install_shell_function(shell):
    """
    Install the shell function to the user's shell profile.
    Returns True if successful, False otherwise.
    """
    try:
        profile_path = find_active_shell_profile(shell)
        if not profile_path:
            return False
        
        # Check if already installed
        if is_shell_function_installed(profile_path):
            return True
        
        # Create backup
        backup_path = profile_path.with_suffix(profile_path.suffix + '.llm-memory-backup')
        if profile_path.exists() and not backup_path.exists():
            shutil.copy2(profile_path, backup_path)
        
        # Add the function to the profile
        function_code = get_shell_function()
        
        if profile_path.exists():
            # Append to existing file
            with open(profile_path, 'a', encoding='utf-8') as f:
                f.write(function_code)
        else:
            # Create new file
            profile_path.write_text(function_code, encoding='utf-8')
        
        return True
    except Exception:
        return False


def uninstall_shell_function(shell):
    """
    Remove the shell function from the user's shell profile.
    Returns True if successful, False otherwise.
    """
    try:
        profile_path = find_active_shell_profile(shell)
        if not profile_path or not profile_path.exists():
            return True  # Nothing to uninstall
        
        content = profile_path.read_text(encoding='utf-8')
        
        # Find and remove the function block
        lines = content.split('\n')
        new_lines = []
        in_function_block = False
        
        for line in lines:
            if '# LLM Memory Plugin Integration' in line:
                in_function_block = True
                continue
            elif in_function_block and line.strip() == '}':
                in_function_block = False
                continue
            elif not in_function_block:
                new_lines.append(line)
        
        # Write back the modified content
        new_content = '\n'.join(new_lines)
        
        # Remove trailing newlines that might have been added
        new_content = new_content.rstrip('\n')
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
        
        profile_path.write_text(new_content, encoding='utf-8')
        return True
    except Exception:
        return False


def verify_shell_integration():
    """
    Verify that shell integration is working by checking if the function exists.
    Returns dict with verification results.
    """
    try:
        shell = detect_user_shell()
        if not shell:
            return {'success': False, 'error': 'Could not detect shell'}
        
        profile_path = find_active_shell_profile(shell)
        if not profile_path:
            return {'success': False, 'error': f'Could not find {shell} profile file'}
        
        installed = is_shell_function_installed(profile_path)
        
        return {
            'success': True,
            'shell': shell,
            'profile_path': str(profile_path),
            'function_installed': installed
        }
    except Exception as e:
        logger = get_logger()
        logger.debug(f"Shell integration verification failed: {e}")
        return {'success': False, 'error': str(e)}


def is_updates_disabled():
    """Check if profile updates are disabled via environment variable."""
    return os.environ.get('LLM_MEMORY_UPDATES', '').lower() in ('false', '0', 'no')


def get_update_interval():
    """Get update check interval in seconds from environment variable."""
    try:
        interval = int(os.environ.get('LLM_MEMORY_UPDATE_INTERVAL', '5'))
        return max(1, interval)  # Minimum 1 second
    except (ValueError, TypeError):
        return 5  # Default 5 seconds


# Global variables for background monitoring
_monitor_thread = None
_monitor_running = False
_last_check_timestamp = None
_monitor_paused = False


class ProfileMonitor:
    """Background monitoring service for profile updates."""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_check_timestamp = None
        self.paused = False
        
    def start(self):
        """Start the background monitoring thread."""
        if self.running:
            return
            
        # Don't start if memory system is disabled
        if is_memory_disabled():
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        # Register cleanup on exit
        atexit.register(self.stop)
        
        logger = get_logger()
        logger.debug("Profile monitoring started")
    
    def stop(self):
        """Stop the background monitoring thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
            
        logger = get_logger()
        logger.debug("Profile monitoring stopped")
    
    def pause(self):
        """Pause profile updates without stopping the monitoring thread."""
        self.paused = True
        logger = get_logger()
        logger.debug("Profile updates paused")
    
    def resume(self):
        """Resume profile updates."""
        self.paused = False
        logger = get_logger()
        logger.debug("Profile updates resumed")
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in background thread."""
        update_interval = get_update_interval()
        
        while self.running:
            try:
                if not self.paused:
                    self._check_for_updates()
            except Exception as e:
                # Log error for debugging but never break
                logger = get_logger()
                logger.debug(f"Monitor loop error: {e}")
            
            # Wait for configured interval before next check
            sleep_increments = int(update_interval * 10)  # Check every 0.1 seconds for early exit
            for _ in range(sleep_increments):
                if not self.running:
                    break
                time.sleep(0.1)
    
    def _check_for_updates(self):
        """Check for new conversations and update profile if needed."""
        try:
            # Skip if updates are disabled
            if is_updates_disabled():
                return
                
            # Get latest conversation since last check
            conversation = get_latest_conversation(self.last_check_timestamp)
            
            if conversation:
                # Update timestamp to prevent reprocessing
                self.last_check_timestamp = conversation['datetime_utc']
                
                # Only update if this is a user prompt (not empty)
                if conversation['prompt'] and conversation['prompt'].strip():
                    # Attempt to update profile
                    if update_profile_with_conversation(conversation):
                        # Profile was updated
                        logger = get_logger()
                        logger.debug(f"Profile updated from conversation {conversation['id']}")
                        
        except Exception as e:
            # Log error for debugging but continue silently
            logger = get_logger()
            logger.debug(f"Update check failed: {e}")


# Global monitor instance
_profile_monitor = ProfileMonitor()


def ensure_monitoring_started():
    """Ensure background monitoring is started. Called when memory is first used."""
    global _profile_monitor
    if not _profile_monitor.running and not is_memory_disabled():
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
            if _profile_monitor.running:
                if _profile_monitor.paused:
                    click.echo(f"  Update status: Paused (use 'llm memory resume' to enable)")
                else:
                    click.echo(f"  Update status: Active")
                    update_interval = get_update_interval()
                    click.echo(f"  Update interval: {update_interval} seconds")
            
            # Check configuration
            if is_memory_disabled():
                click.echo(f"  Memory system: Disabled (LLM_MEMORY_DISABLED=true)")
            elif is_updates_disabled():
                click.echo(f"  Profile updates: Disabled (LLM_MEMORY_UPDATES=false)")
            
            # Show environment configuration
            debug_enabled = os.environ.get('LLM_MEMORY_DEBUG', '').lower() in ('1', 'true', 'yes')
            if debug_enabled:
                memory_dir = llm.user_dir() / "memory"
                log_file = memory_dir / "debug.log"
                click.echo(f"  Debug logging: Enabled ({log_file})")
            
            if profile_exists:
                profile_size = profile_path.stat().st_size
                click.echo(f"  Profile size: {profile_size} bytes")
                if not is_memory_disabled():
                    click.echo(f"  Memory system: Active")
                    click.echo(f"  Usage: llm -f memory:auto \"your prompt\"")
                else:
                    click.echo(f"  Memory system: Disabled by environment variable")
            else:
                click.echo(f"  Memory system: Inactive (no profile)")
                if not is_memory_disabled():
                    click.echo(f"  The profile will be created automatically when you start using memory fragments.")
                else:
                    click.echo(f"  Memory system is disabled by environment variable.")
                
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
    
    @memory.command("install-shell")
    def install_shell():
        """Install shell integration for transparent memory usage"""
        try:
            shell = detect_user_shell()
            if not shell:
                click.echo("Error: Could not detect your shell. Supported shells: bash, zsh, fish.", err=True)
                return
            
            click.echo(f"Detected shell: {shell}")
            
            # Check if already installed
            verification = verify_shell_integration()
            if verification['success'] and verification['function_installed']:
                click.echo("Shell integration is already installed!")
                click.echo(f"Profile file: {verification['profile_path']}")
                click.echo("You can now use 'llm \"your prompt\"' and memory will be automatically included.")
                return
            
            # Install the function
            if install_shell_function(shell):
                profile_path = find_active_shell_profile(shell)
                click.echo("✓ Shell integration installed successfully!")
                click.echo(f"Modified file: {profile_path}")
                
                # Check if backup was created
                backup_path = profile_path.with_suffix(profile_path.suffix + '.llm-memory-backup')
                if backup_path.exists():
                    click.echo(f"Backup created: {backup_path}")
                
                click.echo("")
                click.echo("To activate the integration, restart your terminal or run:")
                if shell == 'fish':
                    click.echo("  source ~/.config/fish/config.fish")
                elif shell == 'zsh':
                    click.echo("  source ~/.zshrc")
                else:
                    click.echo("  source ~/.bashrc")
                
                click.echo("")
                click.echo("After activation, all llm commands will automatically include memory:")
                click.echo("  llm \"What should I work on today?\"")
                click.echo("  # Your response will be personalized based on your profile!")
            else:
                click.echo("Error: Failed to install shell integration", err=True)
                
        except Exception as e:
            click.echo(f"Error installing shell integration: {e}", err=True)
    
    @memory.command("uninstall-shell")
    def uninstall_shell():
        """Remove shell integration and restore normal llm behavior"""
        try:
            shell = detect_user_shell()
            if not shell:
                click.echo("Error: Could not detect your shell.", err=True)
                return
            
            # Check current status
            verification = verify_shell_integration()
            if verification['success'] and not verification['function_installed']:
                click.echo("Shell integration is not currently installed.")
                return
            
            # Uninstall the function
            if uninstall_shell_function(shell):
                click.echo("✓ Shell integration removed successfully!")
                
                profile_path = find_active_shell_profile(shell)
                if profile_path:
                    click.echo(f"Modified file: {profile_path}")
                
                click.echo("")
                click.echo("The 'llm' command now works normally again.")
                click.echo("To use memory manually, run:")
                click.echo("  llm -f memory:auto \"your prompt\"")
                
                click.echo("")
                click.echo("Restart your terminal for changes to take effect, or run:")
                if shell == 'fish':
                    click.echo("  source ~/.config/fish/config.fish")
                elif shell == 'zsh':
                    click.echo("  source ~/.zshrc")
                else:
                    click.echo("  source ~/.bashrc")
            else:
                click.echo("Error: Failed to remove shell integration", err=True)
                
        except Exception as e:
            click.echo(f"Error removing shell integration: {e}", err=True)
    
    @memory.command("shell-status")
    def shell_status():
        """Check shell integration status"""
        try:
            verification = verify_shell_integration()
            
            if not verification['success']:
                click.echo(f"Error: {verification['error']}", err=True)
                return
            
            click.echo("Shell Integration Status:")
            click.echo(f"  Shell: {verification['shell']}")
            click.echo(f"  Profile file: {verification['profile_path']}")
            click.echo(f"  Function installed: {'Yes' if verification['function_installed'] else 'No'}")
            
            if verification['function_installed']:
                click.echo(f"  Status: Active - 'llm' commands automatically include memory")
                click.echo(f"  To disable: llm memory uninstall-shell")
            else:
                click.echo(f"  Status: Inactive - 'llm' commands work normally")
                click.echo(f"  To enable: llm memory install-shell")
                
        except Exception as e:
            click.echo(f"Error checking shell status: {e}", err=True)
    
    @memory.command("pause")
    def pause():
        """Temporarily disable memory profile updates"""
        try:
            global _profile_monitor
            _profile_monitor.pause()
            click.echo("Memory updates paused.")
            click.echo("Profile content will still be injected, but no automatic updates will occur.")
            click.echo("Use 'llm memory resume' to re-enable updates.")
        except Exception as e:
            click.echo(f"Error pausing updates: {e}", err=True)
    
    @memory.command("resume")
    def resume():
        """Re-enable memory profile updates"""
        try:
            global _profile_monitor
            _profile_monitor.resume()
            click.echo("Memory updates resumed.")
            click.echo("Profile will now be automatically updated based on your conversations.")
        except Exception as e:
            click.echo(f"Error resuming updates: {e}", err=True)