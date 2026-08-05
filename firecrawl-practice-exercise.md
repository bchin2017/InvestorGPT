# Beginner Firecrawl Exercise: Build a Documentation Summary

**Difficulty:** Beginner  
**Time:** 30-45 minutes  
**Estimated usage:** 1-3 Firecrawl credits  
**Goal:** Scrape a webpage, inspect its metadata, save the cleaned Markdown, and extract useful information.

## Learning objectives

By completing this exercise, you will learn how to:

- connect a Python program to Firecrawl;
- scrape a public webpage;
- work with cleaned Markdown;
- count headings and links;
- search scraped content for keywords; and
- keep an API key outside your source code.

## 1. Create a free account

1. Visit [Firecrawl](https://www.firecrawl.dev/).
2. Create a free account.
3. Open the dashboard and copy your API key.
4. Keep the key private. Do not place it directly in code that you publish.

The hosted free plan currently includes 1,000 credits per month. Check the [Firecrawl pricing page](https://www.firecrawl.dev/pricing) for current limits.

## 2. Prepare the project

Create a folder called `firecrawl-practice`, open PowerShell inside it, and install the Python SDK:

```powershell
pip install firecrawl-py
```

Temporarily store your API key in an environment variable:

```powershell
$env:FIRECRAWL_API_KEY="fc-your-api-key"
```

Replace `fc-your-api-key` with your actual key. This variable lasts for the current PowerShell session.

## 3. Create the program

Create a file named `practice.py` containing:

```python
from firecrawl import Firecrawl

TARGET_URL = "https://docs.firecrawl.dev/introduction"

app = Firecrawl()

result = app.scrape(
    TARGET_URL,
    formats=["markdown"],
)

markdown = result.markdown or ""

print("Page URL:", TARGET_URL)
print("Characters collected:", len(markdown))
print("\nFirst 500 characters:\n")
print(markdown[:500])

with open("firecrawl_page.md", "w", encoding="utf-8") as file:
    file.write(markdown)

print("\nSaved the cleaned content to firecrawl_page.md")
```

Run the program:

```powershell
python practice.py
```

Firecrawl should return clean Markdown and save it as `firecrawl_page.md`. The current SDK uses `Firecrawl().scrape(...)` for single-page scraping. See the [official Python quickstart](https://docs.firecrawl.dev/quickstarts/python).

## 4. Complete the tasks

### Task A: Inspect the result

Open `firecrawl_page.md` and answer these questions:

1. What is Firecrawl designed to do?
2. Which output format did the program request?
3. What information was removed or simplified compared with the original webpage?
4. Why might Markdown be more useful to an AI application than raw HTML?

### Task B: Count headings and links

Add this code before the file is saved:

```python
heading_count = sum(
    1
    for line in markdown.splitlines()
    if line.startswith("#")
)

link_count = markdown.count("](")

print("Markdown headings:", heading_count)
print("Approximate links:", link_count)
```

Run the program again and record the results.

### Task C: Find relevant lines

Add a function that searches the page for a keyword:

```python
def find_lines(text, keyword):
    matches = []

    for line in text.splitlines():
        if keyword.lower() in line.lower():
            matches.append(line.strip())

    return matches


matches = find_lines(markdown, "API")

print("\nLines mentioning API:")

for line in matches[:10]:
    print("-", line)
```

Try these keywords:

- `API`
- `scrape`
- `search`
- `Markdown`

Which keyword returns the most useful information?

## 5. Main challenge

Modify the program so the user can enter a URL and keyword:

```text
URL to scrape:
Keyword to find:
```

The completed program must:

1. scrape the supplied URL;
2. display the page's character count;
3. count headings and links;
4. print up to ten matching lines;
5. save the Markdown to a file; and
6. show a friendly message if scraping fails.

Do not test against private pages, login-protected pages, or websites that prohibit automated collection.

## Success checklist

- [ ] The API key is stored outside the Python file.
- [ ] Firecrawl returns cleaned Markdown.
- [ ] The Markdown is saved successfully.
- [ ] The program counts headings and links.
- [ ] Keyword searching works without case sensitivity.
- [ ] Errors are handled without crashing.
- [ ] The API key is not committed to GitHub.

## Optional extension

Scrape two public documentation pages and compare:

- their character counts;
- their numbers of headings;
- their approximate numbers of links; and
- the number of times a selected keyword appears.

Limit yourself to three pages so the exercise uses only a tiny portion of the free allowance.

## Reflection questions

1. How is Firecrawl different from downloading raw HTML?
2. When would a site-wide crawl be more useful than a single-page scrape?
3. What could make scraped information inaccurate or incomplete?
4. How would you prepare the resulting Markdown for an AI question-answering system?
