# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
#   Desc.:      Helper Distribution code
#   Purpose:    Helper code for PSet7_Finance of CS50
#   Author:     CS50
#   Date:       ?
#   
#   Licensing Info:
#   ?
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

# Imports:
import csv
import urllib.request

from flask import redirect, render_template, request, session, url_for
from functools import wraps

# ---------------------------------------------------------------------------
#   Desc.:      APOLOGY(top_text, bottom_text)
#   Purpose:    Renders a grumpycat message as an apology to the user
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
def apology(top="", bottom=""):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=escape(top), bottom=escape(bottom))

# ---------------------------------------------------------------------------
#   Desc.:      LOGIN_REQUIRED(function)
#   Purpose:    Decorate routes to require login.
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - modifies the input flask function to require a login
# ---------------------------------------------------------------------------
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------------------------
#   Desc.:      LOOKUP(stock_symbol)
#   Purpose:    Looks up a quote for a stock from Yahoo Finance
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - returns none on failure to retrieve stock
#   - Yahoo csv format is [SYMBOL, NAME, PRICE]
# ---------------------------------------------------------------------------
def lookup(symbol):
    """Look up quote for symbol."""

    # reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # reject symbol if it contains comma
    if "," in symbol:
        return None

    # query Yahoo for quote
    # http://stackoverflow.com/a/21351911
    try:
        url = "http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={}".format(symbol)
        webpage = urllib.request.urlopen(url)
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())
        row = next(datareader)
    except:
        return None

    # ensure stock exists
    try:
        price = float(row[2])
    except:
        return None

    # return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
    return {
        "name": row[1],
        "price": price,
        "symbol": row[0].upper()
    }

# ---------------------------------------------------------------------------
#   Desc.:      USD(Dollar_Amount)
#   Purpose:    Reformats a number into United States Dollars
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - used in a Jinja custom filter (made by CS50)
#   - reformats the stock quotes from Yahoo Finance into USD
# ---------------------------------------------------------------------------
def usd(value):
    """Formats value as USD."""
    return "${:,.2f}".format(value)
    

# ---------------------------------------------------------------------------
#   Desc.:      stockmove(db, user_id, symbol, amount)
#   Purpose:    Inserts a record into the transactions table
#   Author:     Joel Tannas
#   Date:       
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
def stockmove(db, user_id, symbol, amount):
    """Inserts a record into the transactions table"""
    return db.execute("INSERT INTO transactions(user_id, symbol, amount) " 
                    + "VALUES (:user_id, :symbol, :units)", 
                    user_id = user_id, 
                    symbol = symbol, 
                    units = amount)
            
# ---------------------------------------------------------------------------
#   Desc.:      stockbalance(db, user_id, symbol)
#   Purpose:    Retrieves the stock balance for a stock for a user
#   Author:     Joel Tannas
#   Date:       
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
def stockbalance(db, user_id, symbol):
    """ Gets the balance for a user's individual stock"""
    
    rows = db.execute("SELECT symbol, SUM(amount) AS amount "
                    + "FROM transactions "
                    + "WHERE user_id=:user_id AND symbol=:symbol "
                    + "GROUP BY symbol", 
                     user_id = user_id, 
                     symbol = symbol)
                     
    if len(rows) != 1:
        return None
    else:
        return rows[0]["amount"]