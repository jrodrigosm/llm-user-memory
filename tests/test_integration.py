import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, Mock
from llm_memory import (
    memory_fragment_loader,
    ProfileMonitor,
    ensure_monitoring_started,
    install_shell_function,
    verify_shell_integration
)

class TestMemoryWorkflow:
    """Test complete memory system workflows."""
    
    def test_complete_memory_workflow(self, temp_llm_dir, mock_llm_model):
        """Test complete workflow from fragment loading to profile update."""
        memory_dir = temp_llm_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        profile_path = memory_dir / "profile.md"
        
        # Start with empty profile
        initial_profile = """# User Profile

## Personal Information
- Role: [Not specified]

## Interests
- [No interests recorded yet]

## Current Projects
- [No current projects recorded]

## Preferences
- [No preferences recorded yet]
"""
        profile_path.write_text(initial_profile)
        
        # Mock conversation data
        conversation_data = {
            'prompt': 'I am a Python developer working on AI projects',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        # Mock updated profile response
        updated_profile = """# User Profile

## Personal Information
- Role: Python Developer

## Interests
- Artificial Intelligence
- Machine Learning

## Current Projects
- AI project development

## Preferences
- [No preferences recorded yet]
"""
        mock_llm_model.prompt.return_value.text.return_value = updated_profile
        
        with patch('llm.user_dir', return_value=temp_llm_dir):
            with patch('llm.get_model', return_value=mock_llm_model):
                # 1. Test fragment loading
                with patch('llm_memory.ensure_monitoring_started'):
                    fragment = memory_fragment_loader("auto")
                assert str(fragment) == initial_profile
                
                # 2. Test profile update
                from llm_memory import update_profile_with_conversation
                result = update_profile_with_conversation(conversation_data)
                assert result is True
                
                # 3. Test updated fragment loading
                with patch('llm_memory.ensure_monitoring_started'):
                    fragment = memory_fragment_loader("auto")
                assert "Python Developer" in str(fragment)
                assert "Artificial Intelligence" in str(fragment)
    
    def test_shell_integration_workflow(self):
        """Test complete shell integration workflow."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / '.bashrc'
            
            with patch('llm_memory.detect_user_shell', return_value='bash'):
                with patch('llm_memory.find_active_shell_profile', return_value=profile_path):
                    # 1. Verify initial state
                    verification = verify_shell_integration()
                    assert verification['success'] is True
                    assert verification['shell'] == 'bash'
                    
                    # 2. Install shell function
                    result = install_shell_function('bash')
                    assert result is True
                    
                    # 3. Verify installation
                    assert profile_path.exists()
                    content = profile_path.read_text()
                    assert 'llm() {' in content
                    assert 'command llm -f memory:auto' in content
    
    def test_background_monitoring_workflow(self, temp_llm_dir, mock_llm_database):
        """Test background monitoring workflow."""
        memory_dir = temp_llm_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        profile_path = memory_dir / "profile.md"
        profile_path.write_text("# Initial Profile")
        
        monitor = ProfileMonitor()
        
        with patch('llm.user_dir', return_value=temp_llm_dir):
            with patch('llm_memory.get_llm_database_path', return_value=Path(mock_llm_database)):
                with patch('llm_memory.get_update_interval', return_value=0.1):  # Fast for testing
                    # Start monitoring
                    monitor.start()
                    assert monitor.running is True
                    
                    # Let it run briefly
                    time.sleep(0.2)
                    
                    # Stop monitoring
                    monitor.stop()
                    assert monitor.running is False

class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    def test_fragment_loader_with_corrupted_profile(self, temp_llm_dir):
        """Test fragment loader handles corrupted profile gracefully."""
        memory_dir = temp_llm_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        profile_path = memory_dir / "profile.md"
        
        # Create a file that can't be read (permission error simulation)
        profile_path.write_text("test content")
        
        with patch('llm.user_dir', return_value=temp_llm_dir):
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                result = memory_fragment_loader("auto")
                assert result == ""  # Should handle error gracefully
    
    def test_profile_update_with_llm_error(self, temp_llm_dir):
        """Test profile update handles LLM errors gracefully."""
        memory_dir = temp_llm_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        profile_path = memory_dir / "profile.md"
        profile_path.write_text("# Test Profile")
        
        conversation_data = {
            'prompt': 'Test prompt',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        with patch('llm.user_dir', return_value=temp_llm_dir):
            with patch('llm.get_model', side_effect=Exception("LLM error")):
                from llm_memory import update_profile_with_conversation
                result = update_profile_with_conversation(conversation_data)
                assert result is False  # Should handle error gracefully
    
    def test_monitor_with_database_error(self):
        """Test monitor handles database errors gracefully."""
        monitor = ProfileMonitor()
        
        with patch('llm_memory.get_latest_conversation', side_effect=Exception("DB error")):
            # Should not raise exception
            monitor._check_for_updates()
            # Monitor should continue running
            assert True  # If we reach here, error was handled gracefully

class TestConcurrencyAndLocking:
    """Test concurrent access and file locking."""
    
    def test_concurrent_profile_access(self, temp_llm_dir):
        """Test concurrent profile read/write operations."""
        memory_dir = temp_llm_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        profile_path = memory_dir / "profile.md"
        profile_path.write_text("# Initial Profile")
        
        results = []
        
        def read_profile():
            with patch('llm.user_dir', return_value=temp_llm_dir):
                from llm_memory import load_user_profile
                content = load_user_profile()
                results.append(("read", content))
        
        def write_profile():
            with patch('llm.user_dir', return_value=temp_llm_dir):
                from llm_memory import save_user_profile
                success = save_user_profile("# Updated Profile")
                results.append(("write", success))
        
        import threading
        
        # Start concurrent operations
        threads = [
            threading.Thread(target=read_profile),
            threading.Thread(target=write_profile),
            threading.Thread(target=read_profile),
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should complete successfully
        assert len(results) == 3
        assert all(result[1] for result in results)  # All should be successful