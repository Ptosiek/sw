from django.views.generic import DetailView, ListView, TemplateView

from .models import Collection
from .utils import FetchError, PeopleLoader, RecordLoader

PAGE_SIZE = 10


class CollectionListView(ListView):
    queryset = Collection.objects.filter(type=Collection.Type.PEOPLE)


class CollectionDetailView(DetailView):
    queryset = Collection.objects.filter(type=Collection.Type.PEOPLE)

    @staticmethod
    def get_records(instance, cursor):
        return RecordLoader.load(instance.file, cursor)

    @staticmethod
    def get_aggregated_records(instance, columns):
        return RecordLoader.load_aggregate(instance.file, columns)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            page = int(self.request.GET.get("page", 1))
        except ValueError:
            page = 1
        context.update(self.get_records(context["object"], (page - 1) * PAGE_SIZE))

        if page * PAGE_SIZE < context["object"].nb_records:
            context["next_page"] = page + 1

        if page > 1 and getattr(self.request, "is_htmx", False):
            self.template_name = "core/partials/collection_detail/new_records.html"
        return context

    def get_post_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            self.get_aggregated_records(context["object"], kwargs["columns"])
        )
        return context

    def post(self, request, *args, **kwargs):
        columns = [x.replace("chk-", "") for x in request.POST.keys()]

        if getattr(self.request, "is_htmx", False):
            self.template_name = "core/partials/collection_detail/records.html"

        if columns:
            self.object = self.get_object()
            context = self.get_post_context_data(object=self.object, columns=columns)
            return self.render_to_response(context)
        else:
            return self.get(request, *args, **kwargs)


# We wouldn't do this synchronously, it should be done within an async task (can use celery)
# User could easily get notified int the FE when the download/processing is complete using SSE/Websocket.
class CollectionFetchView(TemplateView):
    template_name = "core/partials/collection_list/new_record.html"

    @staticmethod
    def fetch_new_collection():
        return PeopleLoader.load_to_db()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["instance"] = self.fetch_new_collection()
        except FetchError:
            context["error"] = "Something wrong happened, try again later"
        return context
