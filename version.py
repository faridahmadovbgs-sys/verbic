"""Single source of truth for the app version.

Bump this (and version_info.txt / installer.iss) for each release, then tag the
repo `vX.Y.Z` so CI builds + publishes the installer. The self-updater compares
this against the latest release reported by the Sky Tools site.
"""
APP_VERSION = "1.1.1"
