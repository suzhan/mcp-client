"""
Internationalization API endpoints
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Body

from app.i18n import get_language, set_language, LANGUAGES

router = APIRouter(prefix="/i18n", tags=["i18n"])


@router.get("/languages")
async def get_available_languages() -> Dict[str, List[Dict[str, str]]]:
    """
    Get a list of available languages
    """
    languages = [
        {"code": code, "name": code.split("-")[0]} 
        for code in LANGUAGES.keys()
    ]
    
    return {
        "languages": languages,
        "current": get_language()
    }


@router.get("/current")
async def get_current_language() -> Dict[str, str]:
    """
    Get the current language
    """
    return {"language": get_language()}


@router.post("/set")
async def set_current_language(language: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Set the current language
    
    Args:
        language: A dictionary with a 'code' key containing the language code
        
    Returns:
        A dictionary with the result of the operation
    """
    lang_code = language.get("code")
    
    if not lang_code:
        raise HTTPException(status_code=400, detail="Missing language code")
    
    if lang_code not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang_code}")
    
    success = set_language(lang_code)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to set language: {lang_code}")
    
    return {
        "success": True,
        "language": lang_code
    } 