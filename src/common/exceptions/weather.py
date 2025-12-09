"""Weather service exceptions."""

from . import ApplicationError


class WeatherError(ApplicationError):
    """Base weather error."""

    pass


class WeatherServiceError(WeatherError):
    """Weather service operational error."""

    pass
