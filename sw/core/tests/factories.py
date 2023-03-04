from factory.django import DjangoModelFactory

from sw.core.models import Collection


class CollectionFactory(DjangoModelFactory):
    type = Collection.Type.PEOPLE

    class Meta:
        model = Collection
