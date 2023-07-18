from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime
from decimal import Decimal
from time import sleep

import logging
import MainMenu
import configparser
import FulfillerDetails
import DynamoDB
import re
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

####################################### Helper Functions #######################################


####################################### Main Functions #######################################
async def awaitFulfiller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request made by the requester.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])

    # Check the status of the chat (i.e. finding fulfiller, in-convo, or cancelled). If fulfiller not found, return back to awaitFulfiller method.
    if (response["Item"]["request_status"] == "Available"):
        
        # TODO: delete request when user uses /cancel here. (EDIT: implement using conv_handler in MainMenu using command handlers)
        await update.message.reply_text("We are still trying to find a fulfiller. Please wait, or use /cancel to quit and remove your current request.")

        return MainMenu.AWAIT_FULFILLER
    elif (response["Item"]["request_status"] == "In Progress"):
        # Get the message the requester is trying to send to the fulfiller
        requesterMsg = update.message.text

        # Get the request the requester has put out and update user_data
        request = response["Item"]
        context.user_data[MainMenu.REQUEST_MADE] = request

        # Store information about the event.
        logger.info("Requester '%s' (chat_id: '%s') sent message to fulfiller '%s' (chat_id: '%s'): %s", request["requester_user_name"], request["requester_chat_id"],
                    request["fulfiller_user_name"], request["fulfiller_chat_id"], requesterMsg)

        in_chat_reminder = f"<b><u>Requester '{update.effective_user.name}' sent the following message:</u></b>\n\n"

        # Send the message (with in-chat reminder) to the fulfiller via the fullfiler's chat id.
        await context.bot.send_message(chat_id=request["fulfiller_chat_id"], text=in_chat_reminder + requesterMsg, parse_mode="HTML")

        return MainMenu.REQUESTER_IN_CONVO
    
async def requesterCancelSearch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the request ID of the request to be deleted by the requester.
    RequestID = context.user_data[MainMenu.REQUEST_MADE]["RequestID"]
    response = DynamoDB.table.delete_item(Key = {"RequestID": RequestID})

    logger.info(f"Requester {update.effective_user.name} (chat_id: {update.effective_user.id}) deleted their request (RequestID: {RequestID}) before a fulfiller was found")
    logger.info("DynamoDB delete response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    await update.message.reply_text("Request cancelled! Use /start to use Dabao4Me again.")

    return ConversationHandler.END

async def promptEditRequest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Define the menu using a 2D array.
    inlineMenu = [
        [InlineKeyboardButton("Change Canteen Location", callback_data="editCanteen")],
        [InlineKeyboardButton("Change Food Option", callback_data="editFood")],
        [InlineKeyboardButton("Change Tip Amount", callback_data="editTip")]
    ]

    # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
    inlineMenuTG = InlineKeyboardMarkup(inlineMenu)

    # Log event
    logger.info(f"Requester {update.effective_user.name} (chat_id: {update.effective_user.id}) is modifying their request.")

    await update.message.reply_text("Please select the part of the request you'd like to edit: ", reply_markup=inlineMenuTG)

    return MainMenu.EDIT_ORDER

# When the fulfiller ends the conversation using the /end command.
async def fulfillerEndConv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request selected by the fulfiller.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_CHOSEN]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_CHOSEN]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the request the fulfiller has chosen.
    request = response["Item"]

    # Update request_status in DynamoDB to "Closed".
    response = DynamoDB.table.update_item(
        Key = {
            "RequestID": request["RequestID"]
        },
        UpdateExpression = "SET request_status = :status",
        ExpressionAttributeValues = {
            ":status" : "Closed"
        }
    )

    # Update status for request variable before updating user_data
    request['request_status'] = "Closed"
    context.user_data[MainMenu.REQUEST_CHOSEN] = request

    logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Update chat_status in local python DS to "end".
    # MainMenu.available_requests[MainMenu.available_requests.index(requestMade)]["chat_status"] = "end"

    # Prompt fulfiller to confirm that the conversation has ended.
    await update.message.reply_text(f"You have ended the conversation with '{request['requester_user_name']}'. Use /start to request or fulfil an order again.")

    # Prompt requester to notify them that the conversation has ended.
    await context.bot.send_message(chat_id=request["requester_chat_id"], text=f"'{request['fulfiller_user_name']}' has ended the conversation. Use /start to request or fulfil an order again.")

    # Store information about their name.
    logger.info("Fulfiller '%s' (chat_id: '%s') ended a conversation with '%s' (chat_id: '%s').", request["fulfiller_user_name"], request["fulfiller_chat_id"],
                request["requester_user_name"], request["requester_chat_id"])

    return ENDConv

