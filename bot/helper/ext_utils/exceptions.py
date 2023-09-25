class DirectDownloadLinkException(Exception):
    pass


class NotSupportedExtractionArchive(Exception):
    """The archive format use is trying to extract is not supported"""
    pass


class RssShutdownException(Exception):
    """This exception should be raised when shutdown is called to stop the montior"""
    pass


class TgLinkException(Exception):
    """No Access granted for this chat"""
    pass