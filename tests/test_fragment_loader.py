import pytest
from unittest.mock import patch, Mock
from llm_memory import memory_fragment_loader, load_user_profile
import llm

class TestFragmentLoader:
    
    def test_memory_fragment_loader_auto_with_profile(self, temp_profile_dir, sample_profile_content):
        """Test fragment loader returns profile content for 'auto' argument."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm_memory.ensure_monitoring_started'):
                result = memory_fragment_loader("auto")
                
        assert isinstance(result, llm.Fragment)
        assert "Python Developer" in result
        assert result.source == "memory:profile"
    
    def test_memory_fragment_loader_auto_no_profile(self, temp_profile_dir):
        """Test fragment loader returns empty string when no profile exists."""
        profile_path = temp_profile_dir / "profile.md"
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm_memory.ensure_monitoring_started'):
                result = memory_fragment_loader("auto")
                
        assert result == ""
    
    def test_memory_fragment_loader_test_argument(self):
        """Test fragment loader returns test fragment for 'test' argument."""
        result = memory_fragment_loader("test")
        
        assert isinstance(result, llm.Fragment)
        assert "TEST FRAGMENT" in result
        assert result.source == "memory:test"
    
    def test_memory_fragment_loader_disabled(self, clean_environment):
        """Test fragment loader returns empty string when memory is disabled."""
        import os
        os.environ['LLM_MEMORY_DISABLED'] = 'true'
        
        result = memory_fragment_loader("auto")
        assert result == ""
    
    def test_memory_fragment_loader_error_handling(self):
        """Test fragment loader handles errors gracefully."""
        with patch('llm_memory.load_user_profile', side_effect=Exception("Test error")):
            result = memory_fragment_loader("auto")
            assert result == ""

class TestProfileLoading:
    
    def test_load_user_profile_success(self, temp_profile_dir, sample_profile_content):
        """Test successful profile loading."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            result = load_user_profile()
            
        assert result == sample_profile_content
    
    def test_load_user_profile_no_file(self, temp_profile_dir):
        """Test profile loading when file doesn't exist."""
        profile_path = temp_profile_dir / "profile.md"
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            result = load_user_profile()
            
        assert result == ""
    
    def test_load_user_profile_error_handling(self):
        """Test profile loading handles errors gracefully."""
        with patch('llm_memory.get_profile_path', side_effect=Exception("Test error")):
            result = load_user_profile()
            assert result == ""