# When the requester ends the conversation using the /end command.
async def requesterEndConv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request selected by the fulfiller.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_MADE]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the request the fulfiller has chosen.
    request = response["Item"]

    # Additional check needed here as this function might be called before the user is even connected to a user (while requester is in the midst of getting matched)
    if (request["request_status"] == "Available"):
        await update.message.reply_text("No conversation to end (we are still trying to find a fulfiller). Please wait, or use /cancel to quit and remove your current request.")

        return MainMenu.AWAIT_FULFILLER

    # Update request_status in DynamoDB to "Closed".
    response = DynamoDB.table.update_item(
        Key = {
            "RequestID": request["RequestID"]
        },
        UpdateExpression = "SET request_status = :status",
        ExpressionAttributeValues = {
            ":status" : "Closed"
        }
    )

    # Update status for request variable before updating user_data
    request['request_status'] = "Closed"
    context.user_data[MainMenu.REQUEST_MADE] = request

    logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])


    # Update chat_status in local python DS to "end".
    # MainMenu.available_requests[MainMenu.available_requests.index(requestMade)]["chat_status"] = "end"

    # Prompt requester to confirm that the conversation has ended.
    await update.message.reply_text(f"You have ended the conversation with '{request['fulfiller_user_name']}'. Use /start to request or fulfil an order again.")

    # Prompt fulfiller to notify them that the conversation has ended.
    await context.bot.send_message(chat_id=request["fulfiller_chat_id"], text=f"'{request['requester_user_name']}' has ended the conversation. Use /start to request or fulfil an order again.")

    # Store information about their name.
    logger.info("Requester '%s' (chat_id: '%s') ended a conversation with '%s' (chat_id: '%s').", request["requester_user_name"], ["requester_chat_id"],
                request["fulfiller_user_name"], request["fulfiller_chat_id"])

    return ENDConv

