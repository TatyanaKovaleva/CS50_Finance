# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
#   Desc.:      The primary controller of website logic for 'finance'
#   Purpose:    Pset7 distribution code
#   Author:     CS50 / Joel Tannas
#   Date:       ? / Feb 2017
#   
#   Licensing Info:
#   ?
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

# Imports:
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# 'Constants'
USD_sentinel = "cash_USD"

# Functions:

# ---------------------------------------------------------------------------
#   Desc.:      APPLICATION INITIALIZE
#   Purpose:    Initializes the finance application object
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------

# configure application
# aka. Initialize the application object
app = Flask(__name__)

# ensure responses aren't cached
# aka. Do not pull webpages from the cache - always get them from the server
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response
        
# custom filter
app.jinja_env.filters["usd"] = usd # usd is a helper function

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite} Index Page
#   Purpose:    Provides an summary page of the user's stocks
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-index-code
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
@login_required
def index():
    
    # --- Section 010: Retrieve a summary of the users stocks
    rows = db.execute("SELECT symbol, SUM(amount) AS amount "
                        + "FROM transactions "
                        + "WHERE user_id=:user_id "
                        + "GROUP BY symbol "
                        + "HAVING SUM(amount) != 0 ",
                        user_id = session["user_id"])
                            
    if len(rows) == 0:
        return render_template("index.html")
    
    # --- Section 020: Lookup the stock information and make a dict
    total = 0
    stocks = {}
    
    # Iterate over the user stocks    
    for row in rows:
        
        # Fill the info for cash manually
        if row["symbol"] == USD_sentinel:
            quote = {
                    "name" : "US Dollars",
                    "price" : 1.00,
                    "symbol" : "$"
                    }
        # Else, use lookup to retrieve the stock info
        else:
            quote = lookup(row["symbol"])
            if quote == None:
                quote = {
                        "name" : "Unknown Stock",
                        "price" : 0.00,
                        "symbol" : row["symbol"]
                        }
                    
        # Add a dict entry to the stocks dict with stock information
        stockval = quote["price"] * row["amount"]
        total += stockval
        
        stocks[row["symbol"]] = {
                                "symbol" : quote["symbol"],
                                "name" : quote["name"],
                                "price" : usd(quote["price"]),
                                "amount" : "{:,.2f}".format(row["amount"]),
                                "value" : usd(stockval)
                                }
        
    return render_template("index.html", 
                            stocklist = sorted(stocks), 
                            stocks = stocks,
                            total = usd(total))
        
# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/BUY
#   Purpose:    Allows the user to purchase stocks
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-buy-code
# ---------------------------------------------------------------------------
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        
        # --- Section 010: Pre-transaction validation
        symbol = request.form.get("symbol")
        try:
            units = int(request.form.get("units"))
            if units < 0:
                return apology("Use the sell webpage to sell stocks")
        except ValueError:
            return apology("That is not a valid cash amount")
        
        if not symbol or not units:
            return apology("Please provide a stock symbol and cash value")
        
        # --- Section 020: Lookup the current information on the stock
        quote = lookup(symbol)
        if quote == None:
            return apology("Unable to find stock: {}".format(symbol))
            
        # --- Section 025: Check for sufficient cash to purchase
        balance = stockbalance(db, session["user_id"], USD_sentinel)
        if balance == None:
            return apology("Error getting your USD balance")
            
        value = units * quote["price"]
        if balance < value:
            return apology("Insufficient funds to complete this transaction")
        
        # --- Section 030: Remove the money and add the stock
        stockmove(db, session["user_id"], USD_sentinel, -1 * value)
        stockmove(db, session["user_id"], quote["symbol"], units)
        
        flash("Transaction Complete")    
        return render_template("confirmation.html",
                                action = "bought",
                                quote = quote, 
                                amount = "{:,.2f}".format(units))
            
    else:
        return render_template("buy.html")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/CHANGEPASSWORD
