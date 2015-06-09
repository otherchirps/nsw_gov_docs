# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime, date
import os.path
import scraperwiki

from nsw_gov_docs.items import (
    NswGovSessionUri,
    NswGovTabledDoc
)

from scrapy.exceptions import DropItem


class LATabledDocFixPublishDate(object):
    """ Fix original date strings.

    They're displayed as dd/mm/yyyy, which is
    useless for sorting. Here we'll convert to a
    date object.
    """
    def process_item(self, item, spider):

        if not isinstance(item, NswGovTabledDoc):
            return item

        published = item['date_tabled']
        if not isinstance(published, (datetime, date)):
            try:
                item['date_tabled'] = datetime.strptime(published, '%d/%m/%Y').date().isoformat()
            except ValueError, err:
                print("Failed to convert to date: '{}' [{}] . Continuing anyway.".format(published, str(err)))
        return item


class LATabledDocSaveToScraperWikiPipeline(object):
    def process_item(self, item, spider):

        if not isinstance(item, NswGovTabledDoc):
            return item

        unique_keys = ['paper_id', 'session_id']
        scraperwiki.sql.save(unique_keys, dict(item), table_name='data')

        return item


class LASessionIndexSaveUri(object):
    """ Append the session uri item to the session_index file.
    """
    def process_item(self, item, spider):

        if not isinstance(item, NswGovSessionUri):
            return item

        session_index_filename = spider.settings.get('session_index')
        if not session_index_filename:
            raise DropItem(
                "Missing session_index. Skipping: {}".format(item.session_uri)
            )

        with open(session_index_filename, 'a') as session_index:
            session_index.write(
                "{0[session_id]}\t{0[session_uri]}\n".format(item)
            )

        return item