async def fulfilRequest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Store user's argument for the /fulfil command
    userInput = context.args[0]
    
    # Get the canteen the fulfiller selected.
    selectedCanteen = context.user_data[MainMenu.CANTEEN]

    # Regex pattern for integers only
    intPattern = r"^\d+$"

    # Check that user input is an integer
    if not re.match(intPattern, userInput):
        await update.message.reply_text("Sorry, you have entered an invalid input (numbers only). Please try again.")
        return MainMenu.FULFIL_REQUEST
    
    # Input has been verified to be an integer
    requestIndex = int(userInput) - 1
    
    # Check that user input is not out of range
    try: 
        selectedRequest = FulfillerDetails.filterRequests(selectedCanteen)[requestIndex]
    except IndexError:
        await update.message.reply_text("Invalid request number. Please try again.")
        return MainMenu.FULFIL_REQUEST  

    # Get the specific request from the list of requests of the selected canteen via the requestIndex.
    # 1. Via DynamoDB
    selectedRequest = FulfillerDetails.filterRequests(selectedCanteen)[requestIndex]

    # 2. Via python local storage
    #selectedRequest = FulfillerDetails.filterRequests(MainMenu.available_requests, selectedCanteen)[requestIndex]

    response = DynamoDB.table.update_item(
        Key = {
            "RequestID": selectedRequest["RequestID"]
        },
        UpdateExpression = "SET fulfiller_chat_id = :chat_id, fulfiller_user_name = :user_name, request_status = :status",
        ExpressionAttributeValues = {
            ":chat_id" : str(update.effective_user.id),
            ":user_name" : update.effective_user.name,
            ":status" : "In Progress"
        }
    )

    # Update attributes for request variable before updating user_data
    selectedRequest['fulfiller_chat_id'] = str(update.effective_user.id)
    selectedRequest['fulfiller_user_name'] = update.effective_user.name
    selectedRequest['request_status'] = "In Progress"
    context.user_data[MainMenu.REQUEST_MADE] = selectedRequest

    logger.info("DynamoDB update_item response for RequestID '%s': '%s'", selectedRequest["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # # Update local python DS to include the requester's chat_id and username in the request.
    # MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["fulfiller_chat_id"] = update.effective_user.id

    # selectedRequest["fulfiller_chat_id"] = update.effective_user.id

    # MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["fulfiller_user_name"] = update.effective_user.name

    # selectedRequest["fulfiller_user_name"] = update.effective_user.name

    # MainMenu.available_requests[MainMenu.available_requests.index(selectedRequest)]["chat_status"] = "connected"

    # selectedRequest["chat_status"] = "connected"

    # Store the selected request the fulfiller has chosen into user_data
    context.user_data[MainMenu.REQUEST_CHOSEN] = FulfillerDetails.get_item(selectedRequest["RequestID"])["Item"]

    # Send message to fulfiller to indicate connection to the requester.
    await update.message.reply_text("You are now connected with the requester! Use /end to end the conversation at any time.")

    # Send message to requester to indicate connection to the fulfiller.
    await context.bot.send_message(chat_id=selectedRequest["requester_chat_id"], text="Fulfiller found!. You are now connected with the fulfiller! Use /end to end the conversation at any time.")

    # Store information about the event.
    logger.info("Fulfiller '%s' (chat_id: '%s') started a conversation with '%s' (chat_id: '%s').", selectedRequest["fulfiller_user_name"], selectedRequest["fulfiller_chat_id"],
                selectedRequest["requester_user_name"], selectedRequest["requester_chat_id"])

    return MainMenu.FULFILLER_IN_CONVO


async def forwardFulfillerMsg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request selected by the fulfiller.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_CHOSEN]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_CHOSEN]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the message the fulfiller is trying to send to the requester
    fulfillerMsg = update.message.text

    try:
        # Get the request the fulfiller has chosen.
        request = response["Item"]
        context.user_data[MainMenu.REQUEST_CHOSEN] = request
    except KeyError:
        # This triggers in the event where the requester does /cancel instead of /end to 
        # gracefully end the convo, and the fulfiller tries to send a message to the requester.
        await update.message.reply_text(f"The requester has deleted their request. Use /start to request or fulfill an order again.")
        return ENDConv

    # Check if requester has ended the chat before sending the message to the requester.
    if (request["request_status"] == "Closed"):
        await update.message.reply_text(f"'{request['requester_user_name']}' has ended the conversation. Use /start to request or fulfill an order again.")
        return ENDConv
    elif (request["request_status"] == "Complete"):
        await update.message.reply_text(f"The conversation has ended. Please rate '{request['requester_user_name']}' Use /start to request or fulfill an order again.")
        return ENDConv

    # Else, store information about the event.
    logger.info("Fulfiller '%s' (chat_id: '%s') sent message to requester '%s' (chat_id: '%s'): %s", request["fulfiller_user_name"], request["fulfiller_chat_id"],
                request["requester_user_name"], request["requester_chat_id"], fulfillerMsg)

    in_chat_reminder = f"<b><u>Fulfiller '{request['fulfiller_user_name']}' sent the following message:</u></b>\n\n"

    await context.bot.send_message(chat_id=request['requester_chat_id'], text=in_chat_reminder + fulfillerMsg, parse_mode="HTML")

    return MainMenu.FULFILLER_IN_CONVO


async def forwardRequesterMsg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request made by the requester.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_MADE]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the message the requester is trying to send to the fulfiller
    requesterMsg = update.message.text

    # Get the request the requester has put out.
    request = response["Item"]
    context.user_data[MainMenu.REQUEST_MADE] = request
    
    # Check valid convo status.
    if (request["request_status"] == "Closed"):
        await update.message.reply_text(f"'{request['fulfiller_user_name']}' has ended the conversation. Use /start to request or fulfill an order again.")
        return ENDConv
    elif (request["request_status"] == "Complete"):
        await update.message.reply_text(f"The conversation has ended. Please rate '{request['fulfiller_user_name']}' Use /start to request or fulfill an order again.")
        return ENDConv

    # Else, store information about the event.
    logger.info("Requester '%s' (chat_id: '%s') sent message to fulfiller '%s' (chat_id: '%s'): %s", request["requester_user_name"], request["requester_chat_id"],
                request["fulfiller_user_name"], request["fulfiller_chat_id"], requesterMsg)


    in_chat_reminder = f"<b><u>Requester '{request['requester_user_name']}' sent the following message:</u></b>\n\n"

    await context.bot.send_message(chat_id=request['fulfiller_chat_id'], text=in_chat_reminder + requesterMsg, parse_mode="HTML")

    return MainMenu.REQUESTER_IN_CONVO


