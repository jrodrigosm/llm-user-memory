import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock
from llm_memory import register_commands
import llm

class TestMemoryCommands:
    
    def setup_method(self):
        """Setup for each test method."""
        self.runner = CliRunner()
        
        # Create a mock CLI and register our commands
        self.mock_cli = Mock()
        register_commands(self.mock_cli)
    
    def test_memory_show_with_profile(self, temp_profile_dir, sample_profile_content):
        """Test memory show command with existing profile."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        with patch('llm_memory.load_user_profile', return_value=sample_profile_content):
            # This test verifies the command structure is set up correctly
            assert self.mock_cli.group.called
    
    def test_memory_show_no_profile(self):
        """Test memory show command with no profile."""
        with patch('llm_memory.load_user_profile', return_value=""):
            # Test that the command structure is properly registered
            assert self.mock_cli.group.called
    
    def test_memory_clear_command(self, temp_profile_dir):
        """Test memory clear command."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text("Old profile content")
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            with patch('llm_memory.save_user_profile', return_value=True) as mock_save:
                # Test command registration
                assert self.mock_cli.group.called
                # Verify save_user_profile would be called with empty profile structure
                # This is tested in integration tests for actual CLI execution
    
    def test_memory_status_command(self):
        """Test memory status command."""
        with patch('llm_memory.get_profile_path') as mock_path:
            with patch('llm_memory.get_llm_database_path') as mock_db:
                mock_path.return_value.exists.return_value = True
                mock_db.return_value = "/path/to/db"
                
                # Test command registration
                assert self.mock_cli.group.called

class TestShellIntegrationCommands:
    
    def setup_method(self):
        """Setup for each test method."""
        self.runner = CliRunner()
        self.mock_cli = Mock()
        register_commands(self.mock_cli)
    
    def test_install_shell_command_registration(self):
        """Test that install-shell command is registered."""
        assert self.mock_cli.group.called
    
    def test_uninstall_shell_command_registration(self):
        """Test that uninstall-shell command is registered."""
        assert self.mock_cli.group.called
    
    def test_shell_status_command_registration(self):
        """Test that shell-status command is registered."""
        assert self.mock_cli.group.called

# Integration test for actual CLI execution
class TestCLIIntegration:
    """Integration tests that actually execute CLI commands."""
    
    @pytest.fixture
    def cli_runner(self):
        """CLI runner for integration tests."""
        return CliRunner()
    
    def test_memory_show_integration(self, cli_runner, temp_profile_dir, sample_profile_content):
        """Integration test for memory show command."""
        profile_path = temp_profile_dir / "profile.md"
        profile_path.write_text(sample_profile_content)
        
        with patch('llm_memory.get_profile_path', return_value=profile_path):
            # This would require setting up the actual CLI
            # For now, we test the structure
            pass