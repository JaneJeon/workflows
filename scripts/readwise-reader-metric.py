import os
from datetime import datetime, timezone
from typing import Generator, List

import requests
from dlt.sources.helpers.rest_client import RESTClient
from dlt.sources.helpers.rest_client.paginators import JSONResponseCursorPaginator

# --- Config ---
HTTP_BASE_URL = "https://readwise.io/api/v3/"
HTTP_AUTH_HEADER = {"Authorization": f"Token {os.environ['READWISE_READER_API_TOKEN']}"}
HTTP_QUERY_PARAMS = {"location": "new", "category": "article"}

NEWS_SITES = ["Financial Times"]

PROM_ENDPOINT = (
    f"{os.environ['VICTORIAMETRICS_HTTP_ENDPOINT']}/api/v1/import/prometheus"
)
PROM_HEADER = {"Content-Type": "text/plain"}

client = RESTClient(
    base_url=HTTP_BASE_URL,
    headers=HTTP_AUTH_HEADER,
    paginator=JSONResponseCursorPaginator(
        cursor_path="nextPageCursor", cursor_param="pageCursor"
    ),
    data_selector="results",
)


# --- Logic ---
def financial_times_articles() -> Generator[dict, None, None]:
    """Yield all unread news articles from Readwise."""
    for page in client.paginate("list", params=HTTP_QUERY_PARAMS):
        yield from (item for item in page if item.get("site_name") in NEWS_SITES)


def compute_metrics(articles: list[dict]) -> tuple[int, float]:
    """Compute count and staleness (days behind) from articles."""
    count = len(articles)

    # Get the earliest published timestamp
    timestamps: List[int] = [
        article.get("published_date")
        for article in articles
        if isinstance(article.get("published_date"), int)
    ]

    if not timestamps:
        return count, 0.0

    earliest_ms = min(timestamps)
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    days_behind = max(0, (now_ms - earliest_ms) / (1000 * 60 * 60 * 24))

    return count, days_behind


def push_metrics(count: int, days_behind: float):
    metrics = f"""
# TYPE unread_news_articles_count gauge
unread_news_articles_count{{source="readwise_reader"}} {count}

# TYPE unread_news_articles_days_behind gauge
unread_news_articles_days_behind{{source="readwise_reader"}} {days_behind:.1f}
""".strip()

    response = requests.post(PROM_ENDPOINT, data=metrics, headers=PROM_HEADER)
    response.raise_for_status()
    print(metrics)
    print(f"✅ Published: {count} articles, {days_behind:.1f} days behind")


# --- Main ---
if __name__ == "__main__":
    articles = list(financial_times_articles())
    count, days_behind = compute_metrics(articles)
    push_metrics(count, days_behind)
