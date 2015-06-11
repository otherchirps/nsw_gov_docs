# -*- coding: utf-8 -*-
import urlparse

import psutil
import scrapy
from scrapy.log import INFO, ERROR
from scrapy.utils.response import get_base_url
from scrapy.exceptions import CloseSpider, NotConfigured

from nsw_gov_docs.items import (
    NswGovSessionUri,
    NswGovTabledDoc
)
from nsw_gov_docs.settings import MEMUSAGE_LIMIT_MB


class BaseLegislativeAssemblySpider(scrapy.Spider):

    allowed_domains = ["parliament.nsw.gov.au"]

    def __init__(self, name=None, **kwargs):
        super(BaseLegislativeAssemblySpider, self).__init__(name, **kwargs)
        self.killed = False
        self._memory_limit = MEMUSAGE_LIMIT_MB * 1024
        self.current_process = psutil.Process()

    def _is_memusage_exceeded(self):
        """ Debugging. The Memusage extension should take case
        of this check for us.
        """
        rss_bytes_used, vms_bytes_used = self.current_process.memory_info()
        usage_kb = rss_bytes_used / 1024

        self.log(
            'Memory usage: %s (kb)' % usage_kb,
            level=INFO
        )

        if usage_kb > self._memory_limit:
            return True
        return False

    def get_xpath_value(self, item, query, default=None):
        result = default
        values = item.xpath(query).extract()
        if values:
            result = values[0]
        return result

    def closed(self, reason):
        """ Called when the spider_closed signal is raised

        See: http://doc.scrapy.org/en/latest/topics/signals.html#scrapy.signals.spider_closed
        """
        self.killed = True
        self.log("spider_closed signal received: {}".format(reason), level=ERROR)


class LegislativeAssemblySessionIndexSpider(BaseLegislativeAssemblySpider):
    name = "legislative_assembly_parliament_sessions"
    allowed_domains = ["parliament.nsw.gov.au"]
    start_urls = (
        'http://www.parliament.nsw.gov.au/prod/la/latabdoc.nsf/V3Home',
    )

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
        the url this form would've sent the user to.
        """
        selector = '//select[@name="jmpByPaperNumber"]/option/@value'
        db_path = self.get_dbPath(response)
        base_url = get_base_url(response)

        for session in response.xpath(selector).extract():
            session_uri = self.build_session_url(
                base_url, db_path, session
            )
            if self.killed:
                raise RuntimeError()

            yield NswGovSessionUri(
                session_id=session,
                session_uri=session_uri
            )


class LegislativeAssemblyTabledDocsSpider(BaseLegislativeAssemblySpider):
    name = "legislative_assembly_tabled_docs"

    def start_requests(self):
        start_url = self.settings.get('session_start_url', None)
        if start_url is None:
            raise NotConfigured("Missing session_start_url")

        return [self.make_requests_from_url(start_url)]

    def parse(self, response):
        """ The main event.

        After the paliamentary session has been selected, the list of all
        documents for that session are shown.

        What this response should have is a large table to trawl.
        """
        # We want all the table rows that have data elements (ie. skip the header row)
        row_selector = '//div[@class="houseTable"]//tr/td/..'
        base_url = get_base_url(response)
        session_id = self.settings.get('session_id')

        for row in response.xpath(row_selector):
            if self.killed:
                raise RuntimeError()

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
            if self._is_memusage_exceeded():
                #self.killed = True
                raise CloseSpider("memory_exceeded")
