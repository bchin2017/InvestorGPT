import os
import re
from firecrawl import FirecrawlApp
from dotenv import load_dotenv

load_dotenv()


def count_headings(markdown: str) -> int:
    return sum(1 for line in markdown.splitlines() if re.match(r"^#{1,6} ", line))


def count_links(markdown: str) -> int:
    return markdown.count("](")


def find_lines(text: str, keyword: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if keyword.lower() in line.lower() and line.strip()
    ]


def scrape_and_analyze(url: str, keyword: str) -> None:
    app = FirecrawlApp()

    print(f"\nScraping: {url}")
    try:
        result = app.scrape_url(url, formats=["markdown"])
    except Exception as e:
        print(f"Scraping failed: {e}")
        return

    markdown = (result.markdown or "").strip()
    if not markdown:
        print("No content returned. The page may be login-protected or blocked.")
        return

    # Stats
    print(f"\nCharacters collected : {len(markdown)}")
    print(f"Markdown headings    : {count_headings(markdown)}")
    print(f"Approximate links    : {count_links(markdown)}")

    # Keyword search
    matches = find_lines(markdown, keyword)
    print(f"\nLines mentioning '{keyword}' ({len(matches)} found):")
    for line in matches[:10]:
        print(" -", line)

    # Save output
    safe_name = re.sub(r"[^\w]", "_", url)[:60]
    output_file = f"firecrawl_{safe_name}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nSaved to {output_file}")


def main() -> None:
    print("=== Firecrawl Practice ===")
    url = input("\nURL to scrape: ").strip()
    keyword = input("Keyword to find: ").strip()

    if not url:
        print("No URL provided.")
        return

    scrape_and_analyze(url, keyword)


if __name__ == "__main__":
    main()
