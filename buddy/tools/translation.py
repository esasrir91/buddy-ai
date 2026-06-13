import json
from typing import Any, Dict, List, Optional
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class TranslationTools(Toolkit):
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        deepl_api_key: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_region: Optional[str] = None,
        **kwargs
    ):
        """Initialize Translation Tools.

        Args:
            google_api_key (Optional[str]): Google Translate API key
            deepl_api_key (Optional[str]): DeepL API key
            azure_api_key (Optional[str]): Azure Translator API key
            azure_region (Optional[str]): Azure region
        """
        self.google_api_key = google_api_key or getenv("GOOGLE_TRANSLATE_API_KEY")
        self.deepl_api_key = deepl_api_key or getenv("DEEPL_API_KEY")
        self.azure_api_key = azure_api_key or getenv("AZURE_TRANSLATOR_KEY")
        self.azure_region = azure_region or getenv("AZURE_TRANSLATOR_REGION")
        
        tools: List[Any] = [
            self.translate_text,
            self.detect_language,
            self.get_supported_languages,
            self.translate_bulk,
        ]

        super().__init__(name="translation", tools=tools, **kwargs)

    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        provider: str = "google"
    ) -> str:
        """Translate text using specified provider.

        Args:
            text (str): Text to translate
            target_language (str): Target language code (e.g., 'es', 'fr')
            source_language (Optional[str]): Source language code (auto-detect if None)
            provider (str): Translation provider ('google', 'deepl', 'azure')

        Returns:
            str: Translation result or error message
        """
        try:
            if provider == "google":
                return self._translate_google(text, target_language, source_language)
            elif provider == "deepl":
                return self._translate_deepl(text, target_language, source_language)
            elif provider == "azure":
                return self._translate_azure(text, target_language, source_language)
            else:
                return json.dumps({"error": "Unsupported provider"})
        except Exception as e:
            return json.dumps({"error": f"Translation failed: {str(e)}"})

    def _translate_google(self, text: str, target_language: str, source_language: Optional[str]) -> str:
        """Translate using Google Translate API."""
        if not self.google_api_key:
            return json.dumps({"error": "Google API key not provided"})

        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            
            data = {
                "q": text,
                "target": target_language,
                "key": self.google_api_key
            }
            
            if source_language:
                data["source"] = source_language

            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            translation = result["data"]["translations"][0]
            
            return json.dumps({
                "translated_text": translation["translatedText"],
                "detected_source_language": translation.get("detectedSourceLanguage"),
                "target_language": target_language,
                "provider": "google",
                "confidence": 1.0  # Google doesn't provide confidence scores
            })
        except Exception as e:
            return json.dumps({"error": f"Google Translate failed: {str(e)}"})

    def _translate_deepl(self, text: str, target_language: str, source_language: Optional[str]) -> str:
        """Translate using DeepL API."""
        if not self.deepl_api_key:
            return json.dumps({"error": "DeepL API key not provided"})

        try:
            url = "https://api-free.deepl.com/v2/translate"
            
            data = {
                "text": text,
                "target_lang": target_language.upper(),
                "auth_key": self.deepl_api_key
            }
            
            if source_language:
                data["source_lang"] = source_language.upper()

            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            translation = result["translations"][0]
            
            return json.dumps({
                "translated_text": translation["text"],
                "detected_source_language": translation["detected_source_language"],
                "target_language": target_language,
                "provider": "deepl",
                "confidence": 1.0
            })
        except Exception as e:
            return json.dumps({"error": f"DeepL translation failed: {str(e)}"})

    def _translate_azure(self, text: str, target_language: str, source_language: Optional[str]) -> str:
        """Translate using Azure Translator."""
        if not self.azure_api_key:
            return json.dumps({"error": "Azure API key not provided"})

        try:
            url = "https://api.cognitive.microsofttranslator.com/translate"
            
            params = {
                "api-version": "3.0",
                "to": target_language
            }
            
            if source_language:
                params["from"] = source_language

            headers = {
                "Ocp-Apim-Subscription-Key": self.azure_api_key,
                "Content-Type": "application/json"
            }
            
            if self.azure_region:
                headers["Ocp-Apim-Subscription-Region"] = self.azure_region

            body = [{"text": text}]

            response = requests.post(url, params=params, headers=headers, json=body)
            response.raise_for_status()
            
            result = response.json()
            translation = result[0]["translations"][0]
            
            return json.dumps({
                "translated_text": translation["text"],
                "detected_source_language": result[0].get("detectedLanguage", {}).get("language"),
                "target_language": target_language,
                "provider": "azure",
                "confidence": result[0].get("detectedLanguage", {}).get("score", 1.0)
            })
        except Exception as e:
            return json.dumps({"error": f"Azure Translator failed: {str(e)}"})

    def detect_language(self, text: str, provider: str = "google") -> str:
        """Detect the language of text.

        Args:
            text (str): Text to analyze
            provider (str): Provider to use for detection

        Returns:
            str: Language detection result or error message
        """
        try:
            if provider == "google":
                return self._detect_language_google(text)
            elif provider == "azure":
                return self._detect_language_azure(text)
            else:
                return json.dumps({"error": "Language detection not supported for this provider"})
        except Exception as e:
            return json.dumps({"error": f"Language detection failed: {str(e)}"})

    def _detect_language_google(self, text: str) -> str:
        """Detect language using Google Translate API."""
        if not self.google_api_key:
            return json.dumps({"error": "Google API key not provided"})

        try:
            url = "https://translation.googleapis.com/language/translate/v2/detect"
            
            data = {
                "q": text,
                "key": self.google_api_key
            }

            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            detection = result["data"]["detections"][0][0]
            
            return json.dumps({
                "detected_language": detection["language"],
                "confidence": detection["confidence"],
                "provider": "google"
            })
        except Exception as e:
            return json.dumps({"error": f"Google language detection failed: {str(e)}"})

    def _detect_language_azure(self, text: str) -> str:
        """Detect language using Azure Translator."""
        if not self.azure_api_key:
            return json.dumps({"error": "Azure API key not provided"})

        try:
            url = "https://api.cognitive.microsofttranslator.com/detect"
            
            params = {"api-version": "3.0"}
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.azure_api_key,
                "Content-Type": "application/json"
            }
            
            if self.azure_region:
                headers["Ocp-Apim-Subscription-Region"] = self.azure_region

            body = [{"text": text}]

            response = requests.post(url, params=params, headers=headers, json=body)
            response.raise_for_status()
            
            result = response.json()
            detection = result[0]
            
            return json.dumps({
                "detected_language": detection["language"],
                "confidence": detection["score"],
                "provider": "azure"
            })
        except Exception as e:
            return json.dumps({"error": f"Azure language detection failed: {str(e)}"})

    def get_supported_languages(self, provider: str = "google") -> str:
        """Get list of supported languages.

        Args:
            provider (str): Provider to get languages for

        Returns:
            str: Supported languages or error message
        """
        try:
            if provider == "google":
                return self._get_google_languages()
            elif provider == "azure":
                return self._get_azure_languages()
            elif provider == "deepl":
                return self._get_deepl_languages()
            else:
                return json.dumps({"error": "Unsupported provider"})
        except Exception as e:
            return json.dumps({"error": f"Failed to get supported languages: {str(e)}"})

    def _get_google_languages(self) -> str:
        """Get Google Translate supported languages."""
        if not self.google_api_key:
            return json.dumps({"error": "Google API key not provided"})

        try:
            url = "https://translation.googleapis.com/language/translate/v2/languages"
            params = {"key": self.google_api_key}

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            return json.dumps({
                "languages": result["data"]["languages"],
                "provider": "google"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get Google languages: {str(e)}"})

    def _get_azure_languages(self) -> str:
        """Get Azure Translator supported languages."""
        try:
            url = "https://api.cognitive.microsofttranslator.com/languages"
            params = {"api-version": "3.0"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            return json.dumps({
                "languages": result,
                "provider": "azure"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get Azure languages: {str(e)}"})

    def _get_deepl_languages(self) -> str:
        """Get DeepL supported languages."""
        # DeepL has a limited set of languages, return them statically
        languages = {
            "source": ["bg", "cs", "da", "de", "el", "en", "es", "et", "fi", "fr", "hu", "id", "it", "ja", "ko", "lt", "lv", "nb", "nl", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "tr", "uk", "zh"],
            "target": ["bg", "cs", "da", "de", "el", "en", "en-gb", "en-us", "es", "et", "fi", "fr", "hu", "id", "it", "ja", "ko", "lt", "lv", "nb", "nl", "pl", "pt", "pt-br", "pt-pt", "ro", "ru", "sk", "sl", "sv", "tr", "uk", "zh"]
        }
        
        return json.dumps({
            "languages": languages,
            "provider": "deepl"
        })

    def translate_bulk(self, texts: List[str], target_language: str, provider: str = "google") -> str:
        """Translate multiple texts.

        Args:
            texts (List[str]): List of texts to translate
            target_language (str): Target language code
            provider (str): Translation provider

        Returns:
            str: Bulk translation results or error message
        """
        try:
            results = []
            
            for text in texts:
                try:
                    translation_result = self.translate_text(text, target_language, provider=provider)
                    translation_data = json.loads(translation_result)
                    results.append({
                        "original_text": text,
                        "status": "success",
                        "translation": translation_data
                    })
                except Exception as e:
                    results.append({
                        "original_text": text,
                        "status": "error",
                        "error": str(e)
                    })
            
            return json.dumps({"results": results})
        except Exception as e:
            return json.dumps({"error": f"Bulk translation failed: {str(e)}"})