# SW

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: MIT

## Basic Commands

Use docker compose to start the project

    $ docker-compose -f local.yml

Then visit  [SW](http://0.0.0.0:8000/)


#### Running tests with pytest and docker

    $ docker-compose -f local.yml run --rm django pytest
