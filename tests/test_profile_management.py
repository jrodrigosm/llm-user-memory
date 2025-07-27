import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from llm_memory import (
    save_user_profile, 
    get_profile_path,
    update_profile_with_conversation
)

class TestProfileManagement:
    
    def test_save_user_profile_success(self, temp_profile_dir, sample_profile_content):
        """Test successful profile saving."""
        profile_path = temp_profile_dir / "profile.md"
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            result = save_user_profile(sample_profile_content)
            
        assert result is True
        assert profile_path.read_text() == sample_profile_content
    
    def test_save_user_profile_creates_directory(self, temp_llm_dir):
        """Test that save_user_profile creates directory if it doesn't exist."""
        profile_path = temp_llm_dir / "memory" / "profile.md"
        
        # Actually test the real get_profile_path function which should create directory
        with patch('llm.user_dir', return_value=temp_llm_dir):
            result = save_user_profile("test content")
            
        assert result is True
        assert profile_path.parent.exists()
        assert profile_path.read_text() == "test content"
    
    def test_get_profile_path_creates_directory(self, temp_llm_dir):
        """Test that get_profile_path creates memory directory."""
        with patch('llm.user_dir', return_value=temp_llm_dir):
            profile_path = get_profile_path()
            
        expected_path = temp_llm_dir / "memory" / "profile.md"
        assert profile_path == expected_path
        assert profile_path.parent.exists()

class TestProfileUpdates:
    
    def test_update_profile_with_conversation_success(self, temp_profile_dir, sample_profile_content, mock_llm_model):
        """Test successful profile update from conversation."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        conversation_data = {
            'prompt': 'I am now working on React development',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        updated_profile = sample_profile_content + "\n- Currently learning React"
        mock_llm_model.prompt.return_value.text.return_value = updated_profile
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm.get_model', return_value=mock_llm_model):
                result = update_profile_with_conversation(conversation_data)
                
        assert result is True
        assert profile_path.read_text() == updated_profile
    
    def test_update_profile_no_update_needed(self, temp_profile_dir, sample_profile_content, mock_llm_model):
        """Test when no profile update is needed."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        conversation_data = {
            'prompt': 'Hello',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        mock_llm_model.prompt.return_value.text.return_value = "NO_UPDATE"
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm.get_model', return_value=mock_llm_model):
                result = update_profile_with_conversation(conversation_data)
                
        assert result is False
        assert profile_path.read_text() == sample_profile_content
    
    def test_update_profile_creates_initial_profile(self, temp_profile_dir, mock_llm_model):
        """Test profile update creates initial profile if none exists."""
        profile_path = temp_profile_dir / "profile.md"
        
        conversation_data = {
            'prompt': 'I am a Python developer',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        updated_profile = "# User Profile\n\n## Personal Information\n- Role: Python Developer"
        mock_llm_model.prompt.return_value.text.return_value = updated_profile
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm.get_model', return_value=mock_llm_model):
                result = update_profile_with_conversation(conversation_data)
                
        assert result is True
        assert "Python Developer" in profile_path.read_text()
    
    def test_update_profile_updates_disabled(self, clean_environment, temp_profile_dir):
        """Test profile update is skipped when updates are disabled."""
        import os
        os.environ['LLM_MEMORY_UPDATES'] = 'false'
        
        conversation_data = {
            'prompt': 'Test prompt',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        result = update_profile_with_conversation(conversation_data)
        assert result is False