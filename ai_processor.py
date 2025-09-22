"""
AI Processor Module for Enterprise Integration
Provides access to AI processing functionality
"""

# Import from app.ai.processor for backward compatibility
from app.ai.processor import *

# Re-export all functionality
__all__ = ['AIProcessor', 'process_transaction', 'analyze_risk']
