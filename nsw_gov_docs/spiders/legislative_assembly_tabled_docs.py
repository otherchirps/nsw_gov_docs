# -*- coding: utf-8 -*-
import urlparse

import resource
import scrapy
from scrapy.utils.response import get_base_url


from nsw_gov_docs.items import NswGovTabledDoc


class LegislativeAssemblyTabledDocsSpider(scrapy.Spider):
    name = "legislative_assembly_tabled_docs"
    allowed_domains = ["parliament.nsw.gov.au"]
    start_urls = (
        'http://www.parliament.nsw.gov.au/prod/la/latabdoc.nsf/V3Home',
    )

    def get_xpath_value(self, item, query, default=None):
        result = default
        values = item.xpath(query).extract()
        if values:
            result = values[0]
        return result

    def get_dbPath(self, response):
        # The index page contains several hidden input fields.
        # When a search option is chosen, these hidden values are
        # normally strung together via javascript, to build a url
        # to perform an ajax fetch from.
        #
        # The main one we're interested in is "dbPath".
        return self.get_xpath_value(response, '//input[@name="dbPath"]/@value')

    def build_session_url(self, base_url, db_path, session_id):
        """ Generate the tabled docs url for the given parliamentary session.

        Normally this link is built via javascript, out of the session id,
        a hidden form value, and a sprinkle of hardcoding.
        """
        return urlparse.urljoin(
            base_url,
            "{}V3ListBySession?open&key={}".format(
                db_path, session_id
            )
        )

    def parse(self, response):
        """ Entry point of the spider.

        The first page we land on has a form, allowing you to select
        which 'session' of parliament you want the docs for.

        We want them all.

        So we need to walk each available session value, and yield
        a request for the url this form would've sent the user to.
        """
        selector = '//select[@name="jmpByPaperNumber"]/option/@value'
        db_path = self.get_dbPath(response)
        base_url = get_base_url(response)

        for session in response.xpath(selector).extract():
            session_url = self.build_session_url(
                base_url, db_path, session
            )
            request = scrapy.Request(session_url, callback=self.parse_tabled_docs_page)
            request.meta['session_id'] = session
            yield request

    def parse_tabled_docs_page(self, response):
        """ The main event.

        After the paliamentary session has been selected, the list of all
        documents for that session are shown.

        What this response should have is a large table to trawl.
        """
        # We want all the table rows that have data elements (ie. skip the header row)
        row_selector = '//div[@class="houseTable"]//tr/td/..'
        base_url = get_base_url(response)
        session_id = response.meta['session_id']

        for row in response.xpath(row_selector):
            yield NswGovTabledDoc(
                paper_id=self.get_xpath_value(row, 'td[1]/text()'),
                date_tabled=self.get_xpath_value(row, 'td[2]/text()'),
                title=self.get_xpath_value(row, 'td[3]/a/text()'),
                url=urlparse.urljoin(
                    base_url, self.get_xpath_value(row, 'td[3]/a/@href')
                ),
                type=self.get_xpath_value(row, 'td[4]/text()'),
                laid_by=self.get_xpath_value(row, 'td[5]/text()'),
                session_id=session_id
            )
            log.msg('Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, level=log.INFO)
