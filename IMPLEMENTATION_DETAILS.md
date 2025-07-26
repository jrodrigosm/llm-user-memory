# LLM Memory Plugin - Technical Implementation Details

## LLM Plugin System Overview

### Plugin Structure
LLM plugins are Python packages with specific entry points. Required files:
- `llm_memory.py` - Main plugin module
- `pyproject.toml` - Package configuration with entry points

### Entry Point Configuration
In `pyproject.toml`:
```toml
[project.entry-points.llm]
llm-memory = "llm_memory"
```

### Plugin Installation
- Development: `llm install -e .` in plugin directory
- Verification: `llm plugins` lists installed plugins

## Plugin Hooks System

LLM uses the Pluggy plugin system. Available hooks:

### 1. Fragment Loader Hook (KEY FOR OUR IMPLEMENTATION)
```python
import llm

@llm.hookimpl
def register_fragment_loaders(register):
    register("memory", memory_fragment_loader)

def memory_fragment_loader(argument):
    """
    Called when user runs: llm -f memory:argument "prompt"
    Returns text content to inject into prompt
    """
    if argument == "auto":
        return load_user_profile()  # Read from ~/.config/llm/memory/profile.md
    return ""
```

### 2. Command Registration Hook
```python
@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def memory():
        """Memory management commands"""
        pass
    
    @memory.command()
    def show():
        """Display current user profile"""
        # Implementation here
    
    @memory.command()
    def clear():
        """Clear user profile"""
        # Implementation here
```

### 3. Other Available Hooks
- `register_models(register)` - Register new AI models
- `register_tools(register)` - Register tool functions
- `register_template_loaders(register)` - Register template loaders

## LLM Utility Functions

### Configuration Directory Access
```python
import llm

# Get LLM user directory (~/.config/llm or equivalent)
user_dir = llm.user_dir()
memory_dir = user_dir / "memory"
memory_dir.mkdir(exist_ok=True)
profile_path = memory_dir / "profile.md"
```

### Key Management
```python
# Access stored API keys
api_key = llm.get_key(alias="openai", env="OPENAI_API_KEY")
```

### Error Handling
```python
# Use LLM's error class for consistent error reporting
raise llm.ModelError("Memory system initialization failed")
```

## Database Access and Monitoring

### LLM Logging System
- All conversations logged to SQLite database
- Database path: `llm logs path` command
- Tables: `conversations`, `responses`, `attachments`, `fragments`

### Database Schema (Key Tables)
```sql
CREATE TABLE [conversations] (
    [id] TEXT PRIMARY KEY,
    [name] TEXT,
    [model] TEXT
);

CREATE TABLE [responses] (
    [id] TEXT PRIMARY KEY,
    [model] TEXT,
    [prompt] TEXT,
    [system] TEXT,
    [response] TEXT,
    [conversation_id] TEXT REFERENCES [conversations]([id]),
    [datetime_utc] TEXT,
    [duration_ms] INTEGER
);
```

### Database Monitoring Approaches
1. **SQLite Triggers**: Create trigger on INSERT to responses table
2. **Polling**: Periodically check for new entries
3. **File System Watching**: Monitor database file modifications

### Example Database Access
```python
import sqlite3
import subprocess

# Get database path
db_path = subprocess.check_output(["llm", "logs", "path"]).decode().strip()

# Connect and query
conn = sqlite3.connect(db_path)
cursor = conn.execute("""
    SELECT prompt, model, datetime_utc 
    FROM responses 
    ORDER BY datetime_utc DESC 
    LIMIT 1
""")
latest_prompt, model, timestamp = cursor.fetchone()
```

## Fragment System Details

### Fragment Injection
- Fragments are injected when `-f prefix:argument` is used
- Multiple fragments can be stacked: `-f frag1:arg1 -f frag2:arg2`
- Fragments become part of system context

