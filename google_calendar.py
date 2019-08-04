from datetime import datetime, timedelta
from dateutil.parser import parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle

class GoogleCalendar():
    """
    Helper class for interacting with the Google Calendar API from the Desktop Agenda application.
    An API credentials file must be created before this application can use the API.
    https://console.developers.google.com/apis/credentials    

    Details of the Google Calendar API can be found here:
    https://developers.google.com/resources/api-libraries/documentation/calendar/v3/python/latest/calendar_v3.events.html#list
    """

    CLIENT_SECRETS_FILE = "credentials.json"
    TOKEN_DIR = os.path.expanduser("~/.dags")
    TOKEN_FILE = "token.pickle"
    API_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self):
        if not os.path.exists(self.TOKEN_DIR):
            os.mkdir(self.TOKEN_DIR, 0o700)
        token_file = os.path.join(self.TOKEN_DIR, self.TOKEN_FILE)
        creds = None
        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CLIENT_SECRETS_FILE, self.API_SCOPES)
                creds = flow.run_local_server()
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)

        self._service = build("calendar", "v3", credentials=creds)
        self._colors = {}
        try:
            self._colors = self._service.colors().get().execute()
        except:
            print "Failed to load calendar colors from Calendar API"

        self._events = []

    def load_events(self, date_handler=None, event_handler=None, days=7, max_results=30):
        """
        Query the API for calendar events
        Trigger handlers and return events
        """
        now = datetime.utcnow()
        queryStart = now.isoformat() + "Z"
        queryEnd = (now + timedelta(hours=days*24)).isoformat() + "Z"

        calendars = []
        try:
            #calendars_result = self._service.calendarList().list(minAccessRole="owner").execute()
            calendars_result = self._service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])
        except:
            print "Failed to load calendars from Calendar API"

        shown_events = []
        for cal in calendars:
            calId = cal["id"]
            selected = cal.get("selected", False)
            if not selected:
                continue

            color_id = cal["colorId"]
            color = self._colors.get("calendar", {"calendar":{}}).get(color_id, {"background":None})["background"]

            events_result = None
            try:
                events_result = self._service.events().list(calendarId=calId,
                    timeMin=queryStart, timeMax=queryEnd, maxResults=max_results, singleEvents=True,
                    orderBy="startTime").execute()
                events = events_result.get("items", [])
                reminders = events_result.get("defaultReminders", [])
                for event in events:
                    if color != None:
                        event["color"] = color
                    event["reminders"] = reminders
                    shown_events.append(event)
            except:
                print "Failed to load events from Calendar API"
                
        shown_events.sort(key=self.get_event_datetime)
        self._events = shown_events

        # Call handlers
        self.get_events(date_handler, event_handler)

        return self._events

    def get_events(self, date_handler=None, event_handler=None):
        """
        Trigger handlers and return events previously loaded by load_events()
        """
        cur_date = None
        for event in self._events:
            event_date = self.get_event_datetime(event)
            dt = parse(event_date)

            if cur_date != None:
                cd = parse(cur_date)

            if cur_date == None or dt.date() != cd.date():
                cur_date = event_date
                if date_handler is not None:
                    if date_handler(event_date) != True: # Allow handlers to cancel further processing
                        print "date handler canceled processing"
                        break

            if event_handler is not None:
                if event_handler(event) != True: # Allow handlers to cancel further processing
                    print "event handler canceled processing"
                    break

        return self._events

    @staticmethod
    def get_event_datetime(event):
        ev = event["start"].get("dateTime", event["start"].get("date"))
        return ev
