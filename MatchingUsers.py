from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime
from decimal import Decimal
from time import sleep

import logging
import re
import MainMenu
import boto3
import configparser
import FulfillerDetails
import RequesterDetails

####################################### Parameters #######################################

# Create config parser and read config file
config = configparser.ConfigParser()
config.read("config.ini")

# Load bot token
bot_token = config["bot_keys"]["current_bot_token"]

# Define ConversationHandler.END in another variable for clarity.
ENDConv = ConversationHandler.END

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


ENDRequesterConv = ConversationHandler.END
ENDFulfillerConv = ConversationHandler.END

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
    # If fulfiller not found, return back to awaitFulfiller method.
    if (MainMenu.available_requests[MainMenu.available_requests.index(context.user_data[MainMenu.REQUEST_MADE])]["chat_status"] == "await"):
        
        # TODO: delete request when user uses /cancel here. (EDIT: implement using conv_handler in MainMenu using command handlers)
        await update.message.reply_text("We are still trying to find a fulfiller. Please wait, or use /cancel to quit.")

        return MainMenu.AWAIT_FULFILLER
    else:
        # Get the message the requester is trying to send to the fulfiller
        requesterMsg = update.message.text

        # Get the request the requester has put out.
        requestMade = context.user_data[MainMenu.REQUEST_MADE]

        # Check if fulfiller has ended the conversation before the requester even sends their first message
        if (MainMenu.available_requests[MainMenu.available_requests.index(context.user_data[MainMenu.REQUEST_MADE])]["chat_status"] == "end"):
            await update.message.reply_text(f"'{requestMade['fulfiller_user_name']}' has ended the conversation. Use /start to request or fulfill an order again.")
            return ENDConv

        # Store information about the event.
        logger.info("Requester '%s' (chat_id: '%s') sent message to fulfiller '%s' (chat_id: '%s'): %s", requestMade["requester_user_name"], requestMade["requester_chat_id"],
                    requestMade["fulfiller_user_name"], requestMade["fulfiller_chat_id"], requesterMsg)

        in_chat_reminder = f"<b><u>Requester '{update.effective_user.name}' sent the following message:</u></b>\n\n"

        # Else, send the message (with in-chat reminder) to the fulfiller via the fullfiler's chat id.
        await context.bot.send_message(chat_id=requestMade["fulfiller_chat_id"], text=in_chat_reminder + requesterMsg, parse_mode="HTML")

        return MainMenu.REQUESTER_IN_CONVO

# When the fulfiller ends the conversation using the /end command.
async def fulfillerEndConv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # The request the fulfiller has initally chosen.
    requestChosen = context.user_data[MainMenu.REQUEST_CHOSEN]

    # Update chat_status in local python DS to "end".
    MainMenu.available_requests[MainMenu.available_requests.index(requestChosen)]["chat_status"] = "end"

    # Prompt fulfiller to confirm that the conversation has ended.
    await update.message.reply_text(f"You have ended the conversation with '{requestChosen['requester_user_name']}'. Use /start to request or fulfil an order again.")

    # Prompt requester to notify them that the conversation has ended.
    await context.bot.send_message(chat_id=requestChosen["requester_chat_id"], text=f"'{requestChosen['fulfiller_user_name']}' has ended the conversation. Use /start to request or fulfil an order again.")

    # Store information about their name.
    logger.info("Fulfiller '%s' (chat_id: '%s') ended a conversation with '%s' (chat_id: '%s').", requestChosen["fulfiller_user_name"], requestChosen["fulfiller_chat_id"],
                requestChosen["requester_user_name"], requestChosen["requester_chat_id"])

    return ENDConv

# When the requester ends the conversation using the /end command.
async def requesterEndConv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # The request the requester has initially put out.
    requestMade = context.user_data[MainMenu.REQUEST_MADE]

    # Update chat_status in local python DS to "end".
    MainMenu.available_requests[MainMenu.available_requests.index(requestMade)]["chat_status"] = "end"

    # Prompt requester to confirm that the conversation has ended.
    await update.message.reply_text(f"You have ended the conversation with '{requestMade['fulfiller_user_name']}'. Use /start to request or fulfil an order again.")

    # Prompt fulfiller to notify them that the conversation has ended.
    await context.bot.send_message(chat_id=requestMade["fulfiller_chat_id"], text=f"'{requestMade['requester_user_name']}' has ended the conversation. Use /start to request or fulfil an order again.")

    # Store information about their name.
    logger.info("Requester '%s' (chat_id: '%s') ended a conversation with '%s' (chat_id: '%s').", requestMade["requester_user_name"], ["requester_chat_id"],
                requestMade["fulfiller_user_name"], requestMade["fulfiller_chat_id"])

    return ENDConv

