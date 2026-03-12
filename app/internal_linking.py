import logging
import re
from typing import Dict, List, Set, Any
from bs4 import BeautifulSoup
from app.config import PILAR_POSTS

logger = logging.getLogger(__name__)

EXCLUDED_TAGS = ['a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre', 'figure', 'figcaption']

def add_internal_links(
    html_content: str, 
    link_map_data: Dict[str, List[Dict[str, Any]]],
    current_post_categories: List[int] = None,
    max_links: int = 6
) -> str:
    """
    Analyzes HTML and inserts internal links based on a prioritized strategy,
    using a list of keywords (title + tags) for each link.
    """
    if not html_content or not link_map_data or not link_map_data.get('posts'):
        return html_content

    soup = BeautifulSoup(html_content, 'html.parser')
    links_inserted = 0
    used_urls: Set[str] = set()
    
    all_link_options = link_map_data['posts']

    # --- Prioritization Logic ---
    pilar_options = []
    category_options = []
    other_options = []

    current_cat_set = set(current_post_categories or [])

    for post_data in all_link_options:
        # Skip if the post has no keywords to match
        if not post_data.get('keywords'):
            continue

        is_pilar = post_data['link'] in PILAR_POSTS
        shares_category = current_cat_set and not current_cat_set.isdisjoint(post_data.get('categories', []))

        if is_pilar:
            pilar_options.append(post_data)
        elif shares_category:
            category_options.append(post_data)
        else:
            other_options.append(post_data)

    # Within each priority group, sort keywords by length, descending.
    # This ensures we try to match "Real Madrid Club de Fútbol" before "Real Madrid".
    for group in [pilar_options, category_options, other_options]:
        for post_data in group:
            post_data['keywords'].sort(key=len, reverse=True)

    prioritized_link_options = pilar_options + category_options + other_options

    text_nodes = soup.find_all(string=True)

    for node in text_nodes:
        if links_inserted >= max_links:
            break

        if any(node.find_parent(tag) for tag in EXCLUDED_TAGS):
            continue

        original_text = str(node)
        modified_in_node = False

        for link_option in prioritized_link_options:
            if modified_in_node or links_inserted >= max_links:
                break

            url = link_option['link']
            if url in used_urls:
                continue

            # Iterate through all keywords for this link option (title, tags)
            for keyword in link_option['keywords']:
                pattern = re.compile(r'\b(' + re.escape(keyword) + r')\b', re.IGNORECASE)
                
                if pattern.search(original_text):
                    link_tag_str = f'<a href="{url}">{keyword}</a>'
                    new_html = pattern.sub(link_tag_str, original_text, count=1)
                    
                    node.replace_with(BeautifulSoup(new_html, 'html.parser'))
                    
                    links_inserted += 1
                    used_urls.add(url)
                    modified_in_node = True # Mark that we modified this node
                    
                    priority = "PILAR" if link_option in pilar_options else "CATEGORY" if link_option in category_options else "OTHER"
                    logger.info(f"Inserted link for keyword: '{keyword}' (Priority: {priority})")
                    break # Stop searching keywords for this link_option

    return str(soup)
