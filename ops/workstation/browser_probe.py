"""Probe: can real Chrome (headed, on a virtual display) open the manufacturer pages?"""
from playwright.sync_api import sync_playwright

URLS = [
    "https://www.erco.com/en/",
    "https://www.deltalight.com/en",
    "https://www.zumtobel.com/com-en/",
    "https://www.flos.com/en/global/",
]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_page()
    for u in URLS:
        try:
            r = pg.goto(u, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(3000)
            print(u, "status", r.status if r else None, "| title:", pg.title()[:60])
        except Exception as e:
            print(u, "ERROR", str(e)[:120])
    b.close()
