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

# Define ConversationHandler.END in another variable for clarity.
ENDRequesterConv = ConversationHandler.END

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

########## Initialising DB and Required Tables ##########

# The name of our table in DynamoDB
tableName = "Dabao4Me_Requests"

# Create resource object to access DynamoDB
db = boto3.resource('dynamodb', 
                    region_name = config["dynamodb"]["region_name"], 
                    aws_access_key_id = config["dynamodb"]["aws_access_key_id"],
                    aws_secret_access_key = config["dynamodb"]["aws_secret_access_key"])

# Create table object with specified table name (the request table)
table = db.Table(tableName)

####################################### Helper Functions #######################################

# Function to put item in a given table
def put_item(table, cols, requestID, requester_telegram_username, canteen, food, tip_amount, status):
    data = {
        cols[0]: requestID,
        cols[1]: requester_telegram_username,
        cols[2]: canteen,
        cols[3]: food,
        cols[4]: tip_amount,
        cols[5]: status
    }
    
    response = table.put_item(Item = data)

    return response

####################################### Main Functions #######################################

async def promptCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the role selected from the user.
    roleSelected = update.callback_query.data

    # Store the input of the user's role into user_data.
    context.user_data[MainMenu.ROLE] = roleSelected

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their role.
    user = update.callback_query.from_user
    logger.info("Role of %s: %s", user.first_name, update.callback_query.data)

    await update.callback_query.message.reply_text(text=f"You have chosen to be a {roleSelected}.")

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
    # Get the canteen selected from the requester.
    canteenSelected = update.callback_query.data

    # Store the input of the requester's canteen into user_data
    context.user_data[MainMenu.CANTEEN] = canteenSelected

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their name.
    user = update.callback_query.from_user
    logger.info("Canteen selected by %s (%s): %s ", user.first_name, context.user_data[MainMenu.ROLE], update.callback_query.data)

    await update.callback_query.message.reply_text("Great! Now, please state the food you'd like to order.")

    return MainMenu.FOOD

async def requesterFood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    # Get the food requested from the requester.
    requesterFood = update.message.text

    # Store the input of the requester's choice of food into user_data
    context.user_data[MainMenu.FOOD] = requesterFood

    # Store information about their name.
    user = update.message.from_user
    logger.info("Food of %s: %s", user.first_name, requesterFood)

    await update.message.reply_text("Finally, how much would you like to tip the fulfiller for your request? (excluding food prices, to the nearest cent)")

    return MainMenu.OFFER_PRICE

async def requesterPrice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tip_pattern = r'^\d+(\.\d{1,2})?$'

    if not re.match(tip_pattern, update.message.text):
        await update.message.reply_text("Sorry, you have entered an invalid input. Please try again.")
        return MainMenu.OFFER_PRICE
    
    # Get the tipping amount from the requester.
    requesterPrice = Decimal(update.message.text)

    # Store the input of the requester's tipping amount into user_data.
    context.user_data[MainMenu.OFFER_PRICE] = requesterPrice

    # Store information about their name.
    user = update.message.from_user
    logger.info("Tip amount set by %s: %0.2f", user.first_name, requesterPrice)

    # Put details of request into data structure.
    MainMenu.available_requests.append({
        # Potential Issue: Not every telegram account has a username.
        "username" : update.effective_user.name,
        "canteen" : context.user_data[MainMenu.CANTEEN],
        "food" : context.user_data[MainMenu.FOOD],
        "tip_amount" : context.user_data[MainMenu.OFFER_PRICE],
        "chat_id" : update.effective_user.id,
        "fulfiller" : ""
    })

    # RequestID which consists of time + telegram username
    requestID = "{}{}".format(datetime.now().timestamp(), update.effective_user.name)

    # Columns in the request table in DynamoDB
    columns = ["RequestID", "requester_telegram_username", "canteen", "food", "tip_amount", "status"]
    
    # Put item in table
    response = put_item(table,
                        columns,
                        requestID, 
                        update.effective_user.name, 
                        context.user_data[MainMenu.CANTEEN], 
                        context.user_data[MainMenu.FOOD], 
                        context.user_data[MainMenu.OFFER_PRICE],
                        "Available")
    
    logger.info("DynamoDB put_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    await update.message.reply_text(parse_mode="HTML", 
                                    text="Request placed! \n<b><u>Summary</u></b>" + 
                                    "\nCanteen: " + MainMenu.canteenDict[context.user_data[MainMenu.CANTEEN]] + 
                                    "\nFood: " + context.user_data[MainMenu.FOOD] +
                                    "\nTip Amount: $" + str(context.user_data[MainMenu.OFFER_PRICE]))
    
    await update.message.reply_text("We will notify and connect you with a fulfiller when found.")

    return MainMenu.AWAIT_FULFILLER
