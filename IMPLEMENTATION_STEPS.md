# Step-by-Step Implementation Guide for LLM Memory Plugin

## Phase 1: Basic Plugin Structure (Days 1-2)
**Goal**: Create a working LLM plugin that can be installed and recognized

### Step 1.1: Set up project structure
- Create `llm_memory.py` (main plugin file)
- Create `pyproject.toml` with basic metadata and entry points
- Add basic imports and plugin registration hook

### Step 1.2: Test plugin installation
- Run `llm install -e .` to install plugin
- Verify with `llm plugins` command
- Ensure no errors in plugin loading

## Phase 2: Memory Fragment Loader (Days 3-4)
**Goal**: Implement core memory injection functionality

### Step 2.1: Implement fragment loader hook
- Add `register_fragment_loaders` hook implementation
- Create `memory_fragment_loader` function
- Handle `memory:auto` argument to load profile
- Return empty string when no profile exists

### Step 2.2: Profile file management
- Create functions to read/write profile from `~/.config/llm/memory/profile.md`
- Implement proper directory creation and file handling
- Add basic error handling (silent failures)

### Step 2.3: Test fragment loading
- Create a test profile file manually
- Test `llm -f memory:auto "test prompt"` command
- Verify profile content is injected into prompt

## Phase 3: CLI Commands (Days 5-6) 
**Goal**: Add user-facing memory management commands

### Step 3.1: Register CLI commands
- Add `register_commands` hook
- Create `memory` command group
- Implement `show`, `clear`, `status` subcommands

### Step 3.2: Implement command functionality
- `show`: Display current profile content
- `clear`: Delete profile file and recreate empty one
- `status`: Show if memory system is active
- Add `path` command to show profile file location

### Step 3.3: Test CLI commands
- Test each command independently
- Verify proper error messages for missing profiles
- Test file operations work correctly

## Phase 4: Database Monitoring & Updates (Days 7-10)
**Goal**: Implement automatic profile updates from conversations

### Step 4.1: Database access setup
- Implement function to find LLM database path via `llm logs path`
- Create database connection and query functionality
- Test reading recent conversations from database

### Step 4.2: Profile update logic
- Create function to send profile update requests to LLM models
- Implement prompt template for profile updates
- Add logic to parse model responses and update profile
- Handle "NO_UPDATE" responses appropriately

### Step 4.3: Background monitoring service
- Implement database polling mechanism (check every 5 seconds)
- Add thread-based background monitoring
- Start monitoring when fragment loader is first used
- Implement proper shutdown handling

### Step 4.4: Test update system
- Create test conversations and verify profile updates
- Test with different models (GPT-4, Claude, etc.)
- Verify background updates don't interfere with main commands

## Phase 5: Shell Integration (Days 11-12)
**Goal**: Make the system completely transparent to users

### Step 5.1: Shell detection and modification
- Implement functions to detect user's shell (bash, zsh, fish)
- Create shell function that wraps `llm` command
- Add functions to modify shell profile files safely

### Step 5.2: Installation commands
- Add `install-shell` and `uninstall-shell` commands
- Implement proper backup of shell profiles before modification
- Add verification that shell function was installed correctly

### Step 5.3: Test shell integration
- Test in different shells (bash, zsh)
- Verify `llm "test"` automatically includes memory
- Test that normal LLM functionality still works
- Verify uninstall removes shell function cleanly

## Phase 6: Robustness & Polish (Days 13-15)
**Goal**: Add production-ready error handling and configuration

### Step 6.1: Error handling improvements
- Add comprehensive try/catch blocks around all operations
- Implement file locking for concurrent access safety
- Add logging for debugging (optional, off by default)
- Ensure main LLM functionality never breaks due to memory errors

### Step 6.2: Configuration options
- Add environment variable support (`LLM_MEMORY_DISABLED`, etc.)
- Implement `pause`/`resume` functionality for updates
- Add configuration for update frequency
- Test all configuration options

### Step 6.3: Final testing & documentation
- Test complete end-to-end workflows
- Test edge cases (empty profiles, database access errors, etc.)
- Verify shell integration works after terminal restarts
- Test uninstall and reinstall procedures

## Detailed Implementation Notes

### Phase 1 Details

#### pyproject.toml Structure
```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "llm-memory"
version = "0.1.0"
description = "Transparent memory system for LLM"
readme = "README.md"
requires-python = ">=3.8"
dependencies = ["llm>=0.13"]

[project.entry-points.llm]
llm-memory = "llm_memory"
```

#### Basic Plugin Structure
```python
import llm

@llm.hookimpl
def register_fragment_loaders(register):
    register("memory", memory_fragment_loader)

def memory_fragment_loader(argument):
    # Implementation here
    pass
```

