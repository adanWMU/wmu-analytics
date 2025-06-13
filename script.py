from collections import deque
import urllib.parse
import re
import csv
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

def is_same_domain(base_url, new_url):
    return urllib.parse.urlparse(base_url).netloc == urllib.parse.urlparse(new_url).netloc


def get_base_url(url: str) -> str:
    """
    Extracts the base URL (scheme and netloc) from a given URL.

    :param url: The full URL from which to extract the base.
    :return: The base URL in the form 'scheme://netloc'.
    """

    parts = urllib.parse.urlsplit(url)
    return '{0.scheme}://{0.netloc}'.format(parts)


def get_page_path(url: str) -> str:
    """
    Extracts the page path from the given URL, used to normalize relative links.

    :param url: The full URL from which to extract the page path.
    :return: The page path (URL up to the last '/').
    """

    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url


def extract_emails(response_text: str) -> set[str]:
    """
    Extracts all email addresses from the provided HTML text.

    :param response_text: The raw HTML content of a webpage.
    :return: A set of email addresses found within the content.
    """

    email_pattern = r'[a-z0-9\.\-+]+@[a-z0-9\.\-+]+\.[a-z]+'
    return set(re.findall(email_pattern, response_text, re.I))


def normalize_link(link: str, base_url: str, page_path: str) -> str:
    """
    Normalizes relative links into absolute URLs.

    :param link: The link to normalize (could be relative or absolute).
    :param base_url: The base URL for relative links starting with '/'.
    :param page_path: The page path for relative links not starting with '/'.
    :return: The normalized link as an absolute URL.
    """

    if link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return page_path + link
    return link


def scrape_website(start_url: str, max_count: int = 100) -> set[str]:
    """
    Scrapes a website starting from the given URL, follows links, and collects email addresses.

    :param start_url: The initial URL to start scraping.
    :param max_count: The maximum number of pages to scrape. Defaults to 100.
    :return: A set of email addresses found during the scraping process.
    """

    urls_to_process = deque([start_url])
    scraped_urls = set()
    collected_emails = set()
    count = 0

    while urls_to_process:
        count += 1
        if count > max_count:
            break

        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue

        scraped_urls.add(url)
        base_url = get_base_url(url)
        page_path = get_page_path(url)

        print(f'[{count}] Processing {url}')

        try:
            response = requests.get(url)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            print('There was a request error')
            continue

        collected_emails.update(extract_emails(response.text))

        soup = BeautifulSoup(response.text, 'lxml')

        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized_link = normalize_link(link, base_url, page_path)

            # Only follow links on the same domain
            if (
                normalized_link not in urls_to_process
                and normalized_link not in scraped_urls
                and is_same_domain(start_url, normalized_link)
            ):
                urls_to_process.append(normalized_link)

    return collected_emails


def send_emails(emails: set[str], sender_email: str, sender_password: str, subject: str, message: str) -> None:
    """
    Sends an email to a list of recipients using SMTP.

    :param emails: Set of email addresses to send to
    :param sender_email: The sender's email address
    :param sender_password: The sender's email password or app password
    :param subject: The email subject
    :param message: The email message content
    """
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['Subject'] = subject
    
    # Add message body
    msg.attach(MIMEText(message, 'plain'))
    
    # Connect to Gmail's SMTP server
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        
        # Send email to each recipient
        for email in emails:
            msg['To'] = email
            try:
                server.send_message(msg)
                print(f'[+] Email sent successfully to {email}')
            except Exception as e:
                print(f'[-] Failed to send email to {email}: {str(e)}')
        
        server.quit()
        print('\n[+] Email sending completed!')
    except Exception as e:
        print(f'[-] Error connecting to SMTP server: {str(e)}')


try:
    user_url = input('[+] Enter url to scan: ')
    emails = scrape_website(user_url)

    # Display collected emails
    if emails:
        print('\n[+] Found emails:')
        for email in emails:
            print(email)
            
        # Ask if user wants to send emails
        send_choice = input('\n[?] Would you like to send an email to these addresses? (yes/no): ').lower()
        if send_choice == 'yes':
            sender_email = input('[+] Enter your Gmail address: ')
            sender_password = input('[+] Enter your Gmail app password: ')  # Use app password for Gmail
            subject = input('[+] Enter email subject: ')
            message = input('[+] Enter email message: ')
            
            send_emails(emails, sender_email, sender_password, subject, message)
    else:
        print('[-] No emails found.')
except KeyboardInterrupt:
    print('[-] Closing!')


# Save emails to a CSV file
with open("collected_emails.csv", mode="w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Email"])  # Header
    for email in emails:
        writer.writerow([email])

print(f'\n[+] Emails saved to collected_emails.csv') 