#   Purpose:    Allows the user to change their password
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    """Allows the user to change their password."""
    if request.method == "POST":
        
        # --- Section 010: Validate the inputs
        # get the inputs
        oldword = pwd_context.encrypt(request.form.get("oldword"))
        password1 = pwd_context.encrypt(request.form.get("password"))
        password2 = pwd_context.encrypt(request.form.get("password2"))
        
        # ensure all passwords are submitted
        if not oldword:
            apology("You must provide your old password for confirmation")
        elif not password1 or not password2:
            return apology("must provide a new password in both fields")
            
        # ensure that the passwords match
        elif not pwd_context.verify(request.form.get("password"), password2):
            return apology("new passwords do not match each other")
            
        # --- Section 020: Verify the old password against the db
        # query database for username
        rows = db.execute("SELECT * "
                        + "FROM users "
                        + "WHERE id = :user_id " 
                        , user_id=session["user_id"]
                        )
        
        # check the old password
        if not pwd_context.verify(request.form.get("oldword"), rows[0]["password"]):
            return apology("Invalid old password")
            
        # --- Section 030: Update the password
        db.execute("UPDATE users "
                + "SET password=:newpw "
                + "WHERE :user_id=:user_id "
                , newpw = password1
                , user_id = session["user_id"]
                )
                        
        flash("Password changed")
        return redirect(url_for("index"))
    else:
        return render_template("changepassword.html")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/CONFIRMATION
#   Purpose:    Confirms a successful stock buy or sell
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-buy-code
# ---------------------------------------------------------------------------
@app.route("/confirmation", methods=["GET", "POST"])
@login_required
def confirmation():
    """Confirms a successful stock buy or sell."""
    if request.method == "POST":
        return render_template("index.html")
    else:
        return render_template("confirmation.html")
        
# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/HISTORY
#   Purpose:    Displays a list of transactions from the user
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-history-code
# ---------------------------------------------------------------------------
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""

    # Rerieve the user transactions
    rows = db.execute("SELECT * FROM transactions "
                    + "WHERE user_id=:user_id "
                    + "ORDER BY id DESC",
                    user_id=session["user_id"])
        
    # Pass them to the history page
    return render_template("history.html", rows = rows)

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/INTRO
#   Purpose:    Renders the "Intro to stocks" webpage
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
@app.route("/intro", methods=["GET", "POST"])
@login_required
def intro():
    return render_template("intro.html")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/LOGIN
