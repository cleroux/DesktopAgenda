# DesktopAgenda
Your calendars overlaid on the desktop.

Install Dependencies
--------------------
```
sudo apt install python-pip python-dateutil python-tz python-gi python-appindicator gir1.2-appindicator3-0.1
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Clone Repository
----------------
```
git clone https://github.com/cleroux/DesktopAgenda.git
```

Obtain API credentials
----------------------
An API credentials file must be created before this application can use the Google Calendar API.  
Visit https://console.developers.google.com/apis/credentials, create an OAuth Client ID and save it as `credentials.json` in your project directory.

Launch the application
----------------------
```
nohup python desktop_agenda.py >/dev/null &
```
