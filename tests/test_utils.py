import pytest
from unittest.mock import patch
import os
from llm_memory import (
    is_memory_disabled,
    is_updates_disabled,
    get_update_interval,
    get_logger
)

class TestConfigurationUtils:
    
    def test_is_memory_disabled_true(self, clean_environment):
        """Test memory disabled detection when enabled."""
        os.environ['LLM_MEMORY_DISABLED'] = 'true'
        assert is_memory_disabled() is True
        
        os.environ['LLM_MEMORY_DISABLED'] = '1'
        assert is_memory_disabled() is True
        
        os.environ['LLM_MEMORY_DISABLED'] = 'yes'
        assert is_memory_disabled() is True
    
    def test_is_memory_disabled_false(self, clean_environment):
        """Test memory disabled detection when not disabled."""
        assert is_memory_disabled() is False
        
        os.environ['LLM_MEMORY_DISABLED'] = 'false'
        assert is_memory_disabled() is False
        
        os.environ['LLM_MEMORY_DISABLED'] = '0'
        assert is_memory_disabled() is False
    
    def test_is_updates_disabled_true(self, clean_environment):
        """Test updates disabled detection when disabled."""
        os.environ['LLM_MEMORY_UPDATES'] = 'false'
        assert is_updates_disabled() is True
        
        os.environ['LLM_MEMORY_UPDATES'] = '0'
        assert is_updates_disabled() is True
        
        os.environ['LLM_MEMORY_UPDATES'] = 'no'
        assert is_updates_disabled() is True
    
    def test_is_updates_disabled_false(self, clean_environment):
        """Test updates disabled detection when not disabled."""
        assert is_updates_disabled() is False
        
        os.environ['LLM_MEMORY_UPDATES'] = 'true'
        assert is_updates_disabled() is False
        
        os.environ['LLM_MEMORY_UPDATES'] = '1'
        assert is_updates_disabled() is False
    
    def test_get_update_interval_default(self, clean_environment):
        """Test default update interval."""
        assert get_update_interval() == 5
    
    def test_get_update_interval_custom(self, clean_environment):
        """Test custom update interval."""
        os.environ['LLM_MEMORY_UPDATE_INTERVAL'] = '10'
        assert get_update_interval() == 10
    
    def test_get_update_interval_minimum(self, clean_environment):
        """Test minimum update interval."""
        os.environ['LLM_MEMORY_UPDATE_INTERVAL'] = '0'
        assert get_update_interval() == 1  # Should be minimum 1
        
        os.environ['LLM_MEMORY_UPDATE_INTERVAL'] = '-5'
        assert get_update_interval() == 1  # Should be minimum 1
    
    def test_get_update_interval_invalid(self, clean_environment):
        """Test invalid update interval."""
        os.environ['LLM_MEMORY_UPDATE_INTERVAL'] = 'invalid'
        assert get_update_interval() == 5  # Should fallback to default
        
        os.environ['LLM_MEMORY_UPDATE_INTERVAL'] = ''
        assert get_update_interval() == 5  # Should fallback to default

class TestLogging:
    
    def test_get_logger_debug_enabled(self, clean_environment, temp_llm_dir):
        """Test logger configuration with debug enabled."""
        os.environ['LLM_MEMORY_DEBUG'] = 'true'
        
        with patch('llm.user_dir', return_value=temp_llm_dir):
            logger = get_logger()
            
        assert logger.level == 10  # DEBUG level
        assert len(logger.handlers) > 0
    
    def test_get_logger_debug_disabled(self, clean_environment):
        """Test logger configuration with debug disabled."""
        # Clear any existing handlers to ensure clean state
        import logging
        logger_instance = logging.getLogger("llm-memory")
        logger_instance.handlers.clear()
        
        logger = get_logger()
        
        assert logger.level == 50  # CRITICAL level (effectively disabled)
    
    def test_get_logger_multiple_calls(self, clean_environment):
        """Test that multiple calls return the same configured logger."""
        # Clear any existing handlers to ensure clean state
        import logging
        logger_instance = logging.getLogger("llm-memory")
        logger_instance.handlers.clear()
        
        logger1 = get_logger()
        logger2 = get_logger()
        
        assert logger1 is logger2
        assert len(logger1.handlers) == len(logger2.handlers)