#   Purpose:    Logs user in
#   Author:     CS50 (reformated by Joel Tannas for style)
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * "
                        + "FROM users "
                        + "WHERE username = :username", 
                        username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["password"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/LOGOUT
#   Purpose:    Logging out the user from their session
#   Author:     CS50
#   Date:       ?
#
#   Bugs, Limitations, and Other Notes:
#   - 
# ---------------------------------------------------------------------------
@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/QUOTE
#   Purpose:    Retrieves a stock quote for the user
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-quote-code
# ---------------------------------------------------------------------------
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        
        # --- Section 010: Pre-lookup validation
        symbol = request.form.get("symbol")
        try:
            units = int(request.form.get("units"))
        except ValueError:
            return apology("That is not a valid stock amount")
        
        if not symbol or not units:
            return apology("Please provide a stock symbol and number of stocks")
        
        # --- Section 020: Lookup the current information on the stock
        quote = lookup(symbol)
        if quote == None:
            return apology("Unable to find stock: {}".format(symbol))
            
        # --- Section 030: Get the cash balance for comparison
        balance = stockbalance(db, session["user_id"], USD_sentinel)
        value = units * quote["price"]
        if balance == None:
            user_message = "Error: Could not retrieve your cash balance"
        else:
            user_message = "Your cash balance is" + usd(balance)
        
        return render_template("quoted.html", 
                                quote = quote, 
                                amount = "{:,.2f}".format(units),
                                value = usd(value),
                                user_message = user_message)
    else:
        return render_template("quote.html")
        
# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/QUOTED
#   Purpose:    Displays a stock quote for the user
#   Author:     Joel Tannas
#   Date:       
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-quote-code
# ---------------------------------------------------------------------------
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quoted():
    return render_template("quoted.html")

# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/REGISTER
#   Purpose:    Registers a new user to the website
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-register-code
#   - inspired by the login method made by CS50 (above)
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # --- Section 010: Validate inputs ---
        
        # get the inputs
        username = request.form.get("username")
        password1 = pwd_context.encrypt(request.form.get("password"))
        password2 = pwd_context.encrypt(request.form.get("password2"))
        
        # ensure username was submitted
        if not username:
            return apology("must provide username")

        # ensure both passwords are submitted
        elif not password1 or not password2:
            return apology("must provide a password in both fields")
            
        # ensure that the passwords match
        elif not pwd_context.verify(request.form.get("password"), password2):
            return apology("passwords do not match each other")

        # --- Section 020: Prevent duplicate users ---
        rows = db.execute("SELECT * "
                        + "FROM users " 
                        + "WHERE username = :username", 
                        username = username)
        if len(rows) != 0:
            return apology("username has already been taken")

        # --- Section 030: Add the user to the database
        # add the user
        db.execute("INSERT INTO users(username, password) "
                + "VALUES (:username, :password)", 
                username = username, 
                password = password1)
            
        # retrieve the newly created user_id
        rows = db.execute("SELECT * "
                        + "FROM users "
                        + "WHERE username = :username", 
                        username = username)
        if len(rows) != 1:
            return apology("failed to create new user in database")
        
        # add the starting funds
        stockmove(db, rows[0]["id"], USD_sentinel, 10000)
            
        # --- Section 040: Login the new user & direct to the index 
        session.clear()
        session["user_id"] = rows[0]["id"]
        return redirect(url_for("index"))

    # GET request procedure
    else:
        return render_template("register.html")
        
# ---------------------------------------------------------------------------
#   Desc.:      {MyWebsite}/SELL
#   Purpose:    Sells a stock from the user's portfolio
#   Author:     Joel Tannas
#   Date:       Feb 2017
#
#   Bugs, Limitations, and Other Notes:
#   - http://docs.cs50.net/problems/finance/finance.html#code-sell-code
# ---------------------------------------------------------------------------
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        
        # --- Section 010: Pre-transaction validation
        # Ensure a stock and # of stocks has been provided
        symbol = request.form.get("symbol")
        units = request.form.get("units")
        if units != "Sell All":
            try:
                units = int(request.form.get("units"))
                if units < 0:
                    return apology("Use the buy webpage to buy stocks")
            except ValueError:
                return apology("That is not a valid stock amount")
        
        if not symbol or not units:
            return apology("Please provide a stock symbol and number of stocks")
        
        # --- Section 020: Lookup the current information on the stock
        quote = lookup(symbol)
        if quote == None:
            return apology("Unable to find stock: {}".format(symbol))
            
        # --- Section 025: Check for sufficient stock to sell
        balance = stockbalance(db, session["user_id"], symbol)
        if balance == None:
            return apology("Error getting your stock balance")

        if units == "Sell All":
            units = balance
        elif units < balance:
            return apology("Insufficient stocks to complete this transaction")
        
        # --- Section 030: Remove the stock and add the money
        value = units * quote["price"]
        stockmove(db, session["user_id"], USD_sentinel, value)
        stockmove(db, session["user_id"], quote["symbol"], -1 * units)
        
        # --- Section 040: Render the transaction confirmation
        flash("Transaction Complete")     
        return render_template("confirmation.html",
                                action = "sold",
                                quote = quote, 
                                amount = "{:,.2f}".format(units))
    
    # GET request procedure        
    else:
        return render_template("sell.html")
