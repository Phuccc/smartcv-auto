from fastapi.templating import Jinja2Templates
from datetime import datetime

templates = Jinja2Templates(directory="app/templates")

def format_datetime(value, format="%d/%m/%Y"):
    if value is None:
        return ""
    return value.strftime(format)

templates.env.filters["strftime"] = format_datetime
