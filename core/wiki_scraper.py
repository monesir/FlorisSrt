"""
Wiki Scraper Module — جلب بيانات الشخصيات والقدرات والأماكن من مصادر خارجية
يدعم: Anilist, Fandom (Characters + Wiki Data), MAL
"""

import urllib.request
import urllib.parse
import json
import re
import time
import sys

HEADERS = {"User-Agent": "FlorisSrt/2.1 (localization-tool)"}


# ═══════════════════════════════════════════════════════════════
#  Anilist Scraper (GraphQL API — stdlib only)
# ═══════════════════════════════════════════════════════════════

class AnilistScraper:
    API_URL = "https://graphql.anilist.co"

    SEARCH_QUERY = """
    query ($search: String) {
      Page(perPage: 5) {
        media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
          id
          title { romaji english native }
          popularity
        }
      }
    }
    """

    CHARACTERS_QUERY = """
    query ($id: Int, $page: Int) {
      Media(id: $id, type: ANIME) {
        id
        title { romaji english native }
        characters(sort: ROLE, perPage: 25, page: $page) {
          pageInfo { total currentPage hasNextPage }
          nodes {
            id
            name { full native }
            gender
          }
        }
      }
    }
    """

    def __init__(self, on_progress=None, on_log=None):
        self.on_progress = on_progress or (lambda cur, total: None)
        self.on_log = on_log or (lambda msg: print(msg))

    def _post(self, body, retries=3):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=data,
            headers={**HEADERS, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    if result.get("errors"):
                        raise Exception(result["errors"][0].get("message", "Unknown AniList error"))
                    return result
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = int(e.headers.get("Retry-After", 60))
                    self.on_log(f"  ⚠️ Rate limited — waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                raise
        raise Exception("Max retries exceeded")

    def search(self, anime_name):
        """بحث عن أنمي بالاسم، يعيد قائمة النتائج"""
        result = self._post({"query": self.SEARCH_QUERY, "variables": {"search": anime_name}})
        return result.get("data", {}).get("Page", {}).get("media", [])

    def fetch_characters(self, anime_id):
        """جلب كل شخصيات الأنمي مع الجنس"""
        all_chars = []
        page = 1
        has_next = True

        while has_next:
            self.on_log(f"  Fetching page {page}...")
            result = self._post({
                "query": self.CHARACTERS_QUERY,
                "variables": {"id": anime_id, "page": page}
            })
            media = result.get("data", {}).get("Media")
            if not media:
                break

            nodes = media.get("characters", {}).get("nodes", [])
            all_chars.extend(nodes)
            has_next = media["characters"]["pageInfo"]["hasNextPage"]
            page += 1
            self.on_progress(len(all_chars), media["characters"]["pageInfo"]["total"])
            time.sleep(1.2)

        # Deduplicate
        seen = set()
        unique = []
        for c in all_chars:
            if c["id"] not in seen:
                seen.add(c["id"])
                unique.append(c)

        return unique

    def run(self, anime_name):
        """البحث + الجلب الكامل. يعيد (title, characters_list)"""
        self.on_log(f'🔍 Searching Anilist for: "{anime_name}"...')
        results = self.search(anime_name)
        if not results:
            self.on_log("❌ No anime found.")
            return None, []

        best = results[0]
        title = best.get("title", {}).get("english") or best["title"]["romaji"]
        self.on_log(f"✅ Found: {title} (ID: {best['id']})")

        chars = self.fetch_characters(best["id"])
        self.on_log(f"✅ {len(chars)} characters fetched.")

        output = []
        for c in chars:
            gender = c.get("gender") or "Unknown"
            if gender == "Male":
                g = "Male"
            elif gender == "Female":
                g = "Female"
            else:
                g = "Unknown"
            output.append({
                "name": c["name"]["full"],
                "gender": g,
                "type": "character",
                "source": "anilist"
            })
        return title, output


# ═══════════════════════════════════════════════════════════════
#  Fandom Character Scraper (MediaWiki API — stdlib only)
# ═══════════════════════════════════════════════════════════════

class FandomCharacterScraper:
    GENDER_CATEGORY_CANDIDATES = [
        ("Male", ["Category:Male characters", "Category:Male Characters",
                  "Category:Male_Characters", "Category:Male_characters",
                  "Category:Males", "Category:Male"]),
        ("Female", ["Category:Female characters", "Category:Female Characters",
                    "Category:Female_Characters", "Category:Female_characters",
                    "Category:Females", "Category:Female"]),
    ]
    MIN_GENDER_CAT_TOTAL = 20
    MAX_GENDER_CAT_MEMBERS = 8000

    INFOBOX_GENDER_RE = re.compile(
        r"\|\s*(?:gender|sex|جنس)\s*=\s*(male|female|ذكر|أنثى|m|f)\b", re.IGNORECASE)
    PRONOUN_FIELD_RE = re.compile(r"\|\s*pronoun\s*=\s*([^\n|}{]+)", re.IGNORECASE)
    MALE_PRONOUN_RE = re.compile(r"\b(he|his|him)\b", re.IGNORECASE)
    FEMALE_PRONOUN_RE = re.compile(r"\b(she|her|hers)\b", re.IGNORECASE)

    INFOBOX_MAP = {"male": "Male", "m": "Male", "ذكر": "Male",
                   "female": "Female", "f": "Female", "أنثى": "Female"}

    _SKIP_SUBCAT = re.compile(
        r"(categor|icon|stub|galler|image|audio|quote|list|navbox|template"
        r"|redirect|disambig|delete|cleanup|wikif|infobox|portal|help|talk"
        r"|maintenance|archive|manga|anime|novel|game|episode|chapter)", re.IGNORECASE)

    def __init__(self, on_progress=None, on_log=None):
        self.on_progress = on_progress or (lambda cur, total: None)
        self.on_log = on_log or (lambda msg: print(msg))

    def _api_get(self, api_url, params):
        url = api_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _category_exists(self, api_url, category):
        try:
            data = self._api_get(api_url, {
                "action": "query", "list": "categorymembers",
                "cmtitle": category, "cmlimit": "1", "cmtype": "page",
                "cmnamespace": "0", "format": "json"})
            return bool(data.get("query", {}).get("categorymembers"))
        except Exception:
            return False

    def _fetch_category_members(self, api_url, category, max_members=8000):
        members = []
        cm_continue = None
        while len(members) < max_members:
            params = {"action": "query", "list": "categorymembers",
                      "cmtitle": category, "cmlimit": "500", "cmtype": "page",
                      "cmnamespace": "0", "format": "json"}
            if cm_continue:
                params["cmcontinue"] = cm_continue
            try:
                data = self._api_get(api_url, params)
            except Exception:
                break
            for m in data.get("query", {}).get("categorymembers", []):
                members.append(m)
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                cm_continue = cont["cmcontinue"]
                time.sleep(0.3)
            else:
                break
        return members

    def _find_character_category(self, api_url):
        candidates = ["Category:Characters", "Category:Character",
                      "Category:Named Characters", "Category:Playable Characters",
                      "Category:Champions", "Category:People", "Category:Persons"]
        for cat in candidates:
            if self._category_exists(api_url, cat):
                return cat
        return "Category:Characters"

    def _fetch_pages_batch(self, api_url, titles):
        result = {}
        try:
            data = self._api_get(api_url, {
                "action": "query", "prop": "revisions",
                "titles": "|".join(titles), "rvprop": "content",
                "rvslots": "main", "format": "json"})
            for page in data.get("query", {}).get("pages", {}).values():
                title = page.get("title", "")
                revs = page.get("revisions", [])
                text = revs[0].get("slots", {}).get("main", {}).get("*", "") if revs else ""
                result[title] = text
        except Exception:
            pass
        return result

    def _detect_gender_from_text(self, text):
        m = self.INFOBOX_GENDER_RE.search(text)
        if m:
            return self.INFOBOX_MAP.get(m.group(1).lower(), "Unknown")
        pm = self.PRONOUN_FIELD_RE.search(text)
        if pm:
            val = pm.group(1).strip().lower()
            if re.search(r"\bshe\b|\bher\b", val):
                return "Female"
            if re.search(r"\bhe\b|\bhim\b", val):
                return "Male"
        male_count = len(self.MALE_PRONOUN_RE.findall(text))
        female_count = len(self.FEMALE_PRONOUN_RE.findall(text))
        if male_count == 0 and female_count == 0:
            return "Unknown"
        if male_count >= female_count * 1.5:
            return "Male"
        if female_count >= male_count * 1.5:
            return "Female"
        return "Unknown"

    def _try_category_method(self, api_url):
        characters = {}
        found_any = False
        for gender_label, candidates in self.GENDER_CATEGORY_CANDIDATES:
            resolved = next((c for c in candidates if self._category_exists(api_url, c)), None)
            if not resolved:
                continue
            self.on_log(f"  📂 [{gender_label}] from {resolved}...")
            members = self._fetch_category_members(api_url, resolved)
            self.on_log(f"     ✓ {len(members)} characters")
            for m in members:
                characters[m["title"]] = gender_label
            if members:
                found_any = True
            time.sleep(0.4)

        if found_any and len(characters) >= self.MIN_GENDER_CAT_TOTAL:
            return characters
        return None

    def _try_wikitext_method(self, api_url):
        cat = self._find_character_category(api_url)
        members = self._fetch_category_members(api_url, cat, max_members=700)
        if not members:
            return None

        self.on_log(f"  📖 Reading {len(members)} pages from {cat}...")
        characters = {}
        batch_size = 50
        total = len(members)

        for i in range(0, total, batch_size):
            batch = members[i:i + batch_size]
            titles = [m["title"] for m in batch]
            pages = self._fetch_pages_batch(api_url, titles)
            for name, text in pages.items():
                characters[name] = self._detect_gender_from_text(text)
            self.on_progress(min(i + batch_size, total), total)
            time.sleep(0.4)

        return characters

    def run(self, fandom_url):
        """جلب شخصيات الفاندوم مع الجنس"""
        api_url = fandom_url.rstrip("/") + "/api.php"
        self.on_log(f"🌐 Fandom: {fandom_url}")

        self.on_log("▶ Method 1: Gender categories...")
        result = self._try_category_method(api_url)
        if result:
            self.on_log(f"  ✅ Success! {len(result)} characters")
            return self._format(result)

        self.on_log("▶ Method 2: Wikitext page reading...")
        result = self._try_wikitext_method(api_url)
        if result:
            self.on_log(f"  ✅ Success! {len(result)} characters")
            return self._format(result)

        self.on_log("  ❌ No method succeeded.")
        return []

    # Fandom subpage suffixes that are NOT real characters
    _SUBPAGE_SUFFIXES = re.compile(
        r"/(Abilities|Gallery|Relationships|Trivia|Quotes|History|"
        r"Image Gallery|Personality|Synopsis|Plot|Appearance|"
        r"Equipment|Techniques|Stats|Voice|Misc|Navigation|"
        r"Skills|Powers|Biography|Storyline|Background|"
        r"Moveset|Strategy|Costumes|Outfits|Versions|"
        r"Part \w+|Chapter \d+|Episode \d+|Season \d+)$",
        re.IGNORECASE
    )

    def _is_subpage(self, title):
        """Check if a wiki page title is a subpage (contains /) that should be skipped."""
        if "/" not in title:
            return False
        return bool(self._SUBPAGE_SUFFIXES.search(title))

    def _format(self, chars_dict):
        filtered = {name: gender for name, gender in chars_dict.items()
                    if not self._is_subpage(name)}
        skipped = len(chars_dict) - len(filtered)
        if skipped:
            self.on_log(f"  🧹 Filtered out {skipped} subpages (e.g. /Abilities, /Gallery)")
        return [{"name": name, "gender": gender, "type": "character", "source": "fandom"}
                for name, gender in sorted(filtered.items())]


# ═══════════════════════════════════════════════════════════════
#  Fandom Wiki Data Scraper (Abilities / Locations / Lore)
# ═══════════════════════════════════════════════════════════════

class FandomWikiDataScraper:
    MAX_PAGES_PER_TYPE = 500
    MAX_CATS_PER_TYPE = 35
    MAX_CAT_FETCH = 8

    ABILITY_SUFFIX_RE = re.compile(
        r"\b(abilities|spells|skills|powers|magic|feats|arts|techniques"
        r"|jutsu|quirks|stands|sorceries|incantations|cantrips"
        r"|enchantments|weapons|armor|armour)s?\s*(\([^)]+\))?$", re.IGNORECASE)
    LOCATION_SUFFIX_RE = re.compile(
        r"\b(locations|places|areas|regions|zones|cities|towns|villages"
        r"|dungeons|realms|worlds|planes|countries|kingdoms|islands"
        r"|forests|mountains|caves|ruins|planets|castles|towers|temples)s?\s*(\([^)]+\))?$", re.IGNORECASE)
    LORE_SUFFIX_RE = re.compile(
        r"\b(lore|history|events|legends|myths|organizations|factions|religions"
        r"|cultures|wars|battles|artifacts|deities|clans|guilds|orders|societies)s?\s*(\([^)]+\))?$", re.IGNORECASE)
    SKIP_RE = re.compile(
        r"(icon|image|gallery|stub|template|redirect|disambig|delete|cleanup"
        r"|navbox|portal|help|talk|policy|maintenance|archive|audio|video"
        r"|episode|chapter|volume|season|soundtrack|music)", re.IGNORECASE)

    ABILITY_CATS = {"Abilities", "Ability", "Powers", "Spells", "Skills", "Techniques",
                    "Jutsu", "Quirks", "Weapons", "Armor", "Magic"}
    LOCATION_CATS = {"Locations", "Location", "Places", "Areas", "Regions",
                     "Cities", "Towns", "Villages", "Dungeons", "Realms", "Worlds"}
    LORE_CATS = {"Lore", "History", "Events", "Organizations", "Factions",
                 "Clans", "Guilds", "Species", "Races", "Artifacts", "Deities"}

    def __init__(self, on_progress=None, on_log=None):
        self.on_progress = on_progress or (lambda cur, total: None)
        self.on_log = on_log or (lambda msg: print(msg))

    def _api_get(self, api_url, params):
        url = api_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _fetch_all_category_names(self, api_url):
        all_cats = []
        ac_continue = None
        pages_fetched = 0
        while pages_fetched < self.MAX_CAT_FETCH:
            params = {"action": "query", "list": "allcategories",
                      "aclimit": "500", "format": "json"}
            if ac_continue:
                params["accontinue"] = ac_continue
            try:
                data = self._api_get(api_url, params)
            except Exception:
                break
            all_cats.extend(c["*"] for c in data.get("query", {}).get("allcategories", []))
            pages_fetched += 1
            cont = data.get("continue", {})
            if "accontinue" in cont:
                ac_continue = cont["accontinue"]
                time.sleep(0.2)
            else:
                break
        return all_cats

    def _fetch_category_pages(self, api_url, category, max_total=500):
        titles = []
        cm_continue = None
        while len(titles) < max_total:
            params = {"action": "query", "list": "categorymembers",
                      "cmtitle": category, "cmlimit": "500", "cmtype": "page",
                      "cmnamespace": "0", "format": "json"}
            if cm_continue:
                params["cmcontinue"] = cm_continue
            try:
                data = self._api_get(api_url, params)
            except Exception:
                break
            for m in data.get("query", {}).get("categorymembers", []):
                titles.append(m["title"])
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                cm_continue = cont["cmcontinue"]
                time.sleep(0.25)
            else:
                break
        return titles

    def _is_type(self, name, known_set, suffix_re):
        if name in known_set:
            return True
        if self.SKIP_RE.search(name):
            return False
        return bool(suffix_re.search(name))

    def run(self, fandom_url, fetch_abilities=True, fetch_locations=True, fetch_lore=True):
        """جلب القدرات / المواقع / اللور من فاندوم"""
        api_url = fandom_url.rstrip("/") + "/api.php"
        self.on_log(f"🌐 Fandom Wiki Data: {fandom_url}")
        self.on_log("🔍 Fetching category list...")

        all_cat_names = self._fetch_all_category_names(api_url)
        self.on_log(f"   {len(all_cat_names)} categories found")

        all_results = []
        type_configs = []
        if fetch_abilities:
            type_configs.append(("ability", self.ABILITY_CATS, self.ABILITY_SUFFIX_RE, "القدرات"))
        if fetch_locations:
            type_configs.append(("location", self.LOCATION_CATS, self.LOCATION_SUFFIX_RE, "المواقع"))
        if fetch_lore:
            type_configs.append(("lore", self.LORE_CATS, self.LORE_SUFFIX_RE, "اللور"))

        for type_key, known, suffix_re, label in type_configs:
            self.on_log(f"\n▶ [{label}]")
            cats = [f"Category:{n}" for n in all_cat_names if self._is_type(n, known, suffix_re)]
            if len(cats) > self.MAX_CATS_PER_TYPE:
                cats = cats[:self.MAX_CATS_PER_TYPE]
            if not cats:
                self.on_log(f"  ⚠️ No categories found for {label}")
                continue

            self.on_log(f"  📂 {len(cats)} matching categories")
            seen = set()
            for cat in cats:
                pages = self._fetch_category_pages(api_url, cat, max_total=self.MAX_PAGES_PER_TYPE - len(seen))
                new_pages = [t for t in pages if t not in seen]
                seen.update(new_pages)
                for t in new_pages:
                    all_results.append({"name": t, "gender": "-", "type": type_key, "source": "fandom"})
                time.sleep(0.15)

            self.on_log(f"  ✅ {len(seen)} unique entries")

        return all_results


# ═══════════════════════════════════════════════════════════════
#  MAL Scraper (Jikan API — uses urllib stdlib, no bs4 needed)
# ═══════════════════════════════════════════════════════════════

class MALScraper:
    JIKAN = "https://api.jikan.moe/v4"
    RX_GENDER = re.compile(r'\b(?:Gender|Sex)\s*[:\-]\s*(Male|Female)', re.I)
    RX_SHE = re.compile(r'\bshe\b', re.I)
    RX_HER = re.compile(r'\bher\b', re.I)
    RX_HE = re.compile(r'\bhe\b', re.I)
    RX_HIS = re.compile(r'\bhis\b', re.I)
    RX_WORD_F = re.compile(r'\b(female|woman|girl|lady|princess|queen|mother|daughter|sister|wife)\b', re.I)
    RX_WORD_M = re.compile(r'\b(male|man|boy|prince|king|father|son\b|brother|husband)\b', re.I)

    def __init__(self, on_progress=None, on_log=None):
        self.on_progress = on_progress or (lambda cur, total: None)
        self.on_log = on_log or (lambda msg: print(msg))

    def _api_get(self, path):
        url = f"{self.JIKAN}{path}"
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = int(e.headers.get("Retry-After", 4))
                    self.on_log(f"  ⏳ Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if e.code in (400, 404, 500, 503):
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                        continue
                    return {}
                raise
            except Exception:
                time.sleep(2 * (attempt + 1))
        return {}

    def _detect_gender(self, text):
        if not text or len(text) < 15:
            return "Unknown"
        m = self.RX_GENDER.search(text)
        if m:
            return m.group(1).capitalize()
        f_words = len(self.RX_WORD_F.findall(text))
        m_words = len(self.RX_WORD_M.findall(text))
        if f_words > 0 and m_words == 0:
            return "Female"
        if m_words > 0 and f_words == 0:
            return "Male"
        she = len(self.RX_SHE.findall(text)) * 3
        her = len(self.RX_HER.findall(text))
        he = len(self.RX_HE.findall(text)) * 2
        his = len(self.RX_HIS.findall(text))
        score_f = she + her
        score_m = he + his
        if score_f >= score_m * 0.75:
            return "Female"
        if score_m > score_f * 1.5:
            return "Male"
        return "Unknown"

    def run(self, anime_name, main_only=False):
        """بحث + جلب شخصيات من MAL"""
        self.on_log(f'🔍 Searching MAL for: "{anime_name}"...')
        encoded = urllib.parse.quote(anime_name)
        data = self._api_get(f"/anime?q={encoded}&limit=5&type=tv")
        results = data.get("data", [])
        if not results:
            data = self._api_get(f"/anime?q={encoded}&limit=5")
            results = data.get("data", [])
        if not results:
            self.on_log("❌ No anime found.")
            return None, []

        anime = results[0]
        anime_id = anime["mal_id"]
        title = anime.get("title_english") or anime.get("title", "")
        self.on_log(f"✅ Found: {title} (ID: {anime_id})")

        chars_data = self._api_get(f"/anime/{anime_id}/characters")
        chars = chars_data.get("data", [])
        if main_only:
            chars = [c for c in chars if c.get("role", "").lower() == "main"]
        self.on_log(f"📋 {len(chars)} characters found")

        output = []
        skipped = 0
        for i, entry in enumerate(chars):
            char = entry.get("character", {})
            char_id = char.get("mal_id")
            char_name = char.get("name", "Unknown")

            self.on_progress(i + 1, len(chars))
            self.on_log(f"  [{i+1}/{len(chars)}] {char_name}")

            gender = "Unknown"
            try:
                about_data = self._api_get(f"/characters/{char_id}")
                about = about_data.get("data", {}).get("about", "") or ""
                if about:
                    gender = self._detect_gender(about)
            except Exception as e:
                self.on_log(f"    ⚠️ Skipped (error: {e})")
                skipped += 1

            output.append({
                "name": char_name,
                "gender": gender,
                "type": "character",
                "source": "mal"
            })
            time.sleep(0.7)  # Jikan rate limit: ~3 req/s

        if skipped:
            self.on_log(f"⚠️ {skipped} characters had API errors (marked as Unknown)")
        self.on_log(f"✅ {len(output)} characters processed.")
        return title, output
