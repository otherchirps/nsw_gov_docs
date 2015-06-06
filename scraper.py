#!/usr/bin/env python

import os
# morph.io requires this db filename, but scraperwiki doesn't nicely
# expose a way to alter this. So we'll fiddle our environment ourselves
# before our pipeline modules load.
os.environ['SCRAPERWIKI_DATABASE_NAME'] = 'sqlite:///data.sqlite'

import scrapekit
import scraperwiki

from collections import namedtuple
from datetime import datetime, date
from urlparse import urlparse, urljoin
from threading import RLock

import resource


scraper = scrapekit.Scraper("NSW Legislative Assembly Tabled Docs")
start_page = "http://www.parliament.nsw.gov.au/prod/la/latabdoc.nsf/V3Home"

SessionPage = namedtuple('SessionPage', ['url', 'sid', 'base_url'])


def get_base_url(url):
    parts = urlparse(url)
    # See RFC 1808 for this craziness on netloc vs path.
    if parts.netloc:
        return "{uri.scheme}://{uri.netloc}".format(uri=parts)
    else:
        domain = parts.path.split('/')[0]
        return "{uri.scheme}://{domain}".format(uri=parts, domain=domain)


def get_db_path(page):
    # The index page contains several hidden input fields.
    # When a search option is chosen, these hidden values are
    # normally strung together via javascript, to build a url
    # to perform an ajax fetch from.
    #
    # The main one we're interested in is "dbPath".
    return page.xpath('//input[@name="dbPath"]/@value')[0]


def get_xpath_value(obj, path, default=None):
    """ Utility function. For when we know there's only
    one value coming back from an xpath list.

    If nothing found, returns the given default.
    """
    result = default
    values = obj.xpath(path)
    if values:
        result = values[0]
    return result


def fix_publish_date(item):
    """ Fix original date strings.

    They're displayed as dd/mm/yyyy, which is
    useless for sorting. Here we'll convert to a
    date object.
    """
    published = item['date_tabled']
    if not isinstance(published, (datetime, date)):
        try:
            item['date_tabled'] = datetime.strptime(published, '%d/%m/%Y').date().isoformat()
        except ValueError, err:
            print("Failed to convert to date: '{}' [{}]. Continuing anyway.".format(published, str(err)))
    return item


# Make sure we've only got one writer at a time.
# SQLite may or may not have threading support turned on...
database_lock = RLock()


@scraper.task
def store_in_db(items):
    unique_keys = ['paper_id', 'session_id']
    for item in items:
        with database_lock:
            #scraperwiki.sql.save(
            #    unique_keys, item, table_name='data'
            #)
            print(str(item))
            usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print('Memory usage: %s (kb)' % usage_kb)
            print()


@scraper.task
def parliament_session_tabled_docs_page(target):
    """ The main event.

    After the paliamentary session has been selected, the list of all
    documents for that session are shown.

    What this response should have is a large table to trawl.
    """
    session_page = scraper.get(target.url).html()

    # We want all the table rows that have data elements (ie. skip the header row)
    row_selector = '//div[@class="houseTable"]//tr/td/..'

    for row in session_page.xpath(row_selector):
        doc_record = dict(
            paper_id=get_xpath_value(row,'td[1]/text()'),
            date_tabled=get_xpath_value(row, 'td[2]/text()'),
            title=get_xpath_value(row, 'td[3]/a/text()'),
            url=urljoin(
                target.base_url, get_xpath_value(row, 'td[3]/a/@href')
            ),
            type=get_xpath_value(row, 'td[4]/text()'),
            laid_by=get_xpath_value(row, 'td[5]/text()'),
            session_id=target.sid
        )
        yield fix_publish_date(doc_record)


@scraper.task
def main_index_page(url):
    """ Entry point of the spider.

    The first page we land on has a form, allowing you to select
    which 'session' of parliament you want the docs for.

    We want them all.

    So we need to walk each available session value, and yield
    a request for the url this form would've sent the user to.
    """
    page = scraper.get(url).html()
    db_path = get_db_path(page)
    base_url = get_base_url(url)

    selector = '//select[@name="jmpByPaperNumber"]/option/@value'
    print("dbPath={}".format(db_path))

    for session in page.xpath(selector):
        session_url = urljoin(
            base_url,
            "{}V3ListBySession?open&key={}".format(
                db_path, session
            )
        )

        yield SessionPage(
            url=session_url,
            sid=session,
            base_url=base_url
        )


def main():
    pipeline = main_index_page | parliament_session_tabled_docs_page > store_in_db
    pipeline.run(start_page)


if __name__ == "__main__":
    main()
