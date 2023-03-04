import logging
from urllib.parse import urljoin

import petl as etl
from django.core.files.base import ContentFile
from django.utils import timezone
from petl.util.base import Table
from requests import Session
from requests.adapters import HTTPAdapter
from requests.exceptions import JSONDecodeError
from urllib3.util.retry import Retry

from .conf import SERVICE_BASE_UL
from .models import Collection

logger = logging.getLogger(__name__)


class FetchError(Exception):
    pass


class RetrySession:
    def __new__(
        cls,
        total_retry: int = 3,
        read: int = 3,
        connect: int = 3,
        backoff_factor: float = 0.3,
    ):
        session = Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=total_retry,
                read=read,
                connect=connect,
                backoff_factor=backoff_factor,
            )
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session


# Should be and abstract class: APILoader(metaclass=abc.ABCMeta),
class APILoader:
    url: str = None
    type: int = None

    def __init__(self):
        self.session = RetrySession()

    @staticmethod
    def fetch(url, session: Session = None) -> [list, str]:
        """
        fetch api, use session object if passed else it will instantiate a new one
        """
        if not session:
            session = RetrySession()
        r = session.get(url)
        if not r.ok:
            # API crashing and / or max retries reached
            # since we are in an HTTP request/response cycle, gently fail and ask the user to try again later.
            # In real life, this wouldn't be done synchronously but in a task.
            # In such event we would just reprogram the task automatically, easily don with celery
            # @app.task(autoretry_for=(ConnectionError,), max_retries=10, retry_backoff=True)
            raise FetchError(r.reason)
        try:
            data = r.json()
            return data["results"], data["next"]
        except (KeyError, JSONDecodeError) as e:
            # api has changed, do proper error handling
            logger.exception(f"API has changed format: {e}")
            raise FetchError

    @classmethod
    def load_from_api(cls) -> list[dict]:
        results = []
        session = RetrySession()
        url = urljoin(SERVICE_BASE_UL, cls.url)
        # we would benefit from using an async loop to parallelize downloads
        try:
            iteration = 0
            while url:
                data, url = cls.fetch(url, session)
                results.extend(data)
                iteration += 1
                # add a failsafe on iteration if there's an issue on 'next'
        except FetchError as e:
            logger.exception(f"API error: {e}")
            raise e
        return results

    @classmethod
    def transform_results(cls, results: list[dict]) -> Table:
        return etl.fromdicts(results)

    @classmethod
    def to_content_file(cls, table: Table) -> ContentFile:
        """
        Transform a table object to a ContenFile that can be used by django
        """
        sink = etl.MemorySource()
        table.tocsv(sink)
        sink.buffer.seek(0)
        return ContentFile(sink.buffer.read(), name=f"{cls.url}_{timezone.now()}.csv")

    @classmethod
    def load(cls) -> [Table, int]:
        results = cls.load_from_api()
        table = cls.transform_results(results)
        return table, len(results)

    @classmethod
    def load_to_db(cls) -> Collection:
        """
        fetch all records from the api and create a new collection record in the database
        """
        table, nb_records = cls.load()
        return Collection.objects.create(
            file=cls.to_content_file(table), nb_records=nb_records, type=cls.type
        )


class PlanetLoader(APILoader):
    url = "planets"
    type = Collection.Type.PLANET

    @classmethod
    def transform_results(cls, results: list[dict]) -> Table:
        return etl.fromdicts(
            results,
            header=[
                "name",
                "url",
            ],
        )


class PeopleLoader(APILoader):
    url = "people"
    type = Collection.Type.PEOPLE

    @classmethod
    def get_join_tables(cls) -> dict:
        try:
            planet = Collection.objects.filter(type=Collection.Type.PLANET).latest()
            table = etl.fromcsv(planet.file)
        except (Collection.DoesNotExist, FileNotFoundError):
            # we don't directly load_to_db, so we get a ref to table object
            table, nb_records = PlanetLoader.load()
            Collection.objects.create(
                file=PlanetLoader.to_content_file(table),
                type=Collection.Type.PLANET,
                nb_records=nb_records,
            )
        return {"planets": table}

    @classmethod
    def transform_results(cls, results: list[dict]) -> Table:
        join_tables = cls.get_join_tables()
        # Since the crux of the task is making use of petl:
        # Else we could parse the date in python instead (it's already in memory within results), and do the planet
        # mapping in python (we could have planet model in the database directly)
        transformed_table = (
            etl.fromdicts(
                results,
                header=[
                    "name",
                    "height",
                    "mass",
                    "hair_color",
                    "skin_color",
                    "eye_color",
                    "birth_year",
                    "gender",
                    "homeworld",
                    "edited",
                ],
            )
            # we might want to deduplicate the rows here too before doing any processing
            # There's petl.util.parsers.dateparser that will do a better job.
            # But it will be slower as it parses the date, if the dataset is not dirty, this is going to be faster
            .convert("edited", lambda x: (x or "")[:10])
            .leftjoin(join_tables["planets"], lkey="homeworld", rkey="url", rprefix="_")
            .cutout("homeworld")
            .rename({"_name": "homeworld", "edited": "date"})
        )
        return transformed_table


class RecordLoader:
    @classmethod
    def load(cls, path: str, start_row: int = 0, limit: int = 10) -> dict:
        """
        Load records from a given path to a csv file:
        :param path: path to a csv file on disk
        :param start_row: start index for slicing results
        :param limit: max nb os record to return
        :return: dictionary of records and headers
        """
        if path:
            try:
                table = etl.fromcsv(path)
                return {
                    "headers": etl.header(table),
                    "records": table.records(start_row, start_row + limit),
                }
            except FileNotFoundError:
                logger.exception(f"No such file {path}")
        return {"headers": [], "records": []}

    @classmethod
    def load_aggregate(cls, path: str, group_by: list[str]) -> dict:
        """
        Load records and run aggregation from a given path to a csv file:
        :param path: path to a csv file on disk
        :param group_by: list of columns to perform the aggregation
        :return: dictionary of records and headers
        """
        if path:
            try:
                table = etl.fromcsv(path).aggregate(group_by, len, field="Count")
                return {"headers": etl.header(table), "records": table.records()}
            except FileNotFoundError:
                logger.exception(f"No such file {path}")
        return {"headers": [], "records": []}