async def requesterComplete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request made by the requester.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_MADE]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the request the requester has put out.
    request = response["Item"]
    context.user_data[MainMenu.REQUEST_MADE] = request
    
    # Check if the stauts of the request is "In progress" before allowing requester to confirm the order.
    if (request["request_status"] == "In Progress"):

        # Check if fulfiller has already sent the "/confirm command"
        if (request["fulfiller_complete"] == "true"):

            # If fulfiller has already confirmed the fulfillment of the request, send the appropriate message to the requester
            await update.message.reply_text(f"The request is now complete. Enjoy your meal! Please rate '{request['fulfiller_user_name']}'.")

            # Send the appropriate message to the fulfiller
            await context.bot.send_message(chat_id=request["fulfiller_chat_id"], text=f"The request is now marked as complete. Please rate '{request['requester_user_name']}'.")

            # Update request_status in DynamoDB to "Complete".
            response = DynamoDB.table.update_item(
                Key = {
                    "RequestID": request["RequestID"]
                },
                UpdateExpression = "SET request_status = :status",
                ExpressionAttributeValues = {
                    ":status" : "Complete"
                }
            )

            # Update status for request variable before updating user_data
            request['request_status'] = "Complete"
            context.user_data[MainMenu.REQUEST_MADE] = request

            logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

            return MainMenu.RATE_USER
        
        else:
            # Else, requester is the one that initiated the confirmation of the request, send the appropritate message to the requester
            await update.message.reply_text(f"You have initiated to mark the order as complete. Please wait for '{request['fulfiller_user_name']}' to confirm before you can leave a rating for them.")

            # Send the appropriate message to the fulfiller
            await context.bot.send_message(chat_id=request["fulfiller_chat_id"], text=f"'{request['requester_user_name']}' has initiated to make the order as complete. To confirm and leave a review for them, please use the '/complete' command.")

            # Update requester_complete to "true"
            response = DynamoDB.table.update_item(
                Key = {
                    "RequestID": request["RequestID"]
                },
                UpdateExpression = "SET requester_complete = :complete",
                ExpressionAttributeValues = {
                    ":complete" : "true"
                }
            )

            # Update status for request variable before updating user_data
            request['requester_complete'] = "true"
            context.user_data[MainMenu.REQUEST_MADE] = request

            logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

            return MainMenu.REQUESTER_IN_CONVO
        
    else:
        await update.message.reply_text(f"Fulfiller has yet to be found. Please use the command only when a fulfiller has been found, and you have agreed with them to mark the order as complete.")

        return MainMenu.AWAIT_FULFILLER
    

async def fulfillerComplete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Query the DB for the request made by the fulfiller.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])

    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_MADE]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the request the fulfiller has put out.
    request = response["Item"]
    context.user_data[MainMenu.REQUEST_CHOSEN] = request

    # Check if requester has already sent the "/confirm command"
    if (request["requester_complete"] == "true"):

        # If requester has already confirmed the fulfillment of the request, send the appropriate message to the fulfiller
        await update.message.reply_text(f"The request is now complete. \n\nPlease rate '{request['requester_user_name']}'.")

        # Send the appropriate message to the requester
        await context.bot.send_message(chat_id=request["requester_chat_id"], 
                                       text=f"The request is now marked as complete. Enjoy your meal!  \n\nPlease rate '{request['fulfiller_user_name']}'.")

        # Update request_status in DynamoDB to "Complete".
        response = DynamoDB.table.update_item(
            Key = {
                "RequestID": request["RequestID"]
            },
            UpdateExpression = "SET request_status = :status",
            ExpressionAttributeValues = {
                ":status" : "Complete"
            }
        )
        
        # Update status for request variable before updating user_data
        request['request_status'] = "Complete"
        context.user_data[MainMenu.REQUEST_MADE] = request
        logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

        return MainMenu.RATE_USER
    
    else:
        # Else, fulfiller is the one that initiated the confirmation of the request, send the appropritate message to the fulfiller
        await update.message.reply_text(f"You have initiated to mark the order as complete. Please wait for '{request['requester_user_name']}' to confirm before you can leave a rating for them.")

        # Send the appropriate message to the requester
        await context.bot.send_message(chat_id=request["requester_chat_id"], text=f"'{request['fulfiller_user_name']}' has initiated to make the order as complete. To confirm and leave a review for them, please use the '/complete' command.")

        # Update fulfiller_complete to "true"
        response = DynamoDB.table.update_item(
            Key = {
                "RequestID": request["RequestID"]
            },
            UpdateExpression = "SET fulfiller_complete = :complete",
            ExpressionAttributeValues = {
                ":complete" : "true"
            }
        )

        # Update status for request variable before updating user_data
        request['fulfiller_complete'] = "true"
        context.user_data[MainMenu.REQUEST_MADE] = request
        logger.info("DynamoDB update_item response for RequestID '%s': '%s'", request["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

        return MainMenu.FULFILLER_IN_CONVO