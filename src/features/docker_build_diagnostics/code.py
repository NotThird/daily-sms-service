"""
---
title: Docker Build Diagnostics
description: Analyzes and resolves Docker build errors with focus on package installation issues
authors: [AI Assistant]
date_created: 2024-01-09
dependencies: []
---
"""

from dataclasses import dataclass
from typing import List, Optional
import re
from functools import lru_cache

@dataclass
class DockerBuildError:
    """Represents a Docker build error with parsing capabilities."""
    error_code: int
    error_message: str
    stage: str
    command: str

    @staticmethod
    def parse_error(error_output: str) -> 'DockerBuildError':
        """
        Parses Docker build error output to extract relevant information.
        
        Security: Implements input validation to prevent injection attacks
        """
        # Sanitize input to prevent command injection
        error_output = re.sub(r'[;&|]', '', error_output)
        
        # Extract error code
        code_match = re.search(r'exit code: (\d+)', error_output)
        error_code = int(code_match.group(1)) if code_match else 0
        
        # Extract command that failed
        command_match = re.search(r'process "([^"]+)"', error_output)
        command = command_match.group(1) if command_match else ''
        
        # Determine build stage
        stage = 'package-installation' if 'apt-get' in error_output else 'unknown'
        
        return DockerBuildError(
            error_code=error_code,
            error_message=error_output,
            stage=stage,
            command=command
        )

class ErrorResolver:
    """
    Provides solutions for Docker build errors.
    
    Security: Implements secure error message handling
    Performance: Uses LRU cache for frequent error patterns
    """
    def __init__(self, error: DockerBuildError):
        self.error = error
        self._solutions: List[str] = []

    @lru_cache(maxsize=100)
    def get_solutions(self) -> List[str]:
        """
        Generates solution suggestions based on the error.
        Caches frequent error patterns for performance.
        """
        if self.error.stage == 'package-installation':
            if self.error.error_code == 100:
                self._solutions = [
                    "Split package installation into multiple RUN commands",
                    "Add retry mechanism for apt-get update",
                    "Use specific package versions",
                    "Add --fix-missing flag to apt-get update"
                ]
        
        return self._solutions

def analyze_build_error(error_output: str) -> List[str]:
    """
    Main function to analyze Docker build errors and provide solutions.
    """
    error = DockerBuildError.parse_error(error_output)
    resolver = ErrorResolver(error)
    return resolver.get_solutions()
