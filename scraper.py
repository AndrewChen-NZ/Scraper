import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import re
import sqlite3
import smtplib
from datetime import date, datetime
import time
import schedule

class Order:
    def __init__(self, name, number, date):
        self.name = name
        self.number = number
        self.date = date

def scraper():
    regex1 = "[A][C][N][ ][0-9][0-9][0-9][ ][0-9][0-9][0-9][ ][0-9][0-9][0-9]"
    regex2 = "[A][C][N][ ][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
    regex3 = "Stop [Ww]ork [Oo]rder for "
    dummyemail = "dummyemail@email.com"

    sqliteConnection = sqlite3.connect("stop_work_orders.db")
    cursor = sqliteConnection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stopworkorders (
            id INTEGER PRIMARY KEY NOT NULL,
            company_name TEXT NOT NULL,
            company_number TEXT,
            date TEXT NOT NULL
        )
    ''')
    sqliteConnection.commit()

    dates = []
    cursor.execute ("SELECT date FROM stopworkorders")
    fetcheddates = cursor.fetchall()
    for date in fetcheddates:
        dates.append(datetime.strptime(date[0], "%d %B %Y").date())
    if len(dates) > 0:
        mostrecentdate = max(dates)
    else:
        mostrecentdate = None

    URL = "https://www.nsw.gov.au/departments-and-agencies/building-commission/register-of-building-work-orders?category=Stop%2520work%2520orders"
    driver = Chrome()
    driver.implicitly_wait(2)
    driver.get(URL)

    searchresults = driver.find_element(By.CLASS_NAME, "nsw-search-results")
    buttonclass = searchresults.find_element(By.CLASS_NAME, "next")
    nextbutton = buttonclass.find_element(By.TAG_NAME, "span")
    lastresult = False

    orders = []

    while nextbutton.is_enabled and not lastresult:
        try: 
            buttonclass = searchresults.find_element(By.CLASS_NAME, "next")
            nextbutton = buttonclass.find_element(By.TAG_NAME, "span")
        except:
            lastresult = True
        else:
            #retrieve all orders
            stoporders = searchresults.find_elements(By.CLASS_NAME, "nsw-list-item__content")
            for stoporder in stoporders:
                acn = None
                #Date and Company Name can be extracted here
                stopdate = stoporder.find_element(By.CLASS_NAME, "nsw-list-item__info").text
                stopurl = stoporder.find_element(By.TAG_NAME, 'a')
                name = re.sub(regex3, "", stopurl.text)

                #Go through URL to retrieve ACN if possible
                stoplink = stopurl.get_attribute("href")
                page = requests.get(stoplink)
                soup = BeautifulSoup(page.content, "html.parser")
                divs = soup.find_all(class_="nsw-wysiwyg-content")
                regexsearch = re.search(regex1, divs[2].text)
                if regexsearch is not None:
                    acn = regexsearch.group()[4:7] + regexsearch.group()[8:11] + regexsearch.group()[12:15]
                regexsearch = re.search(regex2, divs[2].text)
                if regexsearch is not None:
                    acn = regexsearch.group()[4:13]

                # only add entries after the most recent entries in DB
                if mostrecentdate is None or mostrecentdate < datetime.strptime(stopdate, "%d %B %Y").date():
                    new_entry = Order(name, acn, stopdate)
                    orders.append(new_entry)
            #navigate to next
            if not "navigationDisabled" in buttonclass.get_dom_attribute("class"):
                ActionChains(driver).move_to_element(nextbutton).perform()
                nextbutton.click()
                searchresults = driver.find_element(By.CLASS_NAME, "nsw-search-results")
            else:
                lastresult = True

    for order in orders:
        cursor.execute("SELECT COUNT(id) FROM stopworkorders WHERE company_name = ?", (order.name,))
        if not (cursor.fetchone()[0] > 0):
            emailnumber = "N/A" if order.number is None else str(order.number)
            # Send an email 
            email = ("From: %s\r\nTo: %s\r\n\r\n" % (dummyemail, dummyemail))
            email += ('''New Stop Order:\r\n
            Company Name: %s\r\n
            Company Number: %s\r\n
            Date: %s\r\n
            ''' % (order.name, emailnumber, order.date))
            try:
                server = smtplib.SMTP('localhost', 8025)
                server.set_debuglevel(1)
                server.sendmail(dummyemail, dummyemail, email)
                server.quit()
            except:
                print("There was an issue with sending the email. ")
        cursor.execute("INSERT INTO stopworkorders(company_name, company_number, date) VALUES (?, ?, ?)", (order.name, order.number, order.date,))

    sqliteConnection.commit()

    cursor.close()
    sqliteConnection.close()

def main():
    schedule.every().hour.do(scraper)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()