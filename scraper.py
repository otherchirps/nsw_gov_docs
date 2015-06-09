#!/usr/bin/env python

from multiprocessing import Process

import os
import os.path

# morph.io requires this db filename, but scraperwiki doesn't nicely
# expose a way to alter this. So we'll fiddle our environment ourselves
# before our pipeline modules load.
os.environ['SCRAPERWIKI_DATABASE_NAME'] = 'sqlite:///data.sqlite'
session_index_filename = 'session_index'


def run_spider(spider_factory, **extra_settings):
    from twisted.internet import reactor
    from scrapy.crawler import Crawler
    from scrapy import log, signals
    from scrapy.utils.project import get_project_settings

    settings = get_project_settings()
    # Add the extra settings, so all our pipelines / middlewares, etc can access them.
    if extra_settings:
        settings.setdict(extra_settings)

    print("Scraper running...")
    spider = spider_factory()

    print("spawned spider...")
    crawler = Crawler(settings)
    crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()
    log.start(loglevel=log.DEBUG)
    reactor.run()


def session_index_scrape():
    from nsw_gov_docs.spiders.legislative_assembly_tabled_docs import (
        LegislativeAssemblySessionIndexSpider
    )
    run_spider(
        LegislativeAssemblySessionIndexSpider,
        session_index=session_index_filename
    )


def doc_page_scrape(session_id, start_url):
    from nsw_gov_docs.spiders.legislative_assembly_tabled_docs import (
        LegislativeAssemblyTabledDocsSpider
    )
    run_spider(
        LegislativeAssemblyTabledDocsSpider,
        session_id=session_id,
        session_start_url=start_url
    )


def main():
    # Cleanup if a previous run has leftovers...
    if os.path.exists(session_index_filename):
        os.remove(session_index_filename)

    # Spawn first scraper to fetch the list of pages to process...
    index_scraper = Process(
        target=session_index_scrape
    )
    index_scraper.start()
    index_scraper.join()

    if not os.path.exists(session_index_filename):
        raise IOError("File not found: {}".format(session_index_filename))

    # Spawn a scraper for each page found, and wait for it before moving
    # to the next.
    with open(session_index_filename, 'r') as src_file:
        for entry in src_file:
            session_id, session_page_url = entry.split('\t')
            page_scraper = Process(
                target=doc_page_scrape, args=[
                    session_id, session_page_url.strip()
                ]
            )
            page_scraper.start()
            page_scraper.join()

    os.remove(session_index_filename)

if __name__ == "__main__":
    main()
