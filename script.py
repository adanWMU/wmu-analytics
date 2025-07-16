from collections import deque
import urllib.parse
import re
import csv
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

def is_same_domain(base_url, new_url):
    return urllib.parse.urlparse(base_url).netloc == urllib.parse.urlparse(new_url).netloc

def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'

def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

def extract_emails(response_text: str) -> set[str]:
    email_pattern = r'[a-z0-9\.\-+]+@[a-z0-9\.\-+]+\.[a-z]+'
    return set(re.findall(email_pattern, response_text, re.I))

def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return page_path + link
    return link

def scrape_website(start_url: str, max_count: int = 100) -> set[str]:
    urls_to_process = deque([start_url])
    scraped_urls = set()
    collected_emails = set()
    count = 0

    while urls_to_process and count < max_count:
        count += 1
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue
        scraped_urls.add(url)

        print(f'[{count}] Processing {url}')
        try:
            response = requests.get(url)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            print('  ↳ request error, skipping')
            continue

        collected_emails |= extract_emails(response.text)
        soup = BeautifulSoup(response.text, 'lxml')
        base_url = get_base_url(url)
        page_path = get_page_path(url)

        for anchor in soup.find_all('a', href=True):
            link = normalize_link(anchor['href'], base_url, page_path)
            if link not in scraped_urls and link not in urls_to_process and is_same_domain(start_url, link):
                urls_to_process.append(link)

    return collected_emails

if __name__ == '__main__':
    try:
        start_url = input('[+] Enter URL to scan: ').strip()
        emails = scrape_website(start_url)

        if emails:
            print(f'\n[+] Found {len(emails)} unique email(s).')
            for e in sorted(emails):
                print('   -', e)
        else:
            print('\n[-] No emails found.')

    except KeyboardInterrupt:
        print('\n[-] Interrupted by user, exiting.')

    # Always save to CSV (overwrites existing file)
    with open("collected_emails.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Email"])
        for email in sorted(emails):
            writer.writerow([email])
    print('\n[+] Emails saved to collected_emails.csv')
