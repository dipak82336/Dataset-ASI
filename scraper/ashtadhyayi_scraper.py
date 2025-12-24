# -*- coding: utf-8 -*-
"""
Ashtadhyayi.com Universal Book Scraper v3.0
===========================================
A comprehensive scraper for all books on ashtadhyayi.com

Supported Books:
- shivasutra (14 sutras)
- sutraani (3981 sutras) 
- dhatu (2000+ verbs)
- shabda (1000s nouns)
- pratyahara (44+ entries)
- ganapatha (450 groups)
- unadipatha (750 sutras)
- linganushasanam (200 rules)
- shiksha (60 shlokas)

Usage:
    python ashtadhyayi_scraper.py --book shivasutra
    python ashtadhyayi_scraper.py --book sutraani --limit 100
    python ashtadhyayi_scraper.py --book dhatu --output ./my_books

Author: Auto-generated
Date: 2025-12-24
"""

import os
import re
import sys
import time
import json
import argparse
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

# Try to import required packages
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("❌ Selenium not found. Please install: pip install selenium")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ BeautifulSoup not found. Please install: pip install beautifulsoup4")
    sys.exit(1)


# =====================================
# Data Classes
# =====================================

@dataclass
class EntryInfo:
    """Individual entry (sutra, dhatu, shabda, etc.)"""
    number: str
    title: str
    url: str
    content: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)  # For kaumudi, gana, etc.


@dataclass
class ChapterInfo:
    """Chapter/Section information"""
    number: str
    name: str
    url: str
    entries: List[EntryInfo] = field(default_factory=list)


@dataclass
class BookInfo:
    """Book information"""
    name: str
    sanskrit_name: str
    header_shlokas: List[str]
    footer_title: str
    base_url: str
    book_type: str  # shivasutra, sutraani, dhatu, etc.
    chapters: List[ChapterInfo] = field(default_factory=list)


# =====================================
# Book Configurations
# =====================================

BOOK_CONFIGS = {
    'shivasutra': {
        'url': 'https://ashtadhyayi.com/shivasutra/',
        'detail_url_pattern': '/shivasutra/{num}',
        'has_infinite_scroll': False,
        'organize_by': 'flat',  # All in one folder
        'expected_count': 14,
    },
    'sutraani': {
        'url': 'https://ashtadhyayi.com/sutraani',
        'detail_url_pattern': '/sutraani/{a}/{p}/{s}',
        'has_infinite_scroll': True,
        'organize_by': 'adhyaya_pada',  # Nested folders
        'expected_count': 3981,
    },
    'dhatu': {
        'url': 'https://ashtadhyayi.com/dhatu/',
        'detail_url_pattern': '/dhatu/{id}',
        'has_infinite_scroll': True,
        'organize_by': 'gana',  # Group by गण
        'expected_count': 2000,
    },
    'pratyahara': {
        'url': 'https://ashtadhyayi.com/pratyahara',
        'detail_url_pattern': None,  # Single page
        'has_infinite_scroll': False,
        'organize_by': 'flat',
        'expected_count': 44,
    },
    'ganapatha': {
        'url': 'https://ashtadhyayi.com/ganapath/',
        'detail_url_pattern': '/ganapath/{id}',
        'has_infinite_scroll': True,
        'organize_by': 'flat',
        'expected_count': 450,
    },
    'unadipatha': {
        'url': 'https://ashtadhyayi.com/unaadi/',
        'detail_url_pattern': '/unaadi/{id}',
        'has_infinite_scroll': True,
        'organize_by': 'flat',
        'expected_count': 750,
    },
    'linganushasanam': {
        'url': 'https://ashtadhyayi.com/linganushasanam',
        'detail_url_pattern': '/linganushasanam/{id}',
        'has_infinite_scroll': False,
        'organize_by': 'flat',
        'expected_count': 200,
    },
    'shiksha': {
        'url': 'https://ashtadhyayi.com/shiksha',
        'detail_url_pattern': '/shiksha/{id}',
        'has_infinite_scroll': False,
        'organize_by': 'flat',
        'expected_count': 60,
    },
}


