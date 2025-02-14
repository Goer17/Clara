import sys, os
sys.path.append(os.path.abspath("."))

from pathlib import Path

import pytest

from agent.webcrawler import WebCrawler

@pytest.fixture
def crawler():
    crawler = WebCrawler()
    return crawler

@pytest.mark.parametrize("query", ["procrastinate"])
def test_crawler(crawler, query):
    results = crawler.fetch_image_text_pairs(query)
    with open(Path("unittests") / "output" / f"{query}.html", "w") as f:
        for result in results:
            url, description = result["url"], result["description"]
            f.write(f"<img src='{url}'>")
            f.write(f"<div>{description}</div>")
        