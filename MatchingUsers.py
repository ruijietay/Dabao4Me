from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime
from decimal import Decimal

import logging
import re
import MainMenu
import boto3
import configparser
import FulfillerDetails

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
def put_item(table, cols, requestID, requester_telegram_username, canteen, food, tip_amount):
    data = {
        cols[0]: requestID,
        cols[1]: requester_telegram_username,
        cols[2]: canteen,
        cols[3]: food,
        cols[4]: tip_amount
    }
    
    response = table.put_item(Item = data)

    return response

####################################### Main Functions #######################################
async def awaitFulfiller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    

    return ConversationHandler.END

async def fulfillRequest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # Get the index of the request.
    requestIndex = int(context.args[0]) - 1

    # Get the canteen the fulfiller selected.
    selectedCanteen = context.user_data[MainMenu.CANTEEN]

    # Get the specified request from the list of requests of the selected canteen.
    selectedRequest = FulfillerDetails.filterRequests(MainMenu.available_requests, selectedCanteen)[requestIndex]

    # Store the selected request the fulfiller has chosen into user_data
    context.user_data[MainMenu.REQUEST_CHOSEN] = selectedRequest

    await update.message.reply_text("Here are the details of the request. You are now connected with the requester." + str(selectedRequest))

    await update.message.forward(int(selectedRequest['chat_id']))


    return MainMenu.FULFILLER_IN_CONVO


async def forwardFulfillerMsg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the message the fulfiller is trying to send to the requester
    requesterMsg = update.message.text

    # Get the request the fulfiller has chosen.
    chosenRequest = context.user_data[MainMenu.REQUEST_CHOSEN]

    # Store information about their name.
    user = update.message.from_user
    logger.info("%s sent message: %s", user.first_name, requesterMsg)

    await context.bot.send_message(chat_id=chosenRequest['chat_id'], text=requesterMsg)

    return MainMenu.FULFILLER_IN_CONVO
