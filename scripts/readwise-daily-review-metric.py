import os

import requests

# -- Config --
HTTP_URL = "https://readwise.io/api/v2/review/"
HTTP_AUTH_HEADER = {"Authorization": f"Token {os.environ['READWISE_READER_API_TOKEN']}"}

PROM_ENDPOINT = (
    f"{os.environ['VICTORIAMETRICS_HTTP_ENDPOINT']}/api/v1/import/prometheus"
)
PROM_HEADER = {"Content-Type": "text/plain"}


# -- Logic --
def get_review_status() -> int:
    print("Getting daily review status")

    response = requests.get(HTTP_URL, headers=HTTP_AUTH_HEADER)
    response.raise_for_status()

    payload = response.json()
    review_completed = payload["review_completed"]
    if not isinstance(review_completed, bool):
        raise Exception(f"Unexpected payload: {response.text}")

    return 1 if review_completed else 0


def push_metrics(status: int):
    metrics = f"""
# TYPE review_completed gauge
daily_review_completed{{source="readwise"}} {status}
""".strip()

    print("Pushing metric:\n", metrics)

    response = requests.post(PROM_ENDPOINT, data=metrics, headers=PROM_HEADER)
    response.raise_for_status()


# --- Main ---
if __name__ == "__main__":
    status = get_review_status()
    push_metrics(status)
