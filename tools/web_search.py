
def search_web(query: str, max_results: int = 3) -> str:
    """
    Search the web using DuckDuckGo and return a summarized string of results.
    """
    import time
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "Web search is unavailable because its optional dependency is not installed."

    for attempt in range(2):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return "No results found."

            formatted_results = []
            for i, res in enumerate(results):
                title = res.get('title', 'No Title')
                body = res.get('body', 'No snippet')
                link = res.get('href', '')
                formatted_results.append(f"{i+1}. {title}\n{body}\nLink: {link}\n")

            return "\n".join(formatted_results)
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            return f"Error performing web search: {str(e)}"
