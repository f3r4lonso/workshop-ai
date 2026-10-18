"""Error type and exit codes (spec section 9)."""

OK = 0
USAGE = 1        # usage error or not found
VALIDATION = 2   # format, scan block, hash mismatch
REFUSED = 3      # approval declined, conflict, forbidden location
ENVIRONMENT = 4  # client or infra not found, project not initialized


class WaiError(Exception):
    """An expected failure: message says what failed and what to do next."""

    def __init__(self, message, code=USAGE):
        super().__init__(message)
        self.code = code
