# FlorisSrt v2.0.1: Extractor Enhancements & Fixes 🛠️

This patch brings important improvements and fixes to the Extractor Agent (Pre-Analyze) workflow introduced in v2.0.0.

## ✨ Enhancements
* **Arabic Source Language Support:** Greatly improved the logic when the source subtitle language is Arabic. The Extractor will now natively deduce the original Romaji/English names and terms while preserving the exact Arabic translation used in the text.
* **Bilingual Character Names:** The Extractor agent now suggests accurate Arabic translations (or transliterations) for Character Names automatically during the extraction phase.
* **Token Cost Tracking:** The UI now displays a highlighted summary of the **Total Tokens** consumed across all processed chunks and files at the end of the extraction process, making it much easier to track API costs.

## 🐛 Bug Fixes
* **Independent Provider Configurations:** Fixed a critical bug where changing the AI Provider in the Extractor tab (e.g., from OpenAI to Anthropic) would not load the correct models or API keys. The Extractor now has its own independent caching system for API Keys and Models per-provider.
* **Model Synchronization:** Added missing models (like `deepseek-v4-pro`) to the Extractor's dropdown list, ensuring it matches the Main Translation Agent's capabilities.