# =====================================
# Main Scraper Class
# =====================================

class AshtadhyayiScraper:
    """
    Universal scraper for ashtadhyayi.com
    Handles all book types with automatic structure detection
    """
    
    BASE_URL = "https://ashtadhyayi.com"
    
    # Devanagari to English number mapping
    DEVA_TO_ENG = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', 
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
        # Gujarati numerals (sometimes appear)
        '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4',
        '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    }
    
    def __init__(self, output_dir: str = "books", headless: bool = True, 
                 delay: float = 1.5, limit: int = None, verbose: bool = True):
        """
        Initialize the scraper
        
        Args:
            output_dir: Directory to save markdown files
            headless: Run browser in headless mode
            delay: Delay between requests (seconds)
            limit: Maximum entries to scrape (None for all)
            verbose: Print progress messages
        """
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.limit = limit
        self.verbose = verbose
        self.driver = None
        self.headless = headless
        
    def log(self, message: str):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message)
        
    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        self.log("🔧 Initializing Chrome WebDriver...")
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=hi,sa,en")
        options.add_experimental_option('prefs', {
            'intl.accept_languages': 'hi,sa,en'
        })
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.log("✅ Chrome WebDriver initialized successfully")
        except Exception as e:
            self.log(f"❌ Failed to initialize Chrome: {e}")
            raise
    
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _wait_for_content(self, selector: str, timeout: int = 15) -> bool:
        """Wait for element to be present"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def _get_page_source(self, url: str, wait_selector: str = None) -> Optional[str]:
        """Navigate to URL and get page source after JavaScript renders"""
        try:
            self.log(f"   📥 Loading: {url}")
            self.driver.get(url)
            time.sleep(self.delay)
            
            if wait_selector:
                self._wait_for_content(wait_selector, timeout=15)
            else:
                self._wait_for_content("#list-group-content, .list-group-content, .list-group", timeout=15)
            
            return self.driver.page_source
        except Exception as e:
            self.log(f"   ❌ Error loading {url}: {e}")
            return None
    
    def _deva_to_english(self, text: str) -> str:
        """Convert Devanagari/Gujarati numbers to English"""
        return "".join(self.DEVA_TO_ENG.get(c, c) for c in str(text))
    
    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML content to well-formatted Markdown - keeps paragraphs together"""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # First pass: Mark paragraph boundaries with special markers
        PARA_BREAK = "\n\n【PARA】\n\n"
        LINE_BREAK = "\n"
        
        # Handle prakriya (derivation) boxes - convert to blockquotes
        for prakriya in soup.select('.prakriya, .derivation, .prakriya-box'):
            text = prakriya.get_text(strip=True)
            if text:
                new_tag = soup.new_string(f"{PARA_BREAK}> {text}{PARA_BREAK}")
                prakriya.replace_with(new_tag)
        
        # Handle section headers (major section titles)
        for header in soup.select('.section-header, h3, h4, h5'):
            text = header.get_text(strip=True)
            if text:
                new_tag = soup.new_string(f"{PARA_BREAK}### {text}{PARA_BREAK}")
                header.replace_with(new_tag)
        
        # Handle bold text inline
        for bold in soup.select('b, strong'):
            text = bold.get_text(strip=True)
            if text:
                bold.replace_with(f"**{text}**")
        
        # Handle font-weight-bold (often key terms)
        for bold in soup.select('.font-weight-bold, .bigtext-font'):
            text = bold.get_text(strip=True)
            if text:
                bold.replace_with(f"**{text}**")
        
        # Handle italic text inline
        for italic in soup.select('i, em'):
            text = italic.get_text(strip=True)
            if text:
                italic.replace_with(f"*{text}*")
        
        # Handle <br> as line breaks within paragraph
        for br in soup.select('br'):
            br.replace_with(LINE_BREAK)
        
        # Handle section separators as paragraph breaks
        for sep in soup.select('.section-separator, hr'):
            sep.replace_with(f"{PARA_BREAK}---{PARA_BREAK}")
        
        # Handle divs with significant margin as paragraph breaks
        for div in soup.select('div.mt-3, div.mt-4, div.mb-3, div.mb-4'):
            # Add paragraph break before and after
            text = div.get_text(strip=True)
            if text:
                div.replace_with(f"{PARA_BREAK}{text}{PARA_BREAK}")
        
        # Handle links - convert to inline
        for link in soup.select('a'):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text and href:
                link.replace_with(f"[{text}]({href})")
            elif text:
                link.replace_with(text)
        
        # Get text with single space separator (not newline!)
        # This keeps inline text together
        text = soup.get_text(separator=' ')
        
        # Clean up the text
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Process paragraph markers
        # Split by paragraph markers
        paragraphs = text.split('【PARA】')
        
        result_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Handle derivation arrows - format nicely
            if '→' in para and not para.startswith('>'):
                # Split derivation steps
                steps = para.split('→')
                if len(steps) > 1:
                    formatted_steps = []
                    for i, step in enumerate(steps):
                        step = step.strip()
                        if step:
                            if i == 0:
                                formatted_steps.append(step)
                            else:
                                formatted_steps.append(f"→ {step}")
                    para = "\n\n".join(formatted_steps)
            
            result_paragraphs.append(para)
        
        # Join paragraphs with double newlines
        text = '\n\n'.join(result_paragraphs)
        
        # Final cleanup
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\*\*\s*\*\*', '', text)  # Remove empty bolds
        text = re.sub(r'\s+([।॥,;:.])', r'\1', text)  # Fix punctuation spacing
        text = text.strip()
        
        return text
    
    def _scroll_to_load_all(self, max_scrolls: int = 500) -> int:
        """Scroll page to load all content (for infinite scroll pages)"""
        self.log("   📜 Loading all content (infinite scroll)...")
        
        last_count = 0
        scroll_count = 0
        no_change_count = 0
        
        while scroll_count < max_scrolls:
            # Get current count of items
            items = self.driver.find_elements(By.CSS_SELECTOR, "a[href].d-block, .list-group-item a[href]")
            current_count = len(items)
            
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 5:  # No new items after 5 scrolls
                    break
            else:
                no_change_count = 0
                last_count = current_count
            
            # Apply limit if set
            if self.limit and current_count >= self.limit:
                self.log(f"   ⏹️ Reached limit of {self.limit} entries")
                break
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            scroll_count += 1
            
            if scroll_count % 20 == 0:
                self.log(f"   📊 Loaded {current_count} entries...")
        
        self.log(f"   ✅ Total entries loaded: {last_count}")
        return last_count
    
    def _parse_main_page_header(self, soup: BeautifulSoup) -> Tuple[str, List[str], str]:
        """Parse header content (title, shlokas, footer)"""
        # Main title
        title_elem = soup.select_one(".list-group-title")
        main_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Header shlokas
        header_shlokas = []
        header_items = soup.select("#list-group-content > .bg-light.list-group-item, " +
                                   "#list-group-content > .list-group-item.bg-light, " +
                                   ".list-group-item.text-center.bg-light")
        for item in header_items:
            text = item.get_text(strip=True)
            if text and not item.select_one("a[href]"):
                header_shlokas.append(text)
        
        # Footer title
        footer_elem = soup.select_one(".list-group-end-title")
        footer_title = footer_elem.get_text(strip=True) if footer_elem else ""
        
        return main_title, header_shlokas, footer_title
    
    def _parse_entry_links(self, soup: BeautifulSoup, book_type: str) -> List[Dict[str, Any]]:
        """Parse entry links from main page based on book type"""
        results = []
        
        # Select all entry items
        if book_type == 'sutraani':
            items = soup.select("a.d-block[href^='/sutraani/'], a[href^='/sutraani/'].href")
        elif book_type == 'dhatu':
            items = soup.select("a[href^='/dhatu/']")
        else:
            items = soup.select("#list-group-content .list-group-item")
        
        for item in items:
            entry_data = self._parse_single_entry(item, book_type)
            if entry_data:
                results.append(entry_data)
                
                if self.limit and len(results) >= self.limit:
                    break
        
        return results
    
    def _parse_single_entry(self, item, book_type: str) -> Optional[Dict[str, Any]]:
        """Parse a single entry from the list"""
        # For sutraani
        if book_type == 'sutraani':
            if item.name == 'a' and item.get('href', '').startswith('/sutraani/'):
                href = item.get('href')
                
                # IMPORTANT: Filter out non-sutra links like /sutraani/z, /sutraani/skn, etc.
                # Valid sutra URLs have format: /sutraani/adhyaya/pada/sutra (4 parts)
                parts = href.strip('/').split('/')
                if len(parts) != 4:  # Must be sutraani/A/P/S
                    return None
                
                # Check if the last 3 parts are numbers
                try:
                    adhyaya, pada, sutra_num = parts[1], parts[2], parts[3]
                    int(adhyaya), int(pada), int(sutra_num)
                except ValueError:
                    return None  # Not a valid sutra URL
                
                # Get number from badge
                badge = item.select_one('.badge, .font-weight-bold')
                number = badge.get_text(strip=True) if badge else f"{adhyaya}.{pada}.{sutra_num}"
                
                # Get title from sutra-text
                title_elem = item.select_one('.sutra-text, .list-item-title, div:not(.badge):not(.float-right)')
                title = ""
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Get kaumudi reference from float-right
                kaumudi_elem = item.select_one('.float-right, .text-right, .text-dark')
                kaumudi = ""
                if kaumudi_elem:
                    text = kaumudi_elem.get_text(strip=True)
                    if 'कौमुदी' in text:
                        kaumudi = text
                
                # If title not found, try getting full text minus number and kaumudi
                if not title:
                    full_text = item.get_text(strip=True)
                    if number:
                        full_text = full_text.replace(number, '', 1)
                    if kaumudi:
                        full_text = full_text.replace(kaumudi, '', 1)
                    title = full_text.strip()
                
                # Get notes (siblings with bullet points)
                notes = []
                sibling = item.find_next_sibling()
                while sibling and sibling.name != 'a':
                    text = sibling.get_text(strip=True)
                    if text.startswith('•'):
                        notes.append(text)
                    sibling = sibling.find_next_sibling()
                
                return {
                    'number': number,
                    'title': title,
                    'url': self.BASE_URL + href,
                    'notes': notes,
                    'metadata': {'kaumudi': kaumudi} if kaumudi else {},
                    'adhyaya': adhyaya,
                    'pada': pada,
                    'sutra': sutra_num
                }
        
        # For simple books (shivasutra, etc.)
        else:
            # Skip bg-light items (header shlokas)
            if 'bg-light' in item.get('class', []):
                return None
            
            link = item.select_one("a[href]")
            if not link:
                return None
            
            href = link.get('href', '')
            if not href or href == '#':
                return None
            
            # Get number
            badge = item.select_one(".badge")
            number = badge.get_text(strip=True) if badge else ""
            
            # Get title
            title_elem = item.select_one(".list-item-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Build URL
            if href.startswith('/'):
                full_url = self.BASE_URL + href
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = self.BASE_URL + '/' + href
            
            # Get inline notes
            notes = []
            note_elems = item.select(".list-item-text, .text-primary")
            for note in note_elems:
                text = note.get_text(strip=True)
                if text:
                    notes.append(text)
            
            return {
                'number': number,
                'title': title,
                'url': full_url,
                'notes': notes,
                'metadata': {}
            }
    
    def _parse_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse individual entry detail page"""
        html = self._get_page_source(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get title from title-font or list-group-title
        title_elem = soup.select_one(".title-font, .list-group-title")
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Parse number from title (format: १.१.१ वृद्धिरादैच्)
        parts = title.split(" ", 1) if title else ["", ""]
        number = parts[0].strip()
        entry_title = parts[1].strip() if len(parts) > 1 else title
        
        # Get main content and sections
        sections = {}
        main_content = ""
        summary_content = ""
        
        # === EXTRACT SUMMARY SECTION (पदच्छेद, अनुवृत्ति, etc.) ===
        summary_region = soup.select_one("#sutra-summary-region")
        if summary_region:
            summary_items = []
            for item in summary_region.select(".list-group-item, .row"):
                label_elem = item.select_one(".col-3, .col-4, .text-muted, label")
                value_elem = item.select_one(".col-9, .col-8")
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).rstrip(':')
                    value = value_elem.get_text(strip=True)
                    if label and value:
                        summary_items.append(f"**{label}:** {value}")
                else:
                    # Single item
                    text = item.get_text(strip=True)
                    if text and len(text) < 200:
                        summary_items.append(text)
            
            if summary_items:
                summary_content = "\n\n".join(summary_items)
        
        # === EXTRACT MAIN MEANING (Short definition) ===
        short_meaning = ""
        short_elem = soup.select_one(".bigtext-font, .sutra-meaning-short")
        if short_elem:
            short_meaning = f"**{short_elem.get_text(strip=True)}**"
        
        # === EXTRACT MAIN EXPLANATION from sutrartha region ===
        sutrartha = soup.select_one("#sutra-commentary-sutrartha-region .sutra-commentary")
        if sutrartha:
            main_content = self._html_to_markdown(sutrartha.decode_contents())
        
        # Combine short meaning with main content
        if short_meaning and main_content:
            main_content = f"{short_meaning}\n\n{main_content}"
        elif short_meaning:
            main_content = short_meaning
        
        # Add summary to sections if available
        if summary_content:
            sections["सूत्र-विवरण (Summary)"] = summary_content
        
        # === GET ALL COMMENTARY SECTIONS ===
        commentary_regions = soup.select("[id^='sutra-commentary-'][id$='-region']")
        for region in commentary_regions:
            # Skip sutrartha (already captured as main content)
            if 'sutrartha' in region.get('id', ''):
                continue
            
            # Get section title
            title_elem = region.select_one(".list-item-title-color")
            section_name = title_elem.get_text(strip=True) if title_elem else ""
            if not section_name:
                continue
            
            # Get section content
            content_elem = region.select_one(".sutra-commentary")
            if content_elem:
                content_text = self._html_to_markdown(content_elem.decode_contents())
                if content_text.strip():
                    sections[section_name] = content_text
        
        # Fallback: If no sutrartha found, try getting from first list-group-item
        if not main_content:
            first_content = soup.select_one(".bigtext-font, .font-weight-bold")
            if first_content:
                main_content = first_content.get_text(strip=True)
        
        return {
            'number': number,
            'title': entry_title,
            'content': main_content,
            'sections': sections
        }
    
    def scrape_book(self, book_name: str) -> BookInfo:
        """
        Scrape a complete book
        
        Args:
            book_name: Name of book (shivasutra, sutraani, dhatu, etc.)
        
        Returns:
            BookInfo object with all scraped data
        """
        if book_name not in BOOK_CONFIGS:
            available = ", ".join(BOOK_CONFIGS.keys())
            raise ValueError(f"Unknown book: {book_name}. Available: {available}")
        
        config = BOOK_CONFIGS[book_name]
        self._init_driver()
        
        try:
            self.log(f"\n📚 Scraping book: {book_name}")
            self.log(f"   URL: {config['url']}")
            
            # Load main page
            html = self._get_page_source(config['url'])
            if not html:
                raise Exception("Failed to load main page")
            
            # Handle infinite scroll
            if config['has_infinite_scroll']:
                self._scroll_to_load_all()
                html = self.driver.page_source
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse header
            sanskrit_name, header_shlokas, footer_title = self._parse_main_page_header(soup)
            self.log(f"   📜 Title: {sanskrit_name}")
            self.log(f"   📝 Header shlokas: {len(header_shlokas)}")
            
            # Parse entry links
            entries_data = self._parse_entry_links(soup, book_name)
            self.log(f"   📋 Found {len(entries_data)} entries")
            
            # Create book object
            book = BookInfo(
                name=book_name,
                sanskrit_name=sanskrit_name,
                header_shlokas=header_shlokas,
                footer_title=footer_title,
                base_url=config['url'],
                book_type=book_name,
                chapters=[]
            )
            
            # Create chapter for entries
            chapter = ChapterInfo(
                number="1",
                name=book_name,
                url=config['url'],
                entries=[]
            )
            
            # Scrape each entry's detail page
            for i, data in enumerate(entries_data, 1):
                if self.limit and i > self.limit:
                    break
                
                self.log(f"\n   [{i}/{len(entries_data)}] {data.get('number', '')}. {data.get('title', '')[:30]}...")
                
                # Get detail page content
                detail = self._parse_detail_page(data['url'])
                
                entry = EntryInfo(
                    number=data.get('number', ''),
                    title=data.get('title', ''),
                    url=data['url'],
                    content=detail['content'] if detail else '',
                    sections=detail['sections'] if detail else {},
                    notes=data.get('notes', []),
                    metadata=data.get('metadata', {})
                )
                
                if not entry.number:
                    entry.number = detail['number'] if detail else str(i)
                if not entry.title:
                    entry.title = detail['title'] if detail else ''
                
                chapter.entries.append(entry)
                time.sleep(self.delay)
            
            book.chapters.append(chapter)
            self.log(f"\n✅ Successfully scraped {len(chapter.entries)} entries")
            
            return book
            
        finally:
            self._close_driver()
    
    def save_to_markdown(self, book: BookInfo, output_dir: str = None) -> Path:
        """Save book to markdown files"""
        output_path = Path(output_dir) if output_dir else self.output_dir
        book_dir = output_path / book.name
        book_dir.mkdir(parents=True, exist_ok=True)
        
        self.log(f"\n📁 Saving to: {book_dir}")
        
        config = BOOK_CONFIGS.get(book.book_type, {})
        organize_by = config.get('organize_by', 'flat')
        
        # Create README.md
        readme = self._create_readme(book)
        readme_path = book_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme)
        self.log(f"   ✅ Created: README.md")
        
        # Create entry files
        for chapter in book.chapters:
            for entry in chapter.entries:
                # Determine file path based on organization
                if organize_by == 'adhyaya_pada' and '.' in entry.number:
                    parts = self._deva_to_english(entry.number).split('.')
                    if len(parts) >= 3:
                        adhyaya_dir = book_dir / f"adhyaya_{parts[0]}"
                        pada_dir = adhyaya_dir / f"pada_{parts[1]}"
                        pada_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"sutra_{parts[2].zfill(3)}.md"
                        file_path = pada_dir / filename
                    else:
                        filename = self._get_entry_filename(entry)
                        file_path = book_dir / filename
                else:
                    filename = self._get_entry_filename(entry)
                    file_path = book_dir / filename
                
                # Create markdown content
                md_content = self._create_entry_markdown(entry, book)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                self.log(f"   ✅ Created: {file_path.relative_to(book_dir)}")
        
        self.log(f"\n🎉 All files saved to: {book_dir}")
        return book_dir
    
    def _get_entry_filename(self, entry: EntryInfo) -> str:
        """Generate filename for entry"""
        eng_num = self._deva_to_english(entry.number)
        
        # Handle dot-separated numbers
        if '.' in eng_num:
            parts = eng_num.split('.')
            eng_num = '_'.join(p.zfill(2) for p in parts)
        elif eng_num.isdigit():
            eng_num = eng_num.zfill(2)
        
        return f"entry_{eng_num}.md"
    
    def _create_readme(self, book: BookInfo) -> str:
        """Create README.md content"""
        readme = f"""<div align="center">

# {book.sanskrit_name if book.sanskrit_name else book.name.title()}

"""
        
        # Add header shlokas
        for shloka in book.header_shlokas:
            readme += f"*{shloka}*\n\n"
        
        readme += f"""---

📖 **स्रोतः (Source):** [{book.base_url}]({book.base_url})

</div>

---

## 📋 सूचि (Index)

| क्र. | नाम | विवरणम् |
|:---:|:-----|:--------|
"""
        
        config = BOOK_CONFIGS.get(book.book_type, {})
        organize_by = config.get('organize_by', 'flat')
        
        for chapter in book.chapters:
            for entry in chapter.entries:
                eng_num = self._deva_to_english(entry.number)
                
                # Generate correct file path based on organization
                if organize_by == 'adhyaya_pada' and hasattr(entry, 'metadata') and entry.metadata.get('adhyaya'):
                    adhyaya = entry.metadata.get('adhyaya', '1')
                    pada = entry.metadata.get('pada', '1')
                    sutra = entry.metadata.get('sutra', '1')
                    filepath = f"adhyaya_{adhyaya}/pada_{pada}/sutra_{str(sutra).zfill(3)}.md"
                elif '.' in eng_num and organize_by == 'adhyaya_pada':
                    parts = eng_num.split('.')
                    if len(parts) >= 3:
                        filepath = f"adhyaya_{parts[0]}/pada_{parts[1]}/sutra_{parts[2].zfill(3)}.md"
                    else:
                        filepath = self._get_entry_filename(entry)
                else:
                    filepath = self._get_entry_filename(entry)
                
                # Add metadata if available
                extra = ""
                if entry.metadata.get('kaumudi'):
                    extra = f" ({entry.metadata['kaumudi']})"
                
                readme += f"| {entry.number} | **{entry.title}**{extra} | [{filepath}](./{filepath}) |\n"
        
        readme += f"""
---

<div align="center">

{f"*{book.footer_title}*" if book.footer_title else ""}

</div>
"""
        return readme
    
    def _create_entry_markdown(self, entry: EntryInfo, book: BookInfo) -> str:
        """Create markdown content for an entry"""
        md = f"""<div align="center">

# {entry.number}. {entry.title}

"""
        
        # Add metadata
        if entry.metadata.get('kaumudi'):
            md += f"**{entry.metadata['kaumudi']}**\n\n"
        
        md += f"""📖 **स्रोतः:** [{entry.url}]({entry.url})

</div>

---

## 📜 विवरणम् (Explanation)

{entry.content if entry.content else "*विवरणं अनुपलब्धम्*"}

"""
        
        # Add notes
        if entry.notes:
            md += """---

## 📝 टिप्पणी (Notes)

"""
            for note in entry.notes:
                md += f"- {note}\n"
            md += "\n"
        
        # Add sections
        for section_name, section_content in entry.sections.items():
            if section_content.strip() and not section_name.startswith("Additional_"):
                md += f"""---

## 📖 {section_name}

{section_content}

"""
        
        # Navigation footer
        md += f"""---

<div align="center">

[🏠 मुख्यपृष्ठम्](./README.md)

</div>
"""
        return md


# =====================================
# CLI Interface
# =====================================

def main():
    """Main entry point with CLI support"""
    parser = argparse.ArgumentParser(
        description="🕉️ Ashtadhyayi.com Universal Book Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ashtadhyayi_scraper.py --book shivasutra
  python ashtadhyayi_scraper.py --book sutraani --limit 100
  python ashtadhyayi_scraper.py --book dhatu --output ./my_books --delay 2.0
  
Available Books:
  shivasutra, sutraani, dhatu, pratyahara, ganapatha, 
  unadipatha, linganushasanam, shiksha
        """
    )
    
    parser.add_argument(
        '--book', '-b',
        required=True,
        choices=list(BOOK_CONFIGS.keys()),
        help="Book to scrape"
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./books',
        help="Output directory (default: ./books)"
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help="Maximum entries to scrape (for testing)"
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)"
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help="Show browser window (for debugging)"
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🕉️  Ashtadhyayi.com Universal Book Scraper v3.0")
    print("=" * 60)
    print(f"📚 Book: {args.book}")
    print(f"📁 Output: {args.output}")
    if args.limit:
        print(f"⏹️ Limit: {args.limit} entries")
    print("=" * 60)
    
    # Create scraper
    scraper = AshtadhyayiScraper(
        output_dir=args.output,
        headless=not args.no_headless,
        delay=args.delay,
        limit=args.limit,
        verbose=not args.quiet
    )
    
    try:
        # Scrape the book
        book = scraper.scrape_book(args.book)
        
        # Save to Markdown
        output_path = scraper.save_to_markdown(book, output_dir=args.output)
        
        print("\n" + "=" * 60)
        print(f"✅ SUCCESS! Files saved to: {output_path}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
