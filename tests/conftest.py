import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import sqlite3
import os

@pytest.fixture
def temp_llm_dir():
    """Create a temporary LLM user directory for testing."""
    temp_dir = tempfile.mkdtemp()
    with patch('llm.user_dir', return_value=Path(temp_dir)):
        yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_profile_dir(temp_llm_dir):
    """Create a temporary memory profile directory."""
    memory_dir = temp_llm_dir / "memory"
    memory_dir.mkdir(exist_ok=True)
    return memory_dir

@pytest.fixture
def sample_profile_content():
    """Sample profile content for testing."""
    return """# User Profile

## Personal Information
- Role: Python Developer
- Experience: 5+ years

## Interests
- Machine Learning
- Open Source Development

## Current Projects
- Working on LLM memory plugin
- Building automated testing framework

## Preferences
- Prefers practical examples
- Likes concise documentation
"""

@pytest.fixture
def mock_llm_database():
    """Create a mock LLM database for testing."""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    conn = sqlite3.connect(temp_db.name)
    
    # Create the responses table structure
    conn.execute("""
        CREATE TABLE responses (
            id INTEGER PRIMARY KEY,
            prompt TEXT,
            response TEXT,
            model TEXT,
            datetime_utc TEXT
        )
    """)
    
    # Insert sample data
    conn.execute("""
        INSERT INTO responses (prompt, response, model, datetime_utc)
        VALUES (?, ?, ?, ?)
    """, ("Test prompt", "Test response", "gpt-4", "2024-01-01 12:00:00"))
    
    conn.commit()
    conn.close()
    
    yield temp_db.name
    os.unlink(temp_db.name)

@pytest.fixture
def mock_llm_model():
    """Mock LLM model for testing profile updates."""
    mock_model = Mock()
    mock_response = Mock()
    mock_response.text.return_value = "Updated profile content"
    mock_model.prompt.return_value = mock_response
    return mock_model

@pytest.fixture
def clean_environment():
    """Clean environment variables before and after tests."""
    env_vars = [
        'LLM_MEMORY_DISABLED',
        'LLM_MEMORY_UPDATES', 
        'LLM_MEMORY_UPDATE_INTERVAL',
        'LLM_MEMORY_DEBUG'
    ]
    
    # Store original values
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]