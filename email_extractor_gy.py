import aiohttp
import asyncio
import threading
from bs4 import BeautifulSoup
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import csv
from urllib.parse import urljoin, urlparse
import os

# Asynchronous function to fetch emails from a single URL
async def fetch_emails(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', soup.get_text()))
                return soup, list(emails)
            else:
                return None, f"Error: HTTP status {response.status}"
    except Exception as e:
        return None, f"Error fetching {url}: {e}"

# Asynchronous function to crawl a site and extract emails
async def crawl_site(session, base_url, max_depth, visited):
    if base_url in visited or max_depth == 0:
        return []
    
    visited.add(base_url)
    soup, emails = await fetch_emails(session, base_url)
    
    if isinstance(emails, str):  # An error occurred
        return [(base_url, emails)]
    
    results = [(base_url, emails)]
    
    if soup is not None:
        for link in soup.find_all('a', href=True):
            next_url = urljoin(base_url, link['href'])
            if urlparse(next_url).netloc == urlparse(base_url).netloc:
                results.extend(await crawl_site(session, next_url, max_depth - 1, visited))
    
    return results

# Asynchronous function to handle multiple URLs
async def extract_emails_from_urls(urls, max_depth):
    results = []
    visited = set()
    
    async with aiohttp.ClientSession() as session:
        tasks = [crawl_site(session, url.strip(), max_depth, visited) for url in urls if url.strip()]
        sites_results = await asyncio.gather(*tasks)
        for site_result in sites_results:
            results.extend(site_result)
    
    return results

# Function to run the asynchronous email extraction in a separate thread
def start_extraction_thread():
    urls = url_input.get("1.0", "end-1c").splitlines()
    output_text.delete("1.0", tk.END)
    max_depth = int(depth_input.get())

    if not urls:
        messagebox.showwarning("Input Error", "Please enter at least one URL.")
        return

    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        global results
        results = loop.run_until_complete(extract_emails_from_urls(urls, max_depth))
        loop.close()

        for url, emails in results:
            output_text.insert(tk.END, f"URL: {url}\n")
            if isinstance(emails, list) and emails:
                output_text.insert(tk.END, "Emails found:\n")
                for email in emails:
                    output_text.insert(tk.END, f" - {email}\n")
            elif isinstance(emails, list) and not emails:
                output_text.insert(tk.END, "No emails found.\n")
            else:
                output_text.insert(tk.END, f"{emails}\n")
            output_text.insert(tk.END, "-" * 40 + "\n")

    threading.Thread(target=run_async).start()

# Function to save the extracted emails to a CSV file
def save_emails_to_csv():
    if not results:
        messagebox.showwarning("No Data", "No emails to save. Please run the extraction first.")
        return

    # Ask the user where to save the CSV file
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])

    if not file_path:
        return

    try:
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["URL", "Emails"])
            
            for url, emails in results:
                if isinstance(emails, list) and emails:
                    writer.writerow([url, ", ".join(emails)])
                elif isinstance(emails, str):
                    writer.writerow([url, emails])
                else:
                    writer.writerow([url, "No emails found"])

        messagebox.showinfo("Success", f"Emails saved successfully to {file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save emails to CSV: {e}")

# Creating the main window
window = tk.Tk()
window.title("Bulk URL Email Extractor")

# Creating and placing widgets
tk.Label(window, text="Enter URLs (one per line):").pack(pady=5)

url_input = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=50, height=10)
url_input.pack(pady=10)

tk.Label(window, text="Enter max crawl depth:").pack(pady=5)

depth_input = tk.Entry(window)
depth_input.pack(pady=5)
depth_input.insert(0, "2")  # Default depth value

extract_button = tk.Button(window, text="Extract Emails", command=start_extraction_thread)
extract_button.pack(pady=10)

save_button = tk.Button(window, text="Save to CSV", command=save_emails_to_csv)
save_button.pack(pady=10)

tk.Label(window, text="Extracted Emails:").pack(pady=5)

output_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=50, height=10)
output_text.pack(pady=10)

# Global variable to store the results
results = None

# Starting the GUI event loop
window.mainloop()
