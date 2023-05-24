class TomtomException(Exception):
    pass


class DownloadException(TomtomException):
    pass


class RoadTooLongException(TomtomException):
    pass


class ConsecutivePointsException(TomtomException):
    pass


class TooManyViaPointsException(TomtomException):
    pass
