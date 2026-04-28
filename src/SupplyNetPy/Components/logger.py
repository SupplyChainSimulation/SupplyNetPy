import logging

__all__ = ["GlobalLogger"]

# Library root logger name. Per-node loggers in ``core.py`` are created as
# ``f"{_LIBRARY_LOGGER_NAME}.{node.ID}"`` so they propagate to this single
# logger; handlers are attached only here, never per-node. The
# ``_ShortNameFilter`` strips the prefix when records are formatted, so
# ``INFO sim_trace.D1 - ...`` displays as ``INFO D1 - ...`` — preserving the
# log-line shape users have always seen.
_LIBRARY_LOGGER_NAME = "sim_trace"
_LOG_FORMAT = "%(levelname)s %(short_name)s - %(message)s"


class _ShortNameFilter(logging.Filter):
    """Adds ``record.short_name`` (``record.name`` without the ``sim_trace.``
    prefix) so per-node child loggers display as ``D1`` rather than
    ``sim_trace.D1``. Doing this in a filter — not by mutating ``record.name``
    in a custom Formatter — keeps the original name intact for any other
    handler that might be reading it."""

    _PREFIX = _LIBRARY_LOGGER_NAME + "."

    def filter(self, record):
        if record.name.startswith(self._PREFIX):
            record.short_name = record.name[len(self._PREFIX):]
        else:
            record.short_name = record.name
        return True


class GlobalLogger(logging.LoggerAdapter):
    """
    Library-wide :class:`logging.LoggerAdapter` with on/off file and screen handlers.

    Subclasses :class:`logging.LoggerAdapter` so callers can write
    ``node.logger.info(...)`` (and ``debug`` / ``warning`` / ``error`` /
    ``critical``) directly — no more ``node.logger.logger.info(...)`` double-hop.
    The underlying :class:`logging.Logger` is still reachable as
    ``self.logger`` (the standard adapter attribute), so older code that
    reaches through that attribute keeps working.

    **The wrapper is inert by default.** ``GlobalLogger()`` attaches only a
    :class:`logging.NullHandler` and does not open any file — output is opt-in.
    Call :meth:`enable_logging` (or pass ``log_to_file=True`` /
    ``log_to_screen=True`` to the constructor) to attach real handlers. This is
    the documented Python-library logging pattern; see
    https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library

    The library exports a module-level ``global_logger = GlobalLogger()`` from
    ``core.py`` whose underlying :class:`logging.Logger` is named
    ``"sim_trace"``. Every per-node logger created by :class:`Node` lives at
    ``"sim_trace.<node.ID>"`` and propagates up to ``"sim_trace"`` — so all
    log routing is configured in **one place** by calling
    ``scm.global_logger.enable_logging(...)``. ``simulate_sc_net(logging=True)``
    does this automatically; users who drive ``env.run(...)`` themselves and
    want a log file must call it explicitly.

    Parameters:
        logger_name (str): Name of the underlying :class:`logging.Logger`.
            Defaults to ``"sim_trace"``.
        log_to_file (bool): Attach a :class:`logging.FileHandler` writing to
            ``log_file`` (mode ``'w'``). Defaults to ``False`` — opt-in.
        log_file (str): Destination file path. Only opened when
            ``log_to_file`` is ``True``. Defaults to ``"simulation_trace.log"``.
        log_to_screen (bool): Attach a :class:`logging.StreamHandler`. Defaults
            to ``False`` — opt-in.

    Attributes:
        logger (logging.Logger): The underlying logger instance (inherited
            from :class:`logging.LoggerAdapter`).
        log_to_file (bool): Current file-handler flag.
        log_to_screen (bool): Current screen-handler flag.
        log_file (str): Current destination file path.

    Functions:
        debug/info/warning/error/critical/log/exception: Inherited from
            :class:`logging.LoggerAdapter` — call them directly on the
            adapter instead of routing through ``.logger``.
        set_log_file(filename): Set the destination file and re-attach handlers.
        get_log_file(): Return the current log file path.
        set_logger(logger_name): Rebind ``self.logger`` to a different name.
        configure_logger(): Re-build handlers from current flags. Always
            attaches :class:`logging.NullHandler`.
        enable_logging(log_to_file=True, log_to_screen=True): Opt-in: attach
            handlers and unmute the logger.
        disable_logging(): Mute the logger and drop handlers (NullHandler stays).
    """

    def __init__(self,
                 logger_name=_LIBRARY_LOGGER_NAME,
                 log_to_file=False,
                 log_file='simulation_trace.log',
                 log_to_screen=False):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        # The library root logger should not leak records up to Python's root
        # logger — that would dump our logs into whatever the host application
        # has configured. Per-node child loggers keep ``propagate=True`` so
        # their records still reach the handlers attached here.
        if logger_name == _LIBRARY_LOGGER_NAME:
            logger.propagate = False
        # Fresh GlobalLogger == fresh slate: a previous instance may have set
        # disabled=True on the same underlying Python logger.
        logger.disabled = False
        # extra=None: we don't inject any contextual fields. The base
        # LoggerAdapter.process() returns (msg, kwargs) unchanged in that case.
        super().__init__(logger, extra=None)

        self.log_to_file = log_to_file
        self.log_to_screen = log_to_screen
        self.log_file = log_file
        self.configure_logger()

    def set_log_file(self, filename):
        """Set the destination log file and re-attach handlers."""
        self.log_file = filename
        self.configure_logger()

    def get_log_file(self):
        """Return the current log file path."""
        return self.log_file

    def set_logger(self, logger_name):
        """Rebind the underlying logger to a different name."""
        self.logger = logging.getLogger(logger_name)

    def configure_logger(self):
        """
        Replace this logger's handlers based on current ``log_to_file`` /
        ``log_to_screen`` flags. A :class:`logging.NullHandler` is always
        attached so the logger never triggers Python's "No handlers could be
        found" stderr fallback — the recommended default for library loggers.
        """
        self.logger.handlers = [logging.NullHandler()]

        if self.log_to_screen:
            screen_handler = logging.StreamHandler()
            screen_handler.setLevel(logging.DEBUG)
            screen_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
            screen_handler.addFilter(_ShortNameFilter())
            self.logger.addHandler(screen_handler)

        if self.log_to_file:
            file_handler = logging.FileHandler(self.log_file, mode='w')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
            file_handler.addFilter(_ShortNameFilter())
            self.logger.addHandler(file_handler)

    def enable_logging(self, log_to_file=True, log_to_screen=True):
        """Opt-in. Unmute the logger and (re)attach screen and/or file handlers
        according to the arguments. Defaults are ``True`` for both so a bare
        ``enable_logging()`` call gives the user the historical "noisy"
        behavior on demand."""
        self.logger.disabled = False
        self.log_to_file = log_to_file
        self.log_to_screen = log_to_screen
        self.configure_logger()

    def disable_logging(self):
        """Mute the logger. Sets ``self.logger.disabled = True`` and drops all
        handlers (a :class:`logging.NullHandler` is re-attached so the logger
        remains well-formed). Note: this only affects ``self.logger`` — it
        does not touch the global ``logging.disable`` switch, which would
        suppress the host application's own logging."""
        self.logger.disabled = True
        self.logger.handlers = [logging.NullHandler()]
        self.log_to_file = False
        self.log_to_screen = False