async def fulfilRequest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the index of the request.
    requestIndex = int(context.args[0]) - 1

    # Get the canteen the fulfiller selected.
    selectedCanteen = context.user_data[MainMenu.CANTEEN]

    # Get the specific request from the list of requests of the selected canteen via the requestIndex.
    selectedRequest = FulfillerDetails.filterRequests(MainMenu.available_requests, selectedCanteen)[requestIndex]

    # Update local python DS to include the requester's chat_id and username in the request.
    MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["fulfiller_chat_id"] = update.effective_user.id

    selectedRequest["fulfiller_chat_id"] = update.effective_user.id

    MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["fulfiller_user_name"] = update.effective_user.name

    selectedRequest["fulfiller_user_name"] = update.effective_user.name

    MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["chat_status"] = "connected"

    selectedRequest["chat_status"] = "connected"

    # Store the selected request the fulfiller has chosen into user_data
    context.user_data[MainMenu.REQUEST_CHOSEN] = selectedRequest

    # Send message to fulfiller to indicate connection to the requester.
    await update.message.reply_text("Here are the details of the request once more. You are now connected with the requester." + str(selectedRequest))

    # Send message to requester to indicate connection to the fulfiller.
    await context.bot.send_message(chat_id=selectedRequest["requester_chat_id"], text="Fulfiller found!. You are now connected with the fulfiller." + str(selectedRequest))

    # Store information about the event.
    logger.info("Fulfiller '%s' (chat_id: '%s') started a conversation with '%s' (chat_id: '%s').", selectedRequest["fulfiller_user_name"], selectedRequest["fulfiller_chat_id"],
                selectedRequest["requester_user_name"], selectedRequest["requester_chat_id"])

    return MainMenu.FULFILLER_IN_CONVO


async def forwardFulfillerMsg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the message the fulfiller is trying to send to the requester
    fulfillerMsg = update.message.text

    # Get the request the fulfiller has chosen.
    chosenRequest = context.user_data[MainMenu.REQUEST_CHOSEN]

    # Check if requester has ended the chat before sending the message to the requester.
    if (MainMenu.available_requests[MainMenu.available_requests.index(chosenRequest)]["chat_status"] == "end"):
        await update.message.reply_text(f"'{chosenRequest['requester_user_name']}' has ended the conversation. Use /start to request or fulfill an order again.")
        return ENDConv

    # Else, store information about the event.
    logger.info("Fulfiller '%s' (chat_id: '%s') sent message to requester '%s' (chat_id: '%s'): %s", chosenRequest["fulfiller_user_name"], chosenRequest["fulfiller_chat_id"],
                chosenRequest["requester_user_name"], chosenRequest["requester_chat_id"], fulfillerMsg)

    in_chat_reminder = f"<b><u>Fulfiller '{chosenRequest['fulfiller_user_name']}' sent the following message:</u></b>\n\n"

    await context.bot.send_message(chat_id=chosenRequest['requester_chat_id'], text=in_chat_reminder + fulfillerMsg, parse_mode="HTML")

    return MainMenu.FULFILLER_IN_CONVO


async def forwardRequesterMsg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the message the requester is trying to send to the fulfiller
    requesterMsg = update.message.text

    # Get the request the requester has put out.
    requestMade = context.user_data[MainMenu.REQUEST_MADE]
    
    # Check if requester has ended the chat before sending the message to the requester.
    if (MainMenu.available_requests[MainMenu.available_requests.index(requestMade)]["chat_status"] == "end"):
        await update.message.reply_text(f"'{requestMade['requester_user_name']}' has ended the conversation. Use /start to request or fulfill an order again.")
        return ENDConv

    # Else, store information about the event.
    logger.info("Fulfiller '%s' (chat_id: '%s') sent message to requester '%s' (chat_id: '%s'): %s", requestMade["fulfiller_user_name"], requestMade["fulfiller_chat_id"],
                requestMade["requester_user_name"], requestMade["requester_chat_id"], requesterMsg)


    in_chat_reminder = f"<b><u>Requester '{requestMade['requester_user_name']}' sent the following message:</u></b>\n\n"

    await context.bot.send_message(chat_id=requestMade['fulfiller_chat_id'], text=in_chat_reminder + requesterMsg, parse_mode="HTML")

    return MainMenu.REQUESTER_IN_CONVO
