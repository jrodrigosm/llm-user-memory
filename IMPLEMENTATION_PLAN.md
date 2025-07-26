# LLM Memory Plugin - Transparent Implementation Plan

## Overview
Create a completely transparent memory system that requires zero user behavior change. The plugin will monitor conversations, update user profiles, and automatically inject profiles into all prompts.

## Architecture Components

### 1. Plugin Structure
- `llm-memory/llm_memory.py` - Main plugin code
- `llm-memory/pyproject.toml` - Plugin configuration  
- `llm-memory/daemon.py` - Background monitoring daemon
- `llm-memory/shell_setup.sh` - Shell integration script

### 2. Memory Fragment Loader
- Register fragment loader with `@llm.hookimpl def register_fragment_loaders(register)`
- Create `memory:auto` fragment that reads from `~/.config/llm/memory/profile.md`
- Fragment loader returns current user profile or empty string if no profile exists
- Profile injected as system context to provide background about user

### 3. Database Monitor Service  
- Background daemon that monitors `$(llm logs path)` SQLite database
- Uses SQLite triggers or polling to detect new response entries
- Extracts user prompt from new responses (excludes model's response)
- Sends prompt + current profile to same model user just used
- Asks model: "Update this user profile based on this new conversation"
- Updates profile file if model suggests changes

### 4. Transparent Shell Integration
- Install creates shell function that overrides `llm` command:
  ```bash
  llm() { command llm -f memory:auto "$@"; }
  ```
- Function automatically injects memory fragment on every call
- User runs normal `llm` commands, gets profile-aware responses
- Shell function also starts background daemon if not running

### 5. Profile Management
- Profile stored as simple markdown in `~/.config/llm/memory/profile.md`
- Includes user preferences, context, interests, work details
- File locking prevents concurrent access issues
- Graceful degradation if profile operations fail

### 6. Installation & Setup Process
1. `pip install llm-memory` installs plugin
2. `llm memory install-shell` adds function to user's shell profile
3. User restarts shell or sources profile
4. All subsequent `llm` commands automatically include memory
5. Background updates happen transparently

## User Experience
- **Completely transparent**: User runs `llm "What should I work on today?"` 
- Profile automatically injected as context
- Response aware of user's projects, preferences, history
- Memory updated in background after response
- Optional: Show brief "Updating memory..." message before exit

## Technical Implementation Details
- **Profile Updates**: Non-blocking, happen after user sees response
- **Error Handling**: Silent failures, never break user's main interaction
- **Model Selection**: Use same model for updates as user's main query
- **Privacy**: All data stays local, no external services
- **Performance**: Minimal overhead, async background processing

## Commands for Power Users
- `llm memory show` - Display current profile
- `llm memory clear` - Reset profile  
- `llm memory pause/resume` - Temporarily disable updates
- `llm memory uninstall-shell` - Remove shell integration

This approach achieves complete transparency while leveraging LLM's existing fragment system.