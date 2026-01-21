import arxiv
import re
from datetime import datetime
from langchain_core.tools import tool

@tool
def get_arxiv_papers(
    query: str,
    count: int = 100,
    year_from: int | None = None,
    year_to: int | None = None,
    author: str | None = None,
    category: str | None = None,
    sort_by: str = 'date',
    sort_order: str = 'desc',
) -> dict:
    """
    Searches Arxiv specifically within paper TITLES (equivalent to searchtype=title).
    
    Args:
        query: The phrase to find in the title (e.g., "mixture of expert").
        count: The number of papers to retrieve.
    """
    # Increase page_size to fetch more results per request (user-requested).
    # Note: arXiv API may enforce limits; use responsibly.
    client = arxiv.Client()

    # If explicit parameters are provided (from LLM/tool call), prefer them; otherwise parse from `query` text.
    desired_count = int(count)
    author_filter = author
    category_filter = category

    parsed_from_query = False
    base_phrase = None
    if year_from is None and year_to is None and author is None and category is None:
        parsed_from_query = True
        # Parse simple natural-language filters from the query string
        q_lower = query.lower()
        year_from = None
        year_to = None

        # last N years
        m = re.search(r'last\s+(\d{1,2})\s+years?', q_lower)
        if m:
            n = int(m.group(1))
            year_from = datetime.utcnow().year - n

        # from YYYY / since YYYY
        m = re.search(r'(?:from|since)\s+(\d{4})', q_lower)
        if m:
            year_from = int(m.group(1))

        # to YYYY / before YYYY / until YYYY
        m = re.search(r'(?:to|before|until)\s+(\d{4})', q_lower)
        if m:
            year_to = int(m.group(1))

        # author: Name
        m = re.search(r'author:\s*([^,;]+)', query, flags=re.IGNORECASE)
        if m:
            author_filter = m.group(1).strip()
        else:
            m2 = re.search(r'\bby\s+([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*)', query)
            if m2:
                author_filter = m2.group(1).strip()

        # category: code
        m = re.search(r'(?:category|cat)[:\s]+([a-zA-Z0-9\._-]+)', q_lower)
        if m:
            category_filter = m.group(1).strip()

        # top N / limit N
        m = re.search(r'(?:top|first|limit|show)\s+(\d{1,3})', q_lower)
        if m:
            desired_count = int(m.group(1))

        # Build a base search phrase: remove known filter phrases so title search is cleaner
        cleaned = query
        cleaned = re.sub(r'last\s+\d+\s+years?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:from|since)\s+\d{4}', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:to|before|until)\s+\d{4}', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'author:\s*[^,;]+', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'by\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*', '', cleaned)
        cleaned = re.sub(r'(?:category|cat)[:\s]+[a-zA-Z0-9\._-]+', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:top|first|limit|show)\s+\d{1,3}', '', cleaned, flags=re.IGNORECASE)

        base_phrase = cleaned.strip()
    else:
        # use the provided query text as base phrase
        base_phrase = query

    if base_phrase:
        formatted_query = f'ti:"{base_phrase}"'
    else:
        formatted_query = query

    # print(f"DEBUG: Using filters -> year_from={year_from}, year_to={year_to}, author={author_filter}, category={category_filter}, desired_count={desired_count} (parsed_from_query={parsed_from_query})")

    # Increase fetch size when filters are applied to have a larger pool for client-side filtering
    fetch_count = max(desired_count, 200) if (year_from or year_to or author_filter or category_filter) else desired_count

    search = arxiv.Search(
        query=formatted_query,
        max_results=int(fetch_count),
        sort_by=arxiv.SortCriterion.SubmittedDate if sort_by == 'date' else arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending if sort_order == 'desc' else arxiv.SortOrder.Ascending
    )
   
    papers_dict = {}
    
    # 2. Fetch results
    # No need to filter with Python 'if' statements anymore; 
    # the API now only returns papers with the query in the title.
    # for r in client.results(search):
    #     print("-"*100)
    #     print(r,dir(r))
    #     papers_dict[r.entry_id] = {
    #         "title": r.title,
    #         "pdf_url": r.pdf_url,
    #         "date": r.published.isoformat()
    #     }
    result = [r for r in client.results(search)]
    # print(type(result), len(result), dir(result[0]))

    # Apply python-side filters (year, author, category) to the result list
    filtered = []
    for r in result:
        try:
            # year filter
            pub = getattr(r, 'published', None)
            if pub and year_from and pub.year < int(year_from):
                continue
            if pub and year_to and pub.year > int(year_to):
                continue

            # author filter
            if author_filter:
                authors = []
                if getattr(r, 'authors', None):
                    for a in r.authors:
                        if isinstance(a, str):
                            authors.append(a.lower())
                        else:
                            authors.append(getattr(a, 'name', str(a)).lower())
                if not any(author_filter.lower() in a for a in authors):
                    continue

            # category filter (check primary_category and categories)
            if category_filter:
                pc = (getattr(r, 'primary_category', '') or '').lower()
                cats = [c.lower() for c in (getattr(r, 'categories', []) or [])]
                if category_filter.lower() not in pc and category_filter.lower() not in cats:
                    continue

            filtered.append(r)
        except Exception:
            continue

    # Trim to desired_count
    result = filtered[:desired_count]

    # Convert arxiv.Result objects into JSON-serializable dicts
    papers_dict = {}
    for r in result:
        try:
            authors = []
            if getattr(r, 'authors', None):
                for a in r.authors:
                    # arxiv.Author has .name
                    if isinstance(a, str):
                        authors.append(a)
                    else:
                        authors.append(getattr(a, 'name', str(a)))

            papers_dict[getattr(r, 'entry_id', str(r))] = {
                "title": getattr(r, 'title', '') or '',
                "pdf_url": getattr(r, 'pdf_url', '') or '',
                "date": (getattr(r, 'published', None).isoformat() if getattr(r, 'published', None) else ''),
                "summary": getattr(r, 'summary', '') or '',
                "authors": authors,
                "primary_category": getattr(r, 'primary_category', '') or '',
                "categories": (list(getattr(r, 'categories', [])) if getattr(r, 'categories', None) else [])
            }
        except Exception as e:
            print('Error serializing result', e)

    return papers_dict
    
# get_arxiv_papers("Mixture-of-Experts",5)