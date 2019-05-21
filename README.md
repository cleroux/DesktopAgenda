# DesktopAgenda
Your calendars overlaid on the desktop.

Install Dependencies
--------------------
```
sudo apt install python-pip python-dateutil python-tz python-gi python-appindicator gir1.2-appindicator3-0.1
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oathlib
```

Clone Repository
----------------
```
git clone https://github.com/cleroux/DesktopAgenda.git
```

Launch the application
----------------------
```
nohup python desktop_agenda.py >/dev/null &
```
