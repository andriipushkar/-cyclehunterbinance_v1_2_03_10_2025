class BinanceClientException(Exception):
    """Base exception for BinanceClient errors."""
    pass

class SymbolPriceError(BinanceClientException):
    """Raised when the symbol price cannot be fetched."""
    pass
