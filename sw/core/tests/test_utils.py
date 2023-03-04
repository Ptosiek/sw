# Not a complete test suite but PeopleLoader and Record Loader are tested
# the views should be tested too

from unittest.mock import patch

import petl as etl

from sw.core.utils import PeopleLoader, RecordLoader


class MockedRequest:
    def __init__(self, ok, **kwargs):
        self.ok = ok
        self.kwargs = kwargs

    def json(self):
        return {**self.kwargs}


# class TestPeopleLoader:
# to implement


class TestPeopleLoader:
    # we test only the correct path, error handling should be tested too

    records = [
        {
            "name": "Luke Skywalker",
            "height": "172",
            "mass": "77",
            "hair_color": "blond",
            "skin_color": "fair",
            "eye_color": "blue",
            "birth_year": "19BBY",
            "gender": "male",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
                "https://swapi.dev/api/films/3/",
                "https://swapi.dev/api/films/6/",
            ],
            "species": [],
            "vehicles": [
                "https://swapi.dev/api/vehicles/14/",
                "https://swapi.dev/api/vehicles/30/",
            ],
            "starships": [
                "https://swapi.dev/api/starships/12/",
                "https://swapi.dev/api/starships/22/",
            ],
            "created": "2014-12-09T13:50:51.644000Z",
            "edited": "2014-12-20T21:17:56.891000Z",
            "url": "https://swapi.dev/api/people/1/",
        }
    ]

    planet_records = [{"url": "https://swapi.dev/api/planets/1/", "name": "Tatooine"}]

    @patch("requests.Session.get")
    def test_load_from_api(self, mock_api):
        mock_api.return_value = MockedRequest(ok=True, results=self.records, next=None)
        ret = PeopleLoader.load_from_api()
        assert ret == self.records

    @patch.object(PeopleLoader, "get_join_tables")
    def test_transform_results(self, mock_get_join_tables):
        mock_get_join_tables.return_value = {
            "planets": etl.fromdicts(self.planet_records)
        }
        table = PeopleLoader.transform_results(self.records)
        assert etl.header(table) == (
            "name",
            "height",
            "mass",
            "hair_color",
            "skin_color",
            "eye_color",
            "birth_year",
            "gender",
            "date",
            "homeworld",
        )

    @patch.object(PeopleLoader, "get_join_tables")
    @patch("requests.Session.get")
    def test_load(self, mock_api, mock_get_join_tables):
        mock_get_join_tables.return_value = {
            "planets": etl.fromdicts(self.planet_records)
        }
        mock_api.return_value = MockedRequest(ok=True, results=self.records, next=None)
        table, nb_records = PeopleLoader.load()
        assert nb_records == len(self.records)

    def test_to_content_file(self):
        table = etl.fromdicts(self.records)
        assert ".csv" in PeopleLoader.to_content_file(table).name


class TestRecordLoader:
    records = [{"id": 1, "year": "2023"}, {"id": 2, "year": "2023"}]

    @patch.object(etl, "fromcsv")
    def test_load(self, mock_fromcsv):
        """
        Test RecordLoader.load method
        validate that empty path is handled gracefully,
        that records are properly returned and slice is working

        """
        mock_fromcsv.return_value = etl.fromdicts(self.records)
        # empty path
        ret = RecordLoader.load("")
        assert len(ret["records"]) == 0

        ret = RecordLoader.load("whatever")
        assert len(ret["records"]) == 2

        # test slicing
        ret = RecordLoader.load("whatever", 1)
        assert len(ret["records"]) == 1
        assert ret["records"][0]["id"] == 2

    @patch.object(etl, "fromcsv")
    def test_load_aggregate(self, mock_fromcsv):
        """
        Test RecordLoader.load_aggregate method
        validate that records are properly aggregated on the passed columns param
        """
        mock_fromcsv.return_value = etl.fromdicts(self.records)
        ret = RecordLoader.load_aggregate("whatever", ["year"])

        assert len(ret["records"]) == 1
        assert ret["records"][0] == ("2023", 2)
