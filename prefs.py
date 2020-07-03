import json
import os.path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

"""
TODO:
Add "Load on startup" checkbox option.
Needs to create ~/.config/autostart/desktop-agenda.desktop link to /usr/share/applications/desktop-agenda.desktop

On Apply, update app to reflect new preferences
"""


class PrefsWindow(Gtk.Window):

    PREFS_DIR = os.path.expanduser("~/.dags")
    PREFS_FILE = "preferences.json"

    PREF_QUERY_DAYS = "queryDays"
    PREF_QUERY_LIMIT = "queryLimit"
    PREF_STYLE_CALENDAR_COLORS = "styleCalendarColors"
    PREF_SCREEN_POSITION = "screenPosition"

    def __init__(self):
        self._query_days = 7
        self._query_limit = 20  # Max number of items to query per calendar
        self._style_calendar_colors = True  # Whether to use calendar colors from API
        self._screen_position = "right"  # TODO: Make an enum or reuse some Gtk.halign value
        self.load_preferences()

        Gtk.Window.__init__(self)
        self.set_title("Desktop Agenda Preferences")

    def get_query_days(self):
        return self._query_days

    def set_query_days(self, query_days):
        try:
            val = int(query_days)
            if 1 <= val <= 365:
                self._query_days = val
        except ValueError:
            pass  # TODO: Notify user of invalid input

    def get_query_limit(self):
        return self._query_limit

    def set_query_limit(self, query_limit):
        try:
            val = int(query_limit)
            if 1 <= val <= 50:
                self._query_limit = val
        except ValueError:
            pass  # TODO: Notify user of invalid input

    def get_style_calendar_colors(self):
        return self._style_calendar_colors

    def set_style_calendar_colors(self, style_calendar_colors):
        # TODO: Validate boolean
        self._style_calendar_colors = style_calendar_colors

    def get_screen_position(self):
        return self._screen_position

    def set_screen_position(self, screen_position):
        # TODO: Validate enum
        self._screen_position = screen_position

    def load_preferences(self):
        prefs_file = os.path.join(self.PREFS_DIR, self.PREFS_FILE)
        if not os.path.exists(prefs_file):
            print "Creating new prefs file"
            self.save_preferences()
            return

        prefs = json.load(open(prefs_file))

        # Look for values in JSON, continue using current value if item isn't in config
        self.set_query_days(prefs.get(self.PREF_QUERY_DAYS, self._query_days))
        self.set_query_limit(prefs.get(self.PREF_QUERY_LIMIT, self._query_limit))
        self.set_style_calendar_colors(prefs.get(self.PREF_STYLE_CALENDAR_COLORS, self._style_calendar_colors))
        self.set_screen_position(prefs.get(self.PREF_SCREEN_POSITION, self._screen_position))

        print "Loaded preferences"

    def save_preferences(self):
        if not os.path.exists(self.PREFS_DIR):
            os.mkdir(self.PREFS_DIR, 0o700)

        prefs = {
            self.PREF_QUERY_DAYS: self.get_query_days(),
            self.PREF_QUERY_LIMIT: self.get_query_limit(),
            self.PREF_STYLE_CALENDAR_COLORS: self.get_style_calendar_colors(),
            self.PREF_SCREEN_POSITION: self.get_screen_position()
        }

        prefs_file = os.path.join(self.PREFS_DIR, self.PREFS_FILE)
        json.dump(prefs, open(prefs_file, "w"))

        print "Saved preferences"
