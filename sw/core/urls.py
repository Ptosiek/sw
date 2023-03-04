from django.urls import path

from .views import CollectionDetailView, CollectionFetchView, CollectionListView

urlpatterns = [
    path("collections/", CollectionListView.as_view(), name="collection-list"),
    path(
        "collections/<int:pk>/",
        CollectionDetailView.as_view(),
        name="collection-detail",
    ),
    path("collections/fetch/", CollectionFetchView.as_view(), name="collection-fetch"),
]
