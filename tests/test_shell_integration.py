import pytest
from unittest.mock import patch, Mock, mock_open
from pathlib import Path
from llm_memory import (
    detect_user_shell,
    get_shell_profile_paths,
    find_active_shell_profile,
    install_shell_function,
    uninstall_shell_function,
    is_shell_function_installed,
    verify_shell_integration
)

class TestShellDetection:
    
    def test_detect_user_shell_bash(self, clean_environment):
        """Test detecting bash shell."""
        import os
        os.environ['SHELL'] = '/bin/bash'
        
        result = detect_user_shell()
        assert result == 'bash'
    
    def test_detect_user_shell_zsh(self, clean_environment):
        """Test detecting zsh shell."""
        import os
        os.environ['SHELL'] = '/usr/bin/zsh'
        
        result = detect_user_shell()
        assert result == 'zsh'
    
    def test_detect_user_shell_fish(self, clean_environment):
        """Test detecting fish shell."""
        import os
        os.environ['SHELL'] = '/usr/local/bin/fish'
        
        result = detect_user_shell()
        assert result == 'fish'
    
    def test_detect_user_shell_unsupported(self, clean_environment):
        """Test detecting unsupported shell."""
        import os
        os.environ['SHELL'] = '/bin/tcsh'
        
        result = detect_user_shell()
        assert result is None
    
    def test_detect_user_shell_no_env(self, clean_environment):
        """Test when SHELL environment variable is not set."""
        result = detect_user_shell()
        assert result is None

class TestShellProfilePaths:
    
    def test_get_shell_profile_paths_bash(self):
        """Test getting bash profile paths."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            
            paths = get_shell_profile_paths('bash')
            
            expected = [
                Path('/home/user/.bashrc'),
                Path('/home/user/.bash_profile'),
                Path('/home/user/.profile')
            ]
            assert paths == expected
    
    def test_get_shell_profile_paths_zsh(self):
        """Test getting zsh profile paths."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            
            paths = get_shell_profile_paths('zsh')
            
            expected = [
                Path('/home/user/.zshrc'),
                Path('/home/user/.zprofile'),
                Path('/home/user/.profile')
            ]
            assert paths == expected
    
    def test_get_shell_profile_paths_fish(self):
        """Test getting fish profile paths."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            
            paths = get_shell_profile_paths('fish')
            
            expected = [Path('/home/user/.config/fish/config.fish')]
            assert paths == expected
    
    def test_get_shell_profile_paths_unsupported(self):
        """Test getting profile paths for unsupported shell."""
        paths = get_shell_profile_paths('tcsh')
        assert paths == []

class TestActiveShellProfile:
    
    def test_find_active_shell_profile_existing_file(self):
        """Test finding active profile when file exists."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            
            # Create temporary files to simulate existing profile
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                bashrc = temp_path / '.bashrc'
                bashrc.write_text("# existing bashrc")
                
                with patch('llm_memory.get_shell_profile_paths', return_value=[bashrc]):
                    result = find_active_shell_profile('bash')
                    
                assert result == bashrc
    
    def test_find_active_shell_profile_no_existing_file(self):
        """Test finding active profile when no file exists."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            
            with patch('llm_memory.get_shell_profile_paths') as mock_paths:
                mock_path = Mock()
                mock_path.exists.return_value = False
                mock_paths.return_value = [mock_path]
                
                result = find_active_shell_profile('bash')
                
            assert result == mock_path

class TestShellFunctionInstallation:
    
    def test_is_shell_function_installed_true(self):
        """Test detecting installed shell function."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = '''
# LLM Memory Plugin Integration
llm() {
    command llm -f memory:auto "$@"
}
'''
        
        result = is_shell_function_installed(mock_path)
        assert result is True
    
    def test_is_shell_function_installed_false(self):
        """Test detecting uninstalled shell function."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "# Other shell configuration"
        
        result = is_shell_function_installed(mock_path)
        assert result is False
    
    def test_is_shell_function_installed_no_file(self):
        """Test when profile file doesn't exist."""
        mock_path = Mock()
        mock_path.exists.return_value = False
        
        result = is_shell_function_installed(mock_path)
        assert result is False
    
    def test_install_shell_function_new_file(self):
        """Test installing shell function in new file."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / '.bashrc'
            
            with patch('llm_memory.find_active_shell_profile', return_value=profile_path):
                with patch('llm_memory.is_shell_function_installed', return_value=False):
                    result = install_shell_function('bash')
                    
            assert result is True
            assert profile_path.exists()
            content = profile_path.read_text()
            assert 'llm() {' in content
            assert 'command llm -f memory:auto' in content
    
    def test_install_shell_function_existing_file(self):
        """Test installing shell function in existing file."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / '.bashrc'
            profile_path.write_text("# existing content\n")
            
            with patch('llm_memory.find_active_shell_profile', return_value=profile_path):
                with patch('llm_memory.is_shell_function_installed', return_value=False):
                    result = install_shell_function('bash')
                    
            assert result is True
            content = profile_path.read_text()
            assert '# existing content' in content
            assert 'llm() {' in content
            assert 'command llm -f memory:auto' in content
    
    def test_install_shell_function_already_installed(self):
        """Test installing shell function when already installed."""
        mock_path = Mock()
        
        with patch('llm_memory.find_active_shell_profile', return_value=mock_path):
            with patch('llm_memory.is_shell_function_installed', return_value=True):
                result = install_shell_function('bash')
                
        assert result is True
    
    def test_uninstall_shell_function_success(self):
        """Test successful shell function removal."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = '''# Other config
# LLM Memory Plugin Integration
# This function automatically injects memory context into all llm commands
llm() {
    command llm -f memory:auto "$@"
}
# More config'''
        
        with patch('llm_memory.find_active_shell_profile', return_value=mock_path):
            result = uninstall_shell_function('bash')
            
        assert result is True
        mock_path.write_text.assert_called_once()
        written_content = mock_path.write_text.call_args[0][0]
        assert 'llm() {' not in written_content
        assert '# Other config' in written_content
        assert '# More config' in written_content

class TestShellIntegrationVerification:
    
    def test_verify_shell_integration_success(self):
        """Test successful shell integration verification."""
        mock_path = Path('/home/user/.bashrc')
        
        with patch('llm_memory.detect_user_shell', return_value='bash'):
            with patch('llm_memory.find_active_shell_profile', return_value=mock_path):
                with patch('llm_memory.is_shell_function_installed', return_value=True):
                    result = verify_shell_integration()
                    
        assert result['success'] is True
        assert result['shell'] == 'bash'
        assert result['profile_path'] == str(mock_path)
        assert result['function_installed'] is True
    
    def test_verify_shell_integration_no_shell(self):
        """Test verification when shell cannot be detected."""
        with patch('llm_memory.detect_user_shell', return_value=None):
            result = verify_shell_integration()
            
        assert result['success'] is False
        assert 'Could not detect shell' in result['error']
    
    def test_verify_shell_integration_error(self):
        """Test verification error handling."""
        with patch('llm_memory.detect_user_shell', side_effect=Exception("Test error")):
            result = verify_shell_integration()
            
        assert result['success'] is False
        assert 'Test error' in result['error']