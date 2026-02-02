# nkrane/terminology_manager.py
import os
import pandas as pd
import re
import spacy
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import json

# Load spaCy model for English
try:
    nlp = spacy.load("en_core_web_sm")
    STOPWORDS = nlp.Defaults.stop_words
    SPACY_AVAILABLE = True
except:
    print("Warning: spaCy model not found. Please install: python -m spacy download en_core_web_sm")
    SPACY_AVAILABLE = False
    STOPWORDS = set()

@dataclass
class Term:
    id: int
    term: str
    translation: str
    domain: str = "general"
    language: str = "en"
    google_language_code: str = None

class TerminologyManager:
    def __init__(self, terminology_source: str = None):
        """
        Initialize terminology manager.
        
        Args:
            terminology_source: Path to terminology CSV file or directory containing CSV files.
                              If None, looks for terminologies_{lang}.csv in terminologies/ folder
                              inside the package directory.
        """
        self.terminology_source = terminology_source
        self.terms = {}  # Dictionary: term -> Term object
        self.language = None
        
        if terminology_source:
            self._load_terminology()
    
    def _load_terminology(self):
        """Load terminology from CSV file or directory."""
        if not self.terminology_source:
            return
        
        if os.path.isdir(self.terminology_source):
            # Load all CSV files in directory
            csv_files = [f for f in os.listdir(self.terminology_source) 
                        if f.endswith('.csv')]
            for csv_file in csv_files:
                self._load_single_file(os.path.join(self.terminology_source, csv_file))
        else:
            # Load single CSV file
            self._load_single_file(self.terminology_source)
    
    def _load_single_file(self, csv_path: str):
        """Load terminology from a single CSV file."""
        try:
            df = pd.read_csv(csv_path)
            
            # Extract language from filename if not specified in data
            basename = os.path.basename(csv_path)
            language = "en"  # default
            
            # Try to extract language code from filename
            lang_match = re.search(r'terminologies_([a-z]+)\.csv', basename, re.IGNORECASE)
            if lang_match:
                language = lang_match.group(1).lower()
            
            for _, row in df.iterrows():
                term_id = int(row.get('id', len(self.terms) + 1))
                term_text = str(row.get('term', '')).lower().strip()
                translation = str(row.get('translation', ''))
                domain = str(row.get('domain', 'general'))
                
                if term_text and translation:
                    term_obj = Term(
                        id=term_id,
                        term=term_text,
                        translation=translation,
                        domain=domain,
                        language=language,
                        google_language_code=None
                    )
                    self.terms[term_text] = term_obj
            
            self.language = language
            
        except Exception as e:
            print(f"Error loading terminology from {csv_path}: {e}")
    
    def _remove_stopwords(self, phrase: str) -> str:
        """Remove stopwords from a phrase."""
        if not SPACY_AVAILABLE:
            # Simple fallback: remove common English stopwords
            words = phrase.lower().split()
            filtered_words = [w for w in words if w not in STOPWORDS]
            return ' '.join(filtered_words)
        
        doc = nlp(phrase.lower())
        cleaned_tokens = [token.text for token in doc if token.text not in STOPWORDS]
        return ' '.join(cleaned_tokens).strip()
    
    def _extract_noun_phrases(self, text: str) -> List[Dict]:
        """Extract noun phrases from text using spaCy."""
        if not SPACY_AVAILABLE:
            # Fallback: simple word-based extraction
            words = re.findall(r'\b\w+\b', text.lower())
            return [{'text': word, 'start': text.lower().find(word), 
                     'end': text.lower().find(word) + len(word)} 
                    for word in words if word in self.terms]
        
        doc = nlp(text)
        noun_phrases = []
        
        # Extract noun chunks
        for chunk in doc.noun_chunks:
            noun_phrases.append({
                'text': chunk.text,
                'start': chunk.start_char,
                'end': chunk.end_char,
                'root': chunk.root.text
            })
        
        # Also extract standalone proper nouns
        covered_spans = set()
        for np in noun_phrases:
            for i in range(np['start'], np['end']):
                covered_spans.add(i)
        
        for token in doc:
            if token.pos_ in ["PROPN", "NOUN"] and token.idx not in covered_spans:
                noun_phrases.append({
                    'text': token.text,
                    'start': token.idx,
                    'end': token.idx + len(token.text),
                    'root': token.text
                })
        
        return noun_phrases
    
    def _find_matching_term(self, phrase: str) -> Optional[Term]:
        """Find a matching term in terminology for a phrase."""
        phrase_lower = phrase.lower().strip()
        
        # First try exact match
        if phrase_lower in self.terms:
            return self.terms[phrase_lower]
        
        # Try without stopwords
        cleaned_phrase = self._remove_stopwords(phrase_lower)
        if cleaned_phrase and cleaned_phrase in self.terms:
            return self.terms[cleaned_phrase]
        
        return None
    
    def preprocess_text(self, text: str) -> Tuple[str, Dict[str, Term], Dict[str, str]]:
        """
        Replace noun phrases in text with placeholders.
        Only replaces phrases that are found in terminology.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (preprocessed_text, placeholder_to_term, original_cases)
        """
        if not self.terms:
            return text, {}, {}
        
        # Extract noun phrases
        noun_phrases = self._extract_noun_phrases(text)
        
        # Filter to only phrases found in terminology
        matching_phrases = []
        for phrase in noun_phrases:
            if self._find_matching_term(phrase['text']):
                matching_phrases.append(phrase)
        
        # Sort by position (end to start) to avoid replacement issues
        matching_phrases.sort(key=lambda x: x['start'], reverse=True)
        
        preprocessed_text = text
        replacements = {}
        original_cases = {}
        
        for idx, phrase in enumerate(matching_phrases, 1):
            term_obj = self._find_matching_term(phrase['text'])
            if term_obj:
                placeholder = f"<{term_obj.id}>"
                
                # Replace in text
                preprocessed_text = (
                    preprocessed_text[:phrase['start']] + 
                    placeholder + 
                    preprocessed_text[phrase['end']:]
                )
                
                replacements[placeholder] = term_obj
                original_cases[placeholder] = phrase['text']
        
        return preprocessed_text, replacements, original_cases
    
    def postprocess_text(self, text: str, replacements: Dict[str, Term], 
                        original_cases: Dict[str, str]) -> str:
        """
        Replace placeholders with translations, preserving case.
        
        Args:
            text: Translated text with placeholders
            replacements: Mapping from placeholders to Term objects
            original_cases: Mapping from placeholders to original text for case matching
            
        Returns:
            Postprocessed text with actual translations
        """
        result = text
        
        for placeholder, term_obj in replacements.items():
            original_text = original_cases.get(placeholder, '')
            translation = term_obj.translation
            
            # Preserve original case pattern
            if original_text:
                if original_text.isupper():
                    translation = translation.upper()
                elif original_text.istitle():
                    translation = translation.capitalize()
                elif original_text[0].isupper():
                    translation = translation.capitalize()
            
            result = result.replace(placeholder, translation)
        
        return result
    
    def get_terms(self) -> Dict[str, Term]:
        """Get all terms in the terminology."""
        return self.terms
    
    def get_language(self) -> str:
        """Get the language of the terminology."""
        return self.language if self.language else "en"
