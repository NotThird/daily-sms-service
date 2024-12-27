import pytest
from .code import DockerBuildError, ErrorResolver, analyze_build_error

def test_error_parsing():
    """Test parsing of Docker build error messages."""
    error_output = 'error: failed to solve: process "/bin/sh -c apt-get update" did not complete successfully: exit code: 100'
    error = DockerBuildError.parse_error(error_output)
    
    assert error.error_code == 100
    assert error.stage == 'package-installation'
    assert '/bin/sh -c apt-get update' in error.command

def test_error_resolver():
    """Test error resolution suggestions."""
    error = DockerBuildError(
        error_code=100,
        error_message='apt-get update failed',
        stage='package-installation',
        command='apt-get update'
    )
    resolver = ErrorResolver(error)
    solutions = resolver.get_solutions()
    
    assert len(solutions) > 0
    assert any('retry' in solution.lower() for solution in solutions)

def test_analyze_build_error():
    """Test the main analysis function."""
    error_output = 'error: failed to solve: process "/bin/sh -c apt-get update" did not complete successfully: exit code: 100'
    solutions = analyze_build_error(error_output)
    
    assert len(solutions) > 0
    assert isinstance(solutions, list)
    assert all(isinstance(solution, str) for solution in solutions)

def test_error_parsing_sanitization():
    """Test input sanitization for security."""
    malicious_input = 'error; rm -rf /; exit code: 100'
    error = DockerBuildError.parse_error(malicious_input)
    
    assert ';' not in error.error_message
    assert 'rm -rf' not in error.error_message

def test_error_resolver_caching():
    """Test LRU cache performance optimization."""
    error = DockerBuildError(
        error_code=100,
        error_message='apt-get update failed',
        stage='package-installation',
        command='apt-get update'
    )
    resolver = ErrorResolver(error)
    
    # First call should cache the result
    first_solutions = resolver.get_solutions()
    # Second call should use cached result
    second_solutions = resolver.get_solutions()
    
    assert first_solutions == second_solutions
    assert len(first_solutions) > 0

def test_unknown_error_handling():
    """Test handling of unknown error types."""
    error_output = 'error: failed to solve: process "unknown command" did not complete successfully: exit code: 1'
    error = DockerBuildError.parse_error(error_output)
    
    assert error.stage == 'unknown'
    assert error.error_code == 1
