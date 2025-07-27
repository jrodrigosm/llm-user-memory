import pytest
import threading
import time
from pathlib import Path
from unittest.mock import patch, Mock
from llm_memory import ProfileMonitor, ensure_monitoring_started, get_latest_conversation

class TestProfileMonitor:
    
    def test_profile_monitor_start_stop(self):
        """Test starting and stopping profile monitor."""
        monitor = ProfileMonitor()
        
        assert monitor.running is False
        assert monitor.thread is None
        
        monitor.start()
        assert monitor.running is True
        assert monitor.thread is not None
        assert monitor.thread.is_alive()
        
        monitor.stop()
        assert monitor.running is False
    
    def test_profile_monitor_pause_resume(self):
        """Test pausing and resuming profile monitor."""
        monitor = ProfileMonitor()
        
        assert monitor.paused is False
        
        monitor.pause()
        assert monitor.paused is True
        
        monitor.resume()
        assert monitor.paused is False
    
    def test_profile_monitor_disabled(self, clean_environment):
        """Test monitor doesn't start when memory is disabled."""
        import os
        os.environ['LLM_MEMORY_DISABLED'] = 'true'
        
        monitor = ProfileMonitor()
        monitor.start()
        
        assert monitor.running is False
        assert monitor.thread is None
    
    def test_profile_monitor_check_for_updates(self):
        """Test monitor update checking."""
        monitor = ProfileMonitor()
        
        conversation_data = {
            'prompt': 'Test prompt',
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        with patch('llm_memory.get_latest_conversation', return_value=conversation_data):
            with patch('llm_memory.update_profile_with_conversation', return_value=True) as mock_update:
                monitor._check_for_updates()
                
        mock_update.assert_called_once_with(conversation_data)
        assert monitor.last_check_timestamp == '2024-01-01 12:00:00'
    
    def test_profile_monitor_no_conversation(self):
        """Test monitor when no new conversation exists."""
        monitor = ProfileMonitor()
        
        with patch('llm_memory.get_latest_conversation', return_value=None):
            with patch('llm_memory.update_profile_with_conversation') as mock_update:
                monitor._check_for_updates()
                
        mock_update.assert_not_called()
    
    def test_profile_monitor_empty_prompt(self):
        """Test monitor skips empty prompts."""
        monitor = ProfileMonitor()
        
        conversation_data = {
            'prompt': '',  # Empty prompt
            'model': 'gpt-4',
            'datetime_utc': '2024-01-01 12:00:00',
            'id': 123
        }
        
        with patch('llm_memory.get_latest_conversation', return_value=conversation_data):
            with patch('llm_memory.update_profile_with_conversation') as mock_update:
                monitor._check_for_updates()
                
        mock_update.assert_not_called()
    
    def test_profile_monitor_updates_disabled(self, clean_environment):
        """Test monitor respects updates disabled setting."""
        import os
        os.environ['LLM_MEMORY_UPDATES'] = 'false'
        
        monitor = ProfileMonitor()
        
        with patch('llm_memory.get_latest_conversation') as mock_get:
            monitor._check_for_updates()
            
        mock_get.assert_not_called()

class TestMonitoringLoop:
    
    def test_monitor_loop_runs(self):
        """Test that monitor loop runs and can be stopped."""
        monitor = ProfileMonitor()
        
        with patch('llm_memory.get_update_interval', return_value=0.1):  # Fast interval for testing
            monitor.start()
            
            # Let it run briefly
            time.sleep(0.2)
            
            assert monitor.running is True
            assert monitor.thread.is_alive()
            
            monitor.stop()
            
            # Give it time to stop
            time.sleep(0.1)
            assert monitor.running is False
    
    def test_monitor_loop_error_handling(self):
        """Test monitor loop handles errors gracefully."""
        monitor = ProfileMonitor()
        
        with patch('llm_memory.get_update_interval', return_value=0.1):
            with patch.object(monitor, '_check_for_updates', side_effect=Exception("Test error")):
                monitor.start()
                
                # Let it run and encounter errors
                time.sleep(0.2)
                
                # Should still be running despite errors
                assert monitor.running is True
                
                monitor.stop()

class TestEnsureMonitoringStarted:
    
    def test_ensure_monitoring_started_success(self):
        """Test ensure_monitoring_started starts monitor."""
        with patch('llm_memory._profile_monitor') as mock_monitor:
            mock_monitor.running = False
            
            with patch('llm_memory.is_memory_disabled', return_value=False):
                ensure_monitoring_started()
                
            mock_monitor.start.assert_called_once()
    
    def test_ensure_monitoring_started_already_running(self):
        """Test ensure_monitoring_started when already running."""
        with patch('llm_memory._profile_monitor') as mock_monitor:
            mock_monitor.running = True
            
            ensure_monitoring_started()
            
            mock_monitor.start.assert_not_called()
    
    def test_ensure_monitoring_started_disabled(self):
        """Test ensure_monitoring_started when memory is disabled."""
        with patch('llm_memory._profile_monitor') as mock_monitor:
            mock_monitor.running = False
            
            with patch('llm_memory.is_memory_disabled', return_value=True):
                ensure_monitoring_started()
                
            mock_monitor.start.assert_not_called()

class TestDatabaseOperations:
    
    def test_get_latest_conversation_success(self, mock_llm_database):
        """Test getting latest conversation from database."""
        with patch('llm_memory.get_llm_database_path', return_value=Path(mock_llm_database)):
            result = get_latest_conversation()
            
        assert result is not None
        assert result['prompt'] == 'Test prompt'
        assert result['model'] == 'gpt-4'
        assert result['datetime_utc'] == '2024-01-01 12:00:00'
    
    def test_get_latest_conversation_with_timestamp(self, mock_llm_database):
        """Test getting latest conversation since timestamp."""
        with patch('llm_memory.get_llm_database_path', return_value=Path(mock_llm_database)):
            # This should return None since our test data is from 2024-01-01
            result = get_latest_conversation(since_timestamp='2024-12-01 00:00:00')
            
        assert result is None
    
    def test_get_latest_conversation_no_database(self):
        """Test getting conversation when database path is None."""
        with patch('llm_memory.get_llm_database_path', return_value=None):
            result = get_latest_conversation()
            
        assert result is None
    
    def test_get_latest_conversation_error(self):
        """Test error handling in get_latest_conversation."""
        with patch('llm_memory.get_llm_database_path', side_effect=Exception("Test error")):
            result = get_latest_conversation()
            
        assert result is None