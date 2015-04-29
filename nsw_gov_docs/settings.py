# -*- coding: utf-8 -*-

# Scrapy settings for nsw_gov_docs project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'nsw_gov_docs'

SPIDER_MODULES = ['nsw_gov_docs.spiders']
NEWSPIDER_MODULE = 'nsw_gov_docs.spiders'

ITEM_PIPELINES = {
    'nsw_gov_docs.pipelines.LATabledDocFixPublishDate': 400,
    'nsw_gov_docs.pipelines.LATabledDocSaveToScraperWikiPipeline': 500,
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'nsw_gov_docs (+http://www.yourdomain.com)'
