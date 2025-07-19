# Scraper

Scrapes a set website and saves data to a database, with email notification functionality.
Requires Python 3

## Installation

Install requirements per requirements.txt:
```bash
pip install -r requirements.txt
```
## Usage

Running the script script as-is will create a Python instance that will scrape every hour.
```python
python scraper.py
```
To trigger a scrape immediately, you can call the function directly:
```python
python -c "import scraper;  scraper.scraper()" 
```
