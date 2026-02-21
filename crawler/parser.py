import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

def simhash(text):
    """
    A 64-bit SimHash implementation for content deduplication.
    This creates a fingerprint of the text where near-identical
    documents will have near-identical hashes.
    """
    words = re.findall(r'\w+', text.lower())
    if not words:
        return "0" * 16

    v = [0] * 64
    for word in set(words):
        # Create a 64-bit MD5 hash of the word
        h = int(hashlib.md5(word.encode('utf-8')).hexdigest()[:16], 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
            
    # Return as a 16-character hex string for easy SQLite storage
    return f"{fingerprint:016x}"

def hamming_distance(hash1, hash2):
    """Calculate the number of differing bits between two SimHashes."""
    try:
        x = int(hash1, 16) ^ int(hash2, 16)
        return bin(x).count('1')
    except (ValueError, TypeError):
        return 64

def parse_html(html, base_url):
    """
    Parses HTML content, removes boilerplate, and extracts semantic metadata.
    Returns: title, cleaned_text, canonical_url, list_of_links
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove massive boilerplate elements
        for element in soup(["script", "style", "nav", "footer", "aside", "header", "noscript", "iframe"]):
            element.decompose()
            
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
        
        # Determine Canonical URL (prevents indexing URL parameters/session IDs when not needed)
        canonical_tag = soup.find('link', rel='canonical')
        canonical_url = base_url
        if canonical_tag and canonical_tag.has_attr('href'):
            # Sometimes canonicals are relative
            canonical_url = urljoin(base_url, canonical_tag['href'].strip())
        
        # Extract main text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract and normalize links
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            # Skip empty links or anchor jumps on the same page
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
                
            full_url = urljoin(base_url, href)
            
            # We only index standard HTTP protocols
            if full_url.startswith(('http://', 'https://')):
                parsed = urlparse(full_url)
                # Strip fragments
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    # Don't strip queries here, they might be important for page resolution
                    clean_url += f"?{parsed.query}"
                links.add(clean_url)
                
        return title, text, canonical_url, list(links)
    except Exception as e:
        print(f"Parser error for {base_url}: {e}")
        return "", "", base_url, []
