import datetime as dt

def getDateTimeNow():
    formatDate = dt.datetime.now().strftime("%Y.%m.%d %a %H:%M:%S")
    return formatDate