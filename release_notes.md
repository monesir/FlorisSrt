# FlorisSrt v2.0.0: The Agentic Pipeline Update 🚀

This major release transforms FlorisSrt from a standard AI subtitle translator into an **Advanced Agentic Localization Pipeline**. We have introduced a pre-translation extraction workflow that analyzes your files, builds comprehensive glossaries, and passes rich context to the translation agent, ensuring unprecedented consistency and accuracy.

## 🌟 Key Features

### 1. 🕵️ Pre-Analyze Agent (Extractor)
A brand-new workflow tab has been added to extract vital information *before* translation begins:
* **Smart Extraction:** Automatically extracts characters and terminology (locations, abilities, jargon) directly from subtitle files using LLMs.
* **Tunable Chunking:** Control how many lines are sent to the extractor at once to optimize context length and token usage.
* **Manual Work Context:** Pass high-level story summaries directly to the extractor to improve extraction accuracy based on genre or plot.
* **Token Logging:** Real-time logging of token usage (Input, Output, Total) directly in the UI console to monitor AI costs.
* **Independent Connectivity:** A dedicated "Test Extractor Connection" button in the Settings tab ensures your Extractor API key is working perfectly.

### 2. 📝 Advanced Data Editor
The Data Editor has been completely overhauled to act as your central hub for project management:
* **Project Selector & Creator:** You can now create new projects or switch between existing ones directly from a dropdown in the Data Editor—no need to load a subtitle file first!
* **New 'Category' Column:** The Glossary table now natively supports the `Category` attribute (e.g., Location, Ability, Organization) pulled directly from the Extractor agent.
* **Safe Save Validation:** Prevents saving empty data and provides accurate feedback on exactly how many new items were merged into your project.
* **Smart Appending:** Saving extracted data intelligently appends to your existing project files without overwriting your manual edits.

### 3. 🧠 Enhanced Translation Agent
The main translation engine has been upgraded to take full advantage of the pre-analyzed data:
* **Category-Aware Translation:** The translation agent now receives the `Category` of glossary terms, giving it critical context (e.g., knowing a word is a "Location" rather than an "Ability") to ensure highly accurate, context-aware translations.
* **Work Context Injection:** The translator now respects global project descriptions, ensuring genre-appropriate vocabulary and tone.
* **Priority Handling:** Established a strict priority hierarchy where the Main Glossary consistently overrides Term Memory to prevent translation drift.

## 🐛 Bug Fixes & UI Polish
* **Fixed:** Resolved an issue where selecting a folder of subtitles visually appeared to only select the last file in the text box.
* **Fixed:** Removed the hardcoded tab-index lock that disabled the Data Editor on startup, allowing immediate project management.
* **Fixed:** Made tab-switching logic completely dynamic (checking by `currentWidget` instead of index) so users can freely reorder UI tabs without breaking the application logic.

## ⚙️ How to use the new workflow:
1. Go to **Pre-Analyze (Extraction)**, load your subtitles, and extract characters/terms.
2. Review and save them to your project.
3. Go to the **Data Editor** to refine Arabic names, genders, and terminology categories.
4. Go to **Run**, load your file, and start translating with agentic precision!
