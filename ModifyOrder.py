from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import DynamoDB
import configparser
from datetime import datetime
from boto3.dynamodb.conditions import Key
import MainMenu
import re

####################################### Parameters #######################################

# Create config parser and read config file
config = configparser.ConfigParser()
config.read("config.ini")

# Load bot token
bot_token = config["bot_keys"]["current_bot_token"]

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

table = DynamoDB.table

####################################### Helper Functions #######################################

# Get all available requests from given chat ID
def getAvailableRequestsFromChatId(chatId):
    response = table.query(
        IndexName = "requester_chat_id-request_status-index",
        KeyConditionExpression = Key("requester_chat_id").eq(str(chatId)) & Key("request_status").eq("Available"))

    logger.info("DynamoDB query response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    requests = response["Items"]

    # Sort according to timestamp
    sorted_requests = sorted(requests, key=lambda x: x["RequestID"][:16])

    return sorted_requests

####################################### Main Functions #######################################

async def displayUserRequests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Store user's chat ID
    chatId = update.effective_chat.id

    requests = getAvailableRequestsFromChatId(chatId)

    if (len(requests) == 0):
        await update.callback_query.message.reply_text("You have no available orders.")

        return ConversationHandler.END

    # Properly format available requests from that user
    formatted_output = ""
    requestCounter = 1

    for request in requests:
        formattedCanteen = request["canteen"]
        requestID = request["RequestID"]
        # The first 17 characters of the requestID is the time of the request.
        unixTimestamp = float(requestID[:16])
        username = request["requester_user_name"]
        food = request["food"]
        tip_amount = request["tip_amount"]

        formattedTimestamp = datetime.fromtimestamp(unixTimestamp).strftime("%d %b %y %I:%M %p")

        formatted_output += f"""{requestCounter}) Requested on: {formattedTimestamp}
Username / Name: {username}
Canteen: {formattedCanteen}
Food: {food}
Tip Amount: ${tip_amount}

"""
        requestCounter += 1

    logger.info("'%s' (chat_id: '%s') displayed all available orders.", update.effective_user.name, update.effective_chat.id)

    # Send formatted output to user
    await update.callback_query.message.reply_text("Here are all your currently availble requests: \n\n" +
                                                   formatted_output)
    
    await update.callback_query.message.reply_text("Which request would you like to cancel? e.g. \"1\"")
    
    return MainMenu.DELETE_ORDER

async def deleteSelectedOrder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chatId = update.effective_chat.id
    intPattern = r"^\d+$"
    userInput = update.message.text
    
    if not re.match(intPattern, userInput):
        await update.message.reply_text("Sorry, you have entered an invalid input. Please try again.")
        return MainMenu.DELETE_ORDER
    
    selectedRequest = getAvailableRequestsFromChatId(chatId)[int(userInput) - 1]

    response = DynamoDB.table.delete_item(Key = {"RequestID": selectedRequest["RequestID"]})

    logger.info("DynamoDB delete response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    await update.message.reply_text("Request cancelled!")

    return ConversationHandler.END