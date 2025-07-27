from unittest.mock import Mock, patch
import llm

class MockLLMEnvironment:
    """Helper class to mock LLM environment for testing."""
    
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.mock_model = Mock()
        self.mock_response = Mock()
        
    def __enter__(self):
        # Mock llm.user_dir to return our temp directory
        self.user_dir_patcher = patch('llm.user_dir', return_value=self.temp_dir)
        self.user_dir_patcher.start()
        
        # Mock llm.get_model to return our mock model
        self.get_model_patcher = patch('llm.get_model', return_value=self.mock_model)
        self.get_model_patcher.start()
        
        # Setup mock response
        self.mock_response.text.return_value = "Mock profile update"
        self.mock_model.prompt.return_value = self.mock_response
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.user_dir_patcher.stop()
        self.get_model_patcher.stop()
        
    def set_model_response(self, response_text):
        """Set the response text for the mock model."""
        self.mock_response.text.return_value = response_text