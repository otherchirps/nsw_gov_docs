# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NswGovTabledDoc(scrapy.Item):
    paper_id = scrapy.Field()
    date_tabled = scrapy.Field()
    title = scrapy.Field()
    url = scrapy.Field()
    type = scrapy.Field()
    laid_by = scrapy.Field()
    session_id = scrapy.Field()

