"""
Internationalization module for MCP client backend
"""
import os
import json
from typing import Dict, Any, Optional
from importlib import import_module

# Available languages
LANGUAGES = {
    "en-US": "en_US", 
    "zh-CN": "zh_CN"
}

# Default language
DEFAULT_LANGUAGE = "en-US"

# Current language (will be set during initialization)
_current_language = None
_messages = {}


def get_language() -> str:
    """Get the current language code"""
    return _current_language or DEFAULT_LANGUAGE


def set_language(lang_code: str) -> bool:
    """
    Set the current language
    
    Args:
        lang_code: Language code (e.g., 'en-US', 'zh-CN')
        
    Returns:
        bool: True if language was set successfully, False otherwise
    """
    global _current_language, _messages
    
    if lang_code not in LANGUAGES:
        return False
    
    try:
        # Import the language module
        module_name = f"app.i18n.{LANGUAGES[lang_code]}"
        lang_module = import_module(module_name)
        
        # Update current language and messages
        _current_language = lang_code
        _messages = lang_module.MESSAGES
        
        return True
    except (ImportError, AttributeError) as e:
        print(f"Error loading language {lang_code}: {str(e)}")
        
        # Fallback to default language
        if lang_code != DEFAULT_LANGUAGE:
            return set_language(DEFAULT_LANGUAGE)
        return False


def get_message(key: str, **kwargs) -> str:
    """
    Get a localized message by key with optional formatting
    
    Args:
        key: Message key in dot notation (e.g., 'errors.not_found')
        **kwargs: Format arguments for the message
        
    Returns:
        str: Localized message
    """
    if not _messages:
        # Initialize with default language if not yet initialized
        set_language(DEFAULT_LANGUAGE)
    
    # Split the key by dots to navigate the message dictionary
    parts = key.split('.')
    
    # Navigate through the message dictionary
    message_dict = _messages
    for part in parts:
        if part not in message_dict:
            # Key not found, return the key itself
            return key
        
        message_dict = message_dict[part]
    
    # If the final value is not a string, return the key
    if not isinstance(message_dict, str):
        return key
    
    # Format the message with provided arguments
    try:
        return message_dict.format(**kwargs)
    except KeyError:
        # Return the unformatted message if formatting fails
        return message_dict


# Initialize i18n with default language on module import
set_language(DEFAULT_LANGUAGE)


def load_language_from_config() -> None:
    """
    Load language setting from configuration file
    """
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 ".config", "app_config.json")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                lang = config.get('language', DEFAULT_LANGUAGE)
                set_language(lang)
    except Exception as e:
        print(f"Error loading language from config: {str(e)}")
        # Fall back to default language
        set_language(DEFAULT_LANGUAGE) 