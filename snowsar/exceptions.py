"""SnowSAR exception hierarchy."""


class SnowSARError(Exception):
    """Base exception for all SnowSAR errors."""


class DataProviderError(SnowSARError):
    """Raised when a data provider fails to fetch or preprocess data."""


class AlgorithmError(SnowSARError):
    """Raised when an algorithm encounters an error during retrieval."""


class ValidationError(SnowSARError):
    """Raised when input validation fails."""


class JobError(SnowSARError):
    """Raised when job orchestration encounters an error."""