### Phase 2 Details

#### Fragment Loader Implementation
- Check if argument is "auto"
- Read profile from `llm.user_dir() / "memory" / "profile.md"`
- Return content or empty string
- Handle all exceptions silently

#### Profile File Format
```markdown
# User Profile

## Personal Information
- Role: [Job title/role]

## Interests
- Programming languages: Python, JavaScript
- Technologies: Machine Learning, Web Development

## Current Projects
- Working on LLM memory plugin

## Preferences
- Prefers concise explanations
- Interested in practical examples
```

### Phase 4 Details

#### Database Query Example
```python
import sqlite3
import subprocess

# Get database path
db_path = subprocess.check_output(["llm", "logs", "path"]).decode().strip()

# Query latest conversation
conn = sqlite3.connect(db_path)
cursor = conn.execute("""
    SELECT prompt, model, datetime_utc 
    FROM responses 
    ORDER BY datetime_utc DESC 
    LIMIT 1
""")
```

#### Profile Update Prompt Template
```
Current user profile:
{current_profile}

User's latest interaction:
{user_prompt}

Please update the user profile based on this new information.
Only include relevant, factual information about the user.
If no update is needed, respond exactly with "NO_UPDATE".
```

### Phase 5 Details

#### Shell Function Template
```bash
# LLM Memory Plugin Integration
llm() {
    command llm -f memory:auto "$@"
}
```

#### Shell Profile Detection
- Check for `~/.bashrc`, `~/.zshrc`, `~/.config/fish/config.fish`
- Backup original files before modification
- Add function at end of file with clear comments

## Testing Strategy for Each Phase

### Unit Tests
- Test fragment loader with various arguments
- Test profile file read/write operations
- Test database query functions
- Test shell profile modification functions

### Integration Tests
- Test plugin installation and recognition by LLM
- Test fragment injection in actual LLM commands
- Test CLI commands with real profile files
- Test background monitoring with real database

### Manual Testing
- Install plugin and verify `llm plugins` output
- Test `llm -f memory:auto "prompt"` manually
- Test all CLI commands: `show`, `clear`, `status`, `path`
- Test shell integration in clean shell environment
- Test complete workflow: install → use → update → verify

### Error Scenario Testing
- Test with missing profile files
- Test with corrupted profile files
- Test with database access errors
- Test with network failures during model calls
- Test concurrent access to profile files

## Key Success Criteria

### Phase 1 Success
- [x] Plugin installs without errors
- [x] `llm plugins` shows llm-memory in list
- [x] No import or loading errors

### Phase 2 Success
- [x] `llm -f memory:auto "test"` includes profile in prompt
- [x] Empty profile returns empty string (no errors)
- [x] Profile file is read correctly from user directory

### Phase 3 Success
- [ ] All CLI commands work: `llm memory show/clear/status/path`
- [ ] Commands handle missing profiles gracefully
- [ ] File operations work correctly

### Phase 4 Success
- [ ] Database monitoring detects new conversations
- [ ] Profile updates based on conversation content
- [ ] Background updates don't interfere with main LLM usage
- [ ] Works with different LLM models

### Phase 5 Success
- [ ] Shell function installation works in bash/zsh
- [ ] `llm "test"` automatically includes memory (transparent)
- [ ] Normal LLM functionality preserved
- [ ] Uninstall removes shell function completely

### Phase 6 Success
- [ ] System handles all error scenarios gracefully
- [ ] Configuration options work as expected
- [ ] Complete workflows work end-to-end
- [ ] No memory leaks or resource issues

## Common Pitfalls to Avoid

1. **Silent Failures**: Ensure errors in memory system never break main LLM functionality
2. **File Locking**: Implement proper locking for concurrent access to profile files
3. **Shell Compatibility**: Test shell integration across different shells and environments
4. **Database Access**: Handle cases where LLM database is locked or inaccessible
5. **Model Availability**: Handle cases where requested model is not available for updates
6. **Profile Corruption**: Validate profile content and handle corruption gracefully
7. **Memory Leaks**: Ensure background threads are properly managed and cleaned up

## Development Tools & Commands

### Plugin Development
```bash
# Install in development mode
cd llm-memory
llm install -e .

# Verify installation
llm plugins

# Test fragment loader
llm -f memory:auto "test prompt"

# Test CLI commands
llm memory show
llm memory clear
```

### Testing Commands
```bash
# Check database path
llm logs path

# View recent conversations
llm logs -n 5

# Test shell function
type llm  # Should show "llm is a function"
```

This comprehensive guide provides everything a junior developer needs to implement the LLM Memory Plugin incrementally, with clear success criteria and testing strategies for each phase.
