# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime, date
import scraperwiki

class LATabledDocFixPublishDate(object):
    """ Fix original date strings.

    They're displayed as dd/mm/yyyy, which is
    useless for sorting. Here we'll convert to a
    date object.
    """
    def process_item(self, item, spider):
        published = item['date_tabled']
        if not isinstance(published, (datetime, date)):
            try:
                item['date_tabled'] = datetime.strptime(published, '%d/%m/%Y').date().isoformat()
            except ValueError, err:
                print("Failed to convert to date: '{}' [{}] . Continuing anyway.".format(published, str(err)))
        return item

class LATabledDocSaveToScraperWikiPipeline(object):
    def process_item(self, item, spider):
        unique_keys = ['paper_id']
        scraperwiki.sql.save(unique_keys, dict(item), table_name='data')

        return item
