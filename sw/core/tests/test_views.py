from unittest.mock import ANY, Mock

import pytest
from django.test import RequestFactory

from sw.core.views import CollectionDetailView, CollectionFetchView, CollectionListView

from .factories import CollectionFactory

pytestmark = pytest.mark.django_db


class TestCollectionViews:
    def test_list(self, rf: RequestFactory):
        view = CollectionListView.as_view()
        request = rf.get("/fake-url/")

        response = view(request)
        assert response.status_code == 200

    def test_fetch(self, rf: RequestFactory, monkeypatch):
        def mockreturn(*args):
            return CollectionFactory()

        monkeypatch.setattr(CollectionFetchView, "fetch_new_collection", mockreturn)
        view = CollectionFetchView.as_view()

        request = rf.get("/fake-url/")

        response = view(request)
        assert response.status_code == 200

    def test_detail(self, rf: RequestFactory, monkeypatch):
        collection = CollectionFactory(nb_records=11)

        def mock_return(*args):
            page = args[1]
            nb_records = 10 if page == 1 else 2
            return {"headers": ["name"], "records": ["AAA"] * nb_records}

        monkeypatch.setattr(CollectionDetailView, "get_records", mock_return)
        view = CollectionDetailView.as_view()

        request = rf.get("/fake-url/")

        response = view(request, pk=collection.pk)
        assert response.status_code == 200

        # test pagination (we should assert the results are properly returned)
        view = CollectionDetailView.as_view()

        request = rf.get("/fake-url/?page=2")

        response = view(request, pk=collection.pk, page=2)
        assert response.status_code == 200

    def test_aggregate(self, rf: RequestFactory, monkeypatch):
        collection = CollectionFactory(nb_records=11)
        mock_return = Mock()
        mock_return.return_value = {"headers": ["name"], "records": ["AAA"]}

        monkeypatch.setattr(CollectionDetailView, "get_aggregated_records", mock_return)
        view = CollectionDetailView.as_view()

        request = rf.post("/fake-url/", data={"chk-name": "on", "chk-year": "on"})

        response = view(request, pk=collection.pk)
        assert response.status_code == 200
        mock_return.assert_called_once_with(ANY, ["name", "year"])
