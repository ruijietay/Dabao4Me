from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime
from decimal import Decimal

import logging
import re
import MainMenu
import boto3
import configparser

####################################### Parameters #######################################

# Create config parser and read config file
config = configparser.ConfigParser()
config.read("config.ini")

# Load bot token
bot_token = config["bot_keys"]["current_bot_token"]

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

########## Initialising DB and Required Tables ##########

# The name of our table in DynamoDB
tableName = "Dabao4Me_Requests"

# Create resource object to access DynamoDB
db = boto3.resource("dynamodb", 
                    region_name = config["dynamodb"]["region_name"], 
                    aws_access_key_id = config["dynamodb"]["aws_access_key_id"],
                    aws_secret_access_key = config["dynamodb"]["aws_secret_access_key"])

# Create table object with specified table name (the request table)
table = db.Table(tableName)

####################################### Helper Functions #######################################

# Function to put item in a given table
def put_item(table, cols, requestID, requester_telegram_user_id, canteen, food, tip_amount, status):
    data = {
        cols[0]: requestID,
        cols[1]: requester_telegram_user_id,
        cols[2]: canteen,
        cols[3]: food,
        cols[4]: tip_amount,
        cols[5]: status
    }
    
    response = table.put_item(Item = data)

    return response

# Get the request from the local python DS.
def getRequest(available_requests, request_id):

    for request in available_requests:
        if request_id == request['request_id']:
            return request


####################################### Main Functions #######################################

async def promptCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the role selected from the user and store into user_data
    context.user_data[MainMenu.ROLE] = update.callback_query.data

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their role.
    user = update.callback_query.from_user
    logger.info("Role of '%s' (chat_id: '%s'): '%s'", update.effective_user.name, update.effective_user.id, update.callback_query.data)

    await update.callback_query.message.reply_text(text=f"You have chosen to be a {context.user_data[MainMenu.ROLE]}.")

    # Define the canteens using a 2D array.
    inlineCanteen = [
        [InlineKeyboardButton("The Deck", callback_data="deck")],
        [InlineKeyboardButton("Frontier", callback_data="frontier")],
        [InlineKeyboardButton("Fine Foods", callback_data="fine_foods")],
        [InlineKeyboardButton("Flavours @ Utown", callback_data="flavours")],
        [InlineKeyboardButton("TechnoEdge", callback_data="technoedge")],
        [InlineKeyboardButton("PGPR", callback_data="pgpr")],
    ]

    # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
    inlineCanteenTG = InlineKeyboardMarkup(inlineCanteen)

    await update.callback_query.message.reply_text("Now, please select from the list of canteens.", reply_markup=inlineCanteenTG)

    return MainMenu.CANTEEN

async def selectCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the canteen selected from the requester and store the input into user_data
    context.user_data[MainMenu.CANTEEN] = update.callback_query.data

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Let user know their selected canteen.
    await update.callback_query.message.reply_text(text=f"You have chosen {MainMenu.canteenDict[update.callback_query.data]} as your canteen.")

    # Store information about their canteen.
    user = update.callback_query.from_user
    logger.info("Requester '%s' (chat_id: '%s') selected '%s' as their canteen.", update.effective_user.name, update.effective_user.id, context.user_data[MainMenu.CANTEEN])

    await update.callback_query.message.reply_text("Great! Now, please state the food you'd like to order.")

    return MainMenu.FOOD

async def requesterFood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    # Get the food requested from the requester and store it in user_data.
    context.user_data[MainMenu.FOOD] = update.message.text

    # Store information about their name.
    user = update.message.from_user
    logger.info("Requester '%s' (chat_id: '%s') entered '%s' as their food at '%s' canteen.", update.effective_user.name, update.effective_user.id,
                context.user_data[MainMenu.FOOD], context.user_data[MainMenu.CANTEEN])

    await update.message.reply_text("Finally, how much would you like to tip the fulfiller for your request? (excluding food prices, to the nearest cent)")

    return MainMenu.OFFER_PRICE

async def requesterPrice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tip_pattern = r'^\d+(\.\d{1,2})?$'

    if not re.match(tip_pattern, update.message.text):
        await update.message.reply_text("Sorry, you have entered an invalid input. Please try again.")
        return MainMenu.OFFER_PRICE
    
    # Get the tipping amount from the requester and store it in user_data.
    context.user_data[MainMenu.OFFER_PRICE] = Decimal(update.message.text)

    # Store information about their name.
    user = update.message.from_user
    logger.info("Tip amount set by requester '%s': '%0.2f'", update.effective_user.name, context.user_data[MainMenu.OFFER_PRICE])

    # RequestID which consists of time + telegram username
    requestID = "{}{}".format(datetime.now().timestamp(), update.effective_user.id)

    # Columns in the request table in DynamoDB
    columns = ["RequestID", "requester_telegram_user_id", "canteen", "food", "tip_amount", "status"]

    request = {
        "request_id" : requestID,
        "requester_chat_id" : update.effective_user.id,
        "requester_user_name" : update.effective_user.name,
        "canteen" : context.user_data[MainMenu.CANTEEN],
        "food" : context.user_data[MainMenu.FOOD],
        "tip_amount" : context.user_data[MainMenu.OFFER_PRICE],
        "fulfiller_chat_id" : "",
        "fulfiller_user_name" : "",
        "status" : "Available",
        "chat_status" : "await"
    }

    # Store the input of the requester's request into user_data.
    context.user_data[MainMenu.REQUEST_MADE] = request
    
    # Put details of request into local python DS.
    MainMenu.available_requests.append(request)
    
    # Put item in table
    response = put_item(table,
                        columns,
                        requestID, 
                        update.effective_user.id, 
                        context.user_data[MainMenu.CANTEEN], 
                        context.user_data[MainMenu.FOOD], 
                        context.user_data[MainMenu.OFFER_PRICE],
                        "Available")
    
    logger.info("DynamoDB put_item response for request_id '%s': '%s'", requestID, response["ResponseMetadata"]["HTTPStatusCode"])

    await update.message.reply_text(parse_mode="HTML", 
                                    text="Request placed! \n<b><u>Summary</u></b>" + 
                                    "\nCanteen: " + MainMenu.canteenDict[context.user_data[MainMenu.CANTEEN]] + 
                                    "\nFood: " + context.user_data[MainMenu.FOOD] +
                                    "\nTip Amount: $" + str(context.user_data[MainMenu.OFFER_PRICE]))
    
    await update.message.reply_text("We will notify and connect you with a fulfiller when found.")

    return MainMenu.AWAIT_FULFILLER