### Fragment Loader Implementation
```python
def memory_fragment_loader(argument):
    """
    Fragment loader function
    - argument: string after the colon in -f memory:argument
    - Returns: string content to inject, or empty string
    """
    try:
        if argument == "auto":
            profile_path = llm.user_dir() / "memory" / "profile.md"
            if profile_path.exists():
                return profile_path.read_text()
        return ""
    except Exception:
        # Silent failure - never break user's main command
        return ""
```

## Shell Integration

### Shell Function Override
The key to transparency is overriding the `llm` command:

```bash
# Add to ~/.bashrc, ~/.zshrc, etc.
llm() {
    # Always inject memory fragment
    command llm -f memory:auto "$@"
}
```

### Installation Script
```python
def install_shell_integration():
    """Add shell function to user's profile"""
    shells = ["bash", "zsh", "fish"]
    for shell in shells:
        profile_file = get_shell_profile(shell)
        if profile_file and profile_file.exists():
            add_function_to_profile(profile_file)
```

## Background Processing

### Profile Update Process
1. Monitor database for new responses
2. Extract user prompt (exclude model response)
3. Send update request to model:
   ```
   Current profile: [existing profile]
   New conversation: [user prompt]
   
   Update the user profile based on this conversation. 
   Only include relevant facts about the user. 
   If no update needed, respond with "NO_UPDATE".
   ```
4. Parse response and update profile file if changes suggested

### Threading/Async Considerations
```python
import threading
import time

class ProfileUpdater:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start_monitoring(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def _monitor_loop(self):
        while self.running:
            self.check_for_updates()
            time.sleep(5)  # Check every 5 seconds
```

## File Management

### Profile File Format
Simple Markdown format for human readability:
```markdown
# User Profile

## Personal Information
- Name: [User's name if mentioned]
- Role: [Job title/role]

## Interests
- Programming languages: Python, JavaScript
- Technologies: Machine Learning, Web Development

## Current Projects
- Working on LLM memory plugin
- Learning about plugin architectures

## Preferences
- Prefers concise explanations
- Interested in practical examples
```

### File Locking
```python
import fcntl
import contextlib

@contextlib.contextmanager
def locked_file(file_path, mode='r'):
    """Context manager for file locking"""
    with open(file_path, mode) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

## Model Interaction

### Using Same Model as User
```python
def update_profile_with_model(user_prompt, current_profile, model_name):
    """Send profile update request using same model as user"""
    update_prompt = f"""
    Current user profile:
    {current_profile}
    
    User's latest interaction:
    {user_prompt}
    
    Please update the user profile based on this new information.
    Only include relevant, factual information about the user.
    If no update is needed, respond exactly with "NO_UPDATE".
    """
    
    # Use LLM's model system
    model = llm.get_model(model_name)
    response = model.prompt(update_prompt)
    
    if response.text().strip() != "NO_UPDATE":
        save_updated_profile(response.text())
```

## Error Handling and Robustness

### Graceful Degradation
- Fragment loader returns empty string on any error
- Background updates fail silently
- Main user interaction never affected by memory system failures

### Logging and Debugging
```python
import logging

# Setup logging for debugging (optional)
logger = logging.getLogger("llm-memory")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(llm.user_dir() / "memory" / "debug.log")
logger.addHandler(handler)
```

## Testing Considerations

### Unit Tests
- Test fragment loader with various arguments
- Test profile loading/saving with file locking
- Test database monitoring logic

### Integration Tests
- Test shell function integration
- Test end-to-end profile update flow
- Test concurrent access scenarios

## Security and Privacy

### Local-Only Operation
- All data stored locally in user's LLM config directory
- No external API calls beyond existing LLM model usage
- Profile updates use same model/API as user's main request

### Data Protection
- Profile file permissions should be user-readable only
- Sensitive information detection/filtering in profile updates
- Option to disable memory system entirely

This technical guide provides all the implementation details needed to build the transparent LLM memory plugin.