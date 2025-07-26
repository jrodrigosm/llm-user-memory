# llm-memory

[![PyPI](https://img.shields.io/pypi/v/llm-memory.svg)](https://pypi.org/project/llm-memory/)
[![Changelog](https://img.shields.io/github/v/release/user/llm-memory?include_prereleases&label=changelog)](https://github.com/user/llm-memory/releases)
[![Tests](https://github.com/user/llm-memory/workflows/Test/badge.svg)](https://github.com/user/llm-memory/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/user/llm-memory/blob/main/LICENSE)

A transparent memory system for [LLM](https://llm.datasette.io/) that automatically maintains and uses a user profile to provide personalized AI responses.

## Installation

Install this plugin in the same environment as LLM:
```bash
llm install llm-memory
```

## Usage

After installation, set up transparent memory integration:

```bash
llm memory install-shell
```

This adds a shell function that automatically injects your user profile into every LLM interaction. Restart your terminal or run:

```bash
source ~/.bashrc  # or ~/.zshrc for zsh users
```

Now use LLM normally - your conversations will automatically include memory context:

```bash
llm "What should I work on today?"
# Response will be personalized based on your stored profile

llm "I just finished the memory plugin project"
# This information will be remembered for future conversations
```

The memory system works completely transparently. Your user profile is automatically:
- Injected as context in every prompt
- Updated in the background based on your conversations
- Stored locally in your LLM configuration directory

## Features

### Automatic Profile Building

The plugin automatically builds and maintains a user profile based on your conversations:

```bash
# First conversation
llm "I'm a Python developer working on machine learning projects"

# Later conversations automatically know this context
llm "What's the best way to optimize this model?"
# Response considers your Python/ML background
```

### Transparent Operation

No need to remember special commands or flags. Once installed, the memory system works automatically:

```bash
# These all include memory context automatically:
llm "Help me debug this code"
llm -m gpt-4 "Explain quantum computing"
llm -t my-template "Process this data"
```

### Profile Management

View and manage your stored profile:

```bash
# View current profile
llm memory show

# Clear profile and start fresh
llm memory clear

# Temporarily disable memory updates
llm memory pause

# Re-enable memory updates
llm memory resume
```

### Background Updates

Profile updates happen in the background after each conversation, so they never slow down your interactions:

```bash
llm "I switched from JavaScript to Rust development"
# ✓ Response generated immediately
# ✓ Profile updated in background: "Updating memory..."
```

### Privacy and Local Storage

All profile data is stored locally in your LLM configuration directory:
- No external services involved
- Profile updates use the same model you're already using
- Full control over your data

## Memory Profile Structure

Your profile is stored as readable Markdown in `~/.config/llm/memory/profile.md`:

```markdown
# User Profile

## Personal Information
- Role: Python Developer
- Experience: 5+ years in machine learning

## Current Projects
- Working on LLM memory plugin
- Exploring transformer architectures

## Interests
- Natural language processing
- Open source development
- Performance optimization

## Preferences
- Prefers practical examples over theory
- Likes concise, actionable advice
```

## Advanced Usage

### Manual Profile Editing

You can manually edit your profile:

```bash
# Edit profile directly
$EDITOR "$(llm memory path)"

# Or use llm memory show and copy/edit content
llm memory show > temp_profile.md
# Edit temp_profile.md
llm memory load temp_profile.md
```

### Shell Integration Details

The shell integration works by creating a function that wraps the `llm` command:

```bash
llm() {
    command llm -f memory:auto "$@"
}
```

This automatically injects the `memory:auto` fragment on every call.

### Uninstalling Shell Integration

To remove the transparent integration:

```bash
llm memory uninstall-shell
```

Then restart your terminal. You can still use memory manually with:

```bash
llm -f memory:auto "your prompt here"
```

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-memory
python -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:
```bash
pip install -e .
pip install -r requirements-dev.txt
```

To run the tests:
```bash
pytest
```

## How It Works

The plugin uses LLM's fragment loader system to inject profile context and monitors the conversation database to trigger background profile updates:

1. **Fragment Injection**: The `memory:auto` fragment loader reads your profile and injects it as context
2. **Database Monitoring**: A background process watches for new conversations in LLM's SQLite database
3. **Profile Updates**: After each conversation, the same model you used gets a request to update your profile
4. **Transparent Operation**: Shell function integration makes this completely automatic

## Troubleshooting

### Memory not working
Check if shell integration is active:
```bash
type llm
# Should show: llm is a function
```

### Profile not updating
Check if background daemon is running:
```bash
llm memory status
```

### Reset everything
```bash
llm memory clear
llm memory uninstall-shell
llm memory install-shell
```

## Configuration

Memory behavior can be configured via environment variables:

```bash
# Disable background updates
export LLM_MEMORY_UPDATES=false

# Change update frequency (seconds)
export LLM_MEMORY_UPDATE_INTERVAL=10

# Disable memory system entirely
export LLM_MEMORY_DISABLED=true
```