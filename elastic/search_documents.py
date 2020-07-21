from django.core.paginator import Paginator

from elastic.documents import ListPresenceTag


class SearchDocuments:
    def searchTag(self, term, size, offset=0, page=None):
        search = (
            ListPresenceTag.search()
            .query("query_string", query=term, fields=["name", "definition"])
            .extra(from_=0 if page else offset, size=1000 if page else size)
            .highlight("*")
        )

        response = search.execute().to_dict()

        # turn hits to result objects
        results_hits = []
        for h in response["hits"]["hits"]:
            results_hits_object = {
                "id": h["_source"]["tag_id"],
                "highlights": h["highlight"],
                "source": h["_source"],
            }
            results_hits.append(results_hits_object)

        # pagination
        if page is not None:
            results_hits = Paginator(results_hits, size).get_page(page)

        return {
            "hits": results_hits,
            "facets": [],
            "took": response["took"] / 1000,
            "total": search.count,
        }

    def getTagCount(self, term):
        search = ListPresenceTag.search().query(
            "query_string", query=term, fields=["name", "definition"]
        )
        return search.count
