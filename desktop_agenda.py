#!/usr/bin/env python

from datetime import datetime, timedelta
from dateutil.parser import parse
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, Gdk, GObject, AppIndicator3
from google_calendar import GoogleCalendar
import os.path
import prefs
import pytz
import threading
import time

# TODO: Move these to MainWindow class
CSS_SOURCE = "style.css"
CLOCK_TIME_FORMAT = "%-I:%M %p"
CLOCK_DATE_FORMAT = "%A, %B %-d, %Y"
TIME_LBL_FORMAT = "%-I:%M"

# TODO: Use Gtk.Application / Gtk.ApplicationWindow instead.
# This can provide single instance guarantee and better menu
# and window management.
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/application.html

class MainWindow(Gtk.Window):

    def __init__(self):
        self.row = 0
        self.event_container = None
        self.prefs_window = prefs.PrefsWindow()

        # Initialize the taskbar icon
        self.appindicator = AppIndicator3.Indicator.new("desktop-agenda", "gnome-calendar", AppIndicator3.IndicatorCategory.OTHER)
        self.appindicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Create the dropdown menu for the taskbar icon
        menu = Gtk.Menu()
        item_show_hide = Gtk.MenuItem("Hide")
        item_show_hide.connect("activate", self.show_or_hide)
        item_refresh = Gtk.MenuItem("Refresh")
        item_refresh.connect("activate", self.refresh_agenda)
        item_prefs = Gtk.MenuItem("Preferences")
        item_prefs.connect("activate", self.show_prefs)
        item_quit = Gtk.MenuItem("Quit")
        item_quit.connect("activate", self.quit)
        menu.append(item_show_hide)
        menu.append(item_refresh)
        menu.append(item_prefs)
        menu.append(item_quit)
        menu.show_all()
        self.appindicator.set_menu(menu)

        # Create an instance of the GoogleCalendar class
        self.calendar = GoogleCalendar()

        # Initialize the main window
        Gtk.Window.__init__(self)
        self.set_title("Desktop Agenda")

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is None:
            visual = screen.get_system_visual()
        self.set_visual(visual)

        # Load CSS styles from config file
        if os.path.exists(CSS_SOURCE):
            css = Gtk.CssProvider()
            css.load_from_path(CSS_SOURCE)
            Gtk.StyleContext.add_provider_for_screen(screen, css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        # Set window options
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.NONE)
        self.set_resizable(False)
        self.set_accept_focus(False)
        self.set_keep_below(True)
        self.set_skip_taskbar_hint(True)
        self.set_app_paintable(True)

        # Connect some event handlers to the window for custom behavior
        self.connect("delete-event", Gtk.main_quit)
        self.connect("enter-notify-event", self.enter_notify)
        self.connect("leave-notify-event", self.leave_notify)

        # Create window layout
        self.widgets_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.widgets_container.get_style_context().add_class("container")
        self.add(self.widgets_container)

        clockContainer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.widgets_container.pack_start(clockContainer, True, True, 0)

        self.time_lbl = Gtk.Label(xalign=0)
        self.time_lbl.get_style_context().add_class("lbl")
        self.time_lbl.get_style_context().add_class("time-lbl")
        clockContainer.pack_start(self.time_lbl, False, False, 0)

        self.date_lbl = Gtk.Label(xalign=0)
        self.date_lbl.get_style_context().add_class("lbl")
        self.date_lbl.get_style_context().add_class("date-lbl")
        clockContainer.pack_start(self.date_lbl, False, False, 0)

        # Update clock and calendar at startup
        self.update_clock()
        self.update_agenda(force=True)

        # Create timers to update clock and calendar at fixed time intervals
        GObject.timeout_add(1000, self.update_clock)
        GObject.timeout_add(1000, self.update_agenda)
        GObject.timeout_add(1000, self.reminders)


    def position(self):
        screen = self.get_screen()
        window_size = self.get_size()
        self.move(screen.width() - window_size.width, 0)


    def date_handler(self, date):
        """
        This date handler creates a new label containing the specified date.
        This function may return False to cancel further processing of events.
        Return True to allow processing of events to continue.
        """
        dt = parse(date)

        # Do not create a date label because current date label already exists
        if dt.date() == datetime.today().date():
            return True

        # TODO: If creating a date label and one event label would exceed bottom of
        # screen, set a flag indicating this and return False to prevent further
        # processing. The challenge is in keeping track of where the last label was
        # placed relative to the height of the screen.
        # if self.screenMaxReached:
        #     return

        lbl = Gtk.Label(dt.strftime(CLOCK_DATE_FORMAT), xalign=0)
        lbl.get_style_context().add_class("lbl")
        lbl.get_style_context().add_class("date-header-lbl")
        self.event_container.attach(lbl, 0, self.row, 2, 1)
        self.row += 1

        return True

    def event_handler(self, event):
        """
        This event handler creates labels for a calendar event.
        The label will be created with mouse-over tooltip containing the
        location and name of the meeting organizer.
        A click handler is also created to open the event in a web browser.
        This function may return False to cancel further processing of events.
        Return True to allow processing of events to continue.
        """
        # Useful event fields:
        # event["status"]   - "confirmed"
        # event["htmlLink"] - "https://www.google.com/calendar/event?eid=xxxxxxxx"
        # event["summary"]  - "Status Meeting"
        # event["start"]    - {dateTime: 2019-03-21T10:00:00-07:00}
        # TODO: event["datetime"] - event["start"] parsed into a Python DateTime object
        # event["location"] - "Conference Room"
        # event["organizer"] - {email : email@corp.com}
        # event["creator"] - {email : email@corp.com}

        # TODO: If creating an event label would exceed bottom of screen, set a
        # flag indicating this and return
        # if self.screenMaxReached:
        #     return

        title = event.get("summary", "(No title)")
        ev_time = ""
        location = event.get("location", "(No location)")
        organizer = event.get("organizer", event.get("creator", None))
        if organizer is not None:
            organizer = organizer.get("displayName", organizer.get("email", None))

        html_link = event.get("htmlLink", None)

        date = event["start"].get("dateTime", None)
        if date is not None:
            dt = parse(date)
            ev_time = dt.strftime(TIME_LBL_FORMAT)

        time_lbl = Gtk.Label(xalign=0)
        time_lbl.set_halign(Gtk.Align.END)
        time_lbl.set_markup("<span foreground='{}'>{}</span>".format(event["color"], ev_time))
        time_lbl.get_style_context().add_class("lbl")
        time_lbl.get_style_context().add_class("event-time-lbl")
        self.event_container.attach(time_lbl, 0, self.row, 1, 1)

        title_lbl = Gtk.Label(title, xalign=0)
        title_lbl.set_markup("<span foreground='{}'>{}</span>".format(event["color"], title))

        # Set tooltip
        tooltip_text = "Location: {}".format(location)
        if organizer is not None:
            tooltip_text = "{}\nOrganizer: {}".format(tooltip_text, organizer)
        title_lbl.set_tooltip_text(tooltip_text)

        # Set label style
        title_lbl.get_style_context().add_class("lbl")
        title_lbl.get_style_context().add_class("event-title-lbl")

        # Create a click event handler to open the event in a web browser
        # This handler is unique to this label so it is defined as an inner function
        def lbl_click_handler(widget, event):
            Gtk.show_uri(None, html_link, time.time())

        # Create a container that will handle user interaction
        event_box = Gtk.EventBox()
        event_box.connect("button-press-event", lbl_click_handler)
        # The mouse enter and leave events need to pass through to the main window
        event_box.connect("enter-notify-event", self.event_lbl_enter)
        event_box.connect("leave-notify-event", self.event_lbl_leave)
        event_box.add(title_lbl)

        # Add the new label to the window layout
        self.event_container.attach(event_box, 1, self.row, 1, 1)
        self.row += 1

        return True

    def reminder_handler(self, event):
        """
        Checks if the given event has a notification that needs to be shown and
        creates a taskbar notification if necessary.
        This function may return False to cancel further processing of events.
        Return True to allow processing of events to continue.
        """
        date = event["start"].get("dateTime", None)
        if date is None:
            return True 
        dt = parse(date).astimezone(pytz.utc)
        now = datetime.now(pytz.utc).replace(second=0, microsecond=0)

        for reminder in event["reminders"]:
            method = reminder.get("method", None)
            if method is None or method != "popup":
                continue
            minutes = reminder.get("minutes", 0)
            if minutes <= 0:
                continue
            reminder_time = dt - timedelta(minutes=minutes)
            if reminder_time == now:  #if dt.datetime() == datetime.():
                # TODO: Create popup notification
                print "popup"
                return False # Only create one popup and cancel further event handlers
        return True
            

    def event_lbl_enter(self, widget, event):
        pointer = Gdk.Cursor(Gdk.CursorType.HAND1) # TODO: should pointer be a class variable?
        wnd = self.get_root_window()
        wnd.set_cursor(pointer)
        self.enter_notify(widget, event)
        return False

    def event_lbl_leave(self, widget, event):
        # TODO: Is this the best way to restore the default cursor?
        # We don't know what user's default cursor is set to. Shouldn't assume ARROW
        pointer = Gdk.Cursor(Gdk.CursorType.ARROW)
        wnd = self.get_root_window()
        wnd.set_cursor(pointer)
        return False

    def update_clock(self):
        # TODO: Attempted to decouple clock label updates from agenda updates.
        # If API is unreachable because there is no internet connection,
        # the clock labels stop updating. This is unconfirmed hypothesis
        now = datetime.now()

        time_str = now.strftime(CLOCK_TIME_FORMAT)
        date_str = now.strftime(CLOCK_DATE_FORMAT)
        self.time_lbl.set_text(time_str)
        self.date_lbl.set_text(date_str)

        return True

    def update_agenda(self, force = False):
        """
        Updates the entire adenda window
        This function should return True so the timer will continue to run.
        Returning False will cancel the timer.
        """
        now = datetime.now()

        # TODO: Use a timeout for API requests in google_calendar.py

        if (now.second == 0 and now.minute % 15 == 0) or force:

            self.calendar.load_events(days=self.prefs_window.get_query_days(), max_results=self.prefs_window.get_query_limit()) # Synchronous API query

            # Remove all event labels
            if self.event_container is not None:
                self.event_container.destroy()
                self.row = 0

            # Create new labels
            self.event_container = Gtk.Grid()
            self.widgets_container.pack_start(self.event_container, True, True, 0)

            self.calendar.get_events(self.date_handler, self.event_handler)
            self.show_all()

        return True

    def reminders(self):
        now = datetime.now()
        if now.second == 0:
            self.calendar.get_events(None, self.reminder_handler)
        return True

    def enter_notify(self, event, data):
        self.set_keep_below(False)
        self.set_keep_above(True)
        return False

    def leave_notify(self, event, data):
        self.set_keep_above(False)
        self.set_keep_below(True)
        return False

    def show_or_hide(self, event):
        """
        Toggle the visibility of the main window.
        """
        visible = self.get_property("visible")
        if visible:
            self.hide()
            event.set_label("Show")
        else:
            # TODO: There is a bug here, the window does not appear in the correct location after being hidden and shown again
            self.show()
            event.set_label("Hide")

    def refresh_agenda(self, event):
        self.update_agenda(force=True)

    def show_prefs(self, event):
        """
        Menu handler to show the preferences window.
        """
        # TODO: Preferences window layout is not complete
        self.prefs_window.show_all()
        return

    def quit(self, event):
        Gtk.main_quit()

if __name__ == "__main__":
    window = MainWindow()
    window.show_all()
    window.position()

    Gtk.main()
