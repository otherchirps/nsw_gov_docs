import tempfile
from scrapy.http.common import obsolete_setter
from scrapy.http.response.html import HtmlResponse


class HtmlBodyOnDemandResponse(HtmlResponse):
    """ Acts like a HtmlResponse, but does not store the body in memory.
    Will fetch contents from disk on demand.  At end of object's lifetime,
    the underlying file will be deleted.
    """
    def __init__(self, *args, **kwargs):
        self._body_file = None
        super(HtmlBodyOnDemandResponse, self).__init__(*args, **kwargs)

    def _get_body(self):
        if not self._body_file:
            return ''
        self._body_file.seek(0)
        return self._body_file.read()

    def _set_body(self, body):
        # Can safely lose the old reference. The old tempfile will
        # be deleted when the old reference is closed and/or garbage collected.
        self._body_file = tempfile.TemporaryFile()
        try:
            self._body_file.write(body)
        except:
            self._body_file.close()
            self._body_file = None

    body = property(_get_body, obsolete_setter(_set_body, 'body'))


class TabledDocPageDownloadMiddleware(object):
    """ Some of the pages we fetch are too big for the environment we run in.
    Used directly, we end up blowing our memory limit once we have

    1. the request in memory, and
    2. we run the lxml parser, in memory, over the entire document.

    This middleware saves the request to file, throws away the original
    request (which holds everything in memory), and
    """
    def process_response(self, request, response, spider):
        if spider.name != 'legislative_assembly_tabled_docs':
            return response

        if isinstance(response, HtmlBodyOnDemandResponse):
            return response

        replacement = HtmlBodyOnDemandResponse(
            url=response.url,
            status=response.status,
            headers=response.headers,
            body=response.body,
            request=response.request,
            flags=response.flags
        )
        return replacement
