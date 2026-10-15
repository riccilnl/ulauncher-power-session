"""Ulauncher 5 extension bridge. Register native apps for single-Enter use."""
import logging
from ulauncher.api.client.Extension import Extension
from desktop_shortcuts import ensure_launchers

class PowerExtension(Extension):
    def __init__(self):
        super().__init__()
        try:
            updated = ensure_launchers()
            self.logger.info("Native power app launchers ready, changed=%d", len(updated))
        except (OSError, RuntimeError, ValueError):
            logging.getLogger(__name__).exception("Unable to install native power app launchers")

if __name__ == "__main__":
    PowerExtension().run()
