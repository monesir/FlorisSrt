# FlorisSrt v2.0.2: Regional Dialects & Extractor Precision 🚀

This update brings highly-requested linguistic modes to the translation pipeline and introduces surgical precision to the Pre-Analyze (Extractor) agent, along with an important settings bug fix.

## ✨ New Features
* **Regional Colloquial Modes:** Completely overhauled the "Colloquial (عامية)" translation style. You can now choose between three distinct dialect modes for ultra-natural dialogue localization:
  * **Colloquial - White (عامية بيضاء):** Smooth, neutral colloquial Arabic understandable by all.
  * **Colloquial - Egyptian (عامية مصرية):** Authentic Egyptian dialect for lively, natural localization.
  * **Colloquial - Saudi (عامية سعودية):** Everyday conversational Saudi dialect.
* **Granular Extractor Modes:** The Pre-Analyze agent now has dedicated extraction modes, allowing you to save tokens and avoid hallucinations by telling the agent exactly what to look for:
  * **Balanced:** Extracts both Characters and Glossary terms.
  * **Characters Only:** Focuses exclusively on names and skips world-building terms.
  * **Terms Only:** Focuses exclusively on lore/abilities/locations and skips character names.
* **Translate Result Toggle:** Added a new switch in the Pre-Analyze tab. You can now disable translation suggestions to extract names and terms purely in their original language (saving API costs and preventing unwanted Arabic translations).

## 🐛 Bug Fixes
* **Settings Tab Model Selection:** Fixed a persistent bug where selecting a model from the dropdown menu (e.g., Anthropic or DeepSeek) using the mouse would not save the model to the configuration correctly. Selecting models is now instantly and reliably saved.
