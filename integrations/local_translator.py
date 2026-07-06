import logging
import threading
import re

logger = logging.getLogger("local_translator")

_is_initialized = False

EN_AR_MAP = {
    'a': 'ا', 'b': 'ب', 'c': 'ك', 'd': 'د', 'e': 'ي', 'f': 'ف',
    'g': 'ج', 'h': 'ه', 'i': 'ي', 'j': 'ج', 'k': 'ك', 'l': 'ل',
    'm': 'م', 'n': 'ن', 'o': 'و', 'p': 'ب', 'q': 'ك', 'r': 'ر',
    's': 'س', 't': 'ت', 'u': 'و', 'v': 'ف', 'w': 'و', 'x': 'كس',
    'y': 'ي', 'z': 'ز'
}

def force_transliterate(word: str) -> str:
    word = word.lower()
    word = word.replace('tion', 'شن').replace('sh', 'ش').replace('ch', 'تش').replace('th', 'ث').replace('ph', 'ف')
    res = []
    for char in word:
        if char in EN_AR_MAP:
            res.append(EN_AR_MAP[char])
        else:
            res.append(char)
    return "".join(res)

def init_model():
    global _is_initialized
    if _is_initialized:
        return
        
    logger.info("Initializing offline transliteration engine...")
    # We no longer download/load argos-translate as per user request to use purely phonetic transliteration
    _is_initialized = True
    logger.info("Offline transliteration engine is ready.")

def start_background_init():
    """Starts the initialization in a background thread."""
    thread = threading.Thread(target=init_model, daemon=True)
    thread.start()

def auto_correct_english(text: str) -> str:
    """
    Finds English words in the text and transliterates them phonetically.
    """
    if not _is_initialized:
        logger.warning("Translator not initialized yet.")
        return text
        
    # Find English words
    english_words = set(re.findall(r'[a-zA-Z]+', text))
    
    # Sort by length descending to replace longer words first and avoid partial replacements
    english_words = sorted(list(english_words), key=len, reverse=True)
    
    corrected_text = text
    for word in english_words:
        translated = force_transliterate(word)
        corrected_text = corrected_text.replace(word, translated)
        logger.info(f"Auto-corrected: '{word}' -> '{translated}'")
                
    return corrected_text
