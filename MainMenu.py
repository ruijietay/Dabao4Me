# Code that prompts the users with menu for them to select the appropriate choices when using the application.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import RequesterDetails
import FulfillerDetails
import MatchingUsers
import configparser
from boto3.dynamodb.conditions import Key
from datetime import datetime
import boto3

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

RESTART, SELECT_ORDER_TO_MODIFY, ROLE, CANTEEN, FOOD, OFFER_PRICE, AWAIT_FULFILLER, REQUEST_MADE, FULFIL_REQUEST, FULFILLER_IN_CONVO, REQUEST_CHOSEN, REQUESTER_IN_CONVO = range(12)

available_requests = []

canteenDict = {
    "deck": "The Deck",
    "frontier": "Frontier",
    "fine_foods": "Fine Foods",
    "flavours": "Flavours @ Utown",
    "technoedge": "TechnoEdge",
    "pgpr": "PGPR"
}

########## Initialising DB and Required Tables ##########

# The name of our table in DynamoDB
tableName = "Dabao4Me_Requests"

# Create resource object to access DynamoDB
db = boto3.resource('dynamodb', 
                    region_name = config["dynamodb"]["region_name"], 
                    aws_access_key_id = config["dynamodb"]["aws_access_key_id"],
                    aws_secret_access_key = config["dynamodb"]["aws_secret_access_key"])


# Create table object with specified table name
table = db.Table(tableName)

####################################### Main Functions #######################################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Define the menu using a 2D array.
    inlineMenu = [
        [InlineKeyboardButton("Request an order", callback_data="requester")],
        [InlineKeyboardButton("Fulfil an order", callback_data="fulfiller")],
        [InlineKeyboardButton("Modify/Cancel an order", callback_data="modify")],
    ]

    # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
    inlineMenuTG = InlineKeyboardMarkup(inlineMenu)

    await update.message.reply_text("Welcome to Dabao4Me! What would you like to do today?:", reply_markup=inlineMenuTG)

    return ROLE


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command. Send /start to begin using the bot.")

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') sent an unknown command.", update.effective_user.name, update.effective_chat.id)


# Method to cancel current transaction
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Current operation cancelled.")

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') cancelled an operation.", update.effective_user.name, update.effective_chat.id)

    return ConversationHandler.END


# If user tries to cancel outside of a transaction, send a slightly more helpful response
async def invalidCancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="There is no ongoing operation to cancel.")

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') sent an invalid '/cancel' command.", update.effective_user.name, update.effective_chat.id)

async def displayUserRequests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Store user's chat ID
    chatId = update.effective_chat.id
    logger.info(chatId)

    # Get all available requests from that user
    response = table.query(
        IndexName = "requester_chat_id-request_status-index",
        KeyConditionExpression = Key("requester_chat_id").eq(str(chatId)) & Key("request_status").eq("Available"))

    logger.info("DynamoDB query response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    requests = response["Items"]

    # Sorts according to timestamp
    sorted_requests = sorted(requests, key=lambda x: x["RequestID"][:17])

    # Properly format available requests from that user
    formatted_output = ""
    requestCounter = 1

    for request in sorted_requests:
        formattedCanteen = request["canteen"]
        requestID = request["RequestID"]
        # The first 17 characters of the requestID is the time of the request.
        unixTimestamp = float(requestID[:17])
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

    # Send formatted output to user
    await update.callback_query.message.reply_text("Here are all your currently availble orders: \n\n" +
                                                   formatted_output)
    
    return

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    fulfiller_in_conv = ConversationHandler(
        entry_points = [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardFulfillerMsg), CommandHandler("end", MatchingUsers.fulfillerEndConv)],
        states = {
            FULFILLER_IN_CONVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardFulfillerMsg)]
        },
        fallbacks = [CommandHandler("end", MatchingUsers.fulfillerEndConv)],
        map_to_parent= {
            MatchingUsers.ENDConv : ConversationHandler.END
        }
    )

    requester_in_conv = ConversationHandler(
        entry_points = [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardRequesterMsg), CommandHandler("end", MatchingUsers.requesterEndConv)],
        states = {
            REQUESTER_IN_CONVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardRequesterMsg)]
        },
        fallbacks = [CommandHandler("end", MatchingUsers.requesterEndConv)],
        map_to_parent= {
            MatchingUsers.ENDConv : ConversationHandler.END
        }
    )

    requester_init = ConversationHandler(
        entry_points = [CallbackQueryHandler(RequesterDetails.promptCanteen, pattern = "requester")],
        states  = {
            CANTEEN: [CallbackQueryHandler(RequesterDetails.selectCanteen)],
            FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)],
            # TODO: include the command for "end" through messagehandler filters so that it can be passed onto the next conversationhandler in requester_in_conv
            AWAIT_FULFILLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.awaitFulfiller), CommandHandler("end", MatchingUsers.requesterEndConv)],
            REQUESTER_IN_CONVO: [requester_in_conv]
        },
        fallbacks = [CommandHandler("cancel", cancel)],
        map_to_parent= {
            MatchingUsers.ENDRequesterConv : ConversationHandler.END
        }
    )

    fulfiller_init = ConversationHandler(
        entry_points = [CallbackQueryHandler(FulfillerDetails.promptCanteen , pattern = "fulfiller")],
        states = {
            CANTEEN: [CallbackQueryHandler(FulfillerDetails.selectCanteen)],
            FULFIL_REQUEST: [CommandHandler("fulfil", MatchingUsers.fulfilRequest)],
            FULFILLER_IN_CONVO: [fulfiller_in_conv]
        },
        fallbacks = [CommandHandler("cancel", cancel)],
        map_to_parent= {
            MatchingUsers.ENDFulfillerConv : ConversationHandler.END
        }
    )

    modifyRequest_handler = ConversationHandler(
        entry_points = [CallbackQueryHandler(displayUserRequests, pattern = "modify")],
        states = {
            SELECT_ORDER_TO_MODIFY: [MessageHandler(filters.Regex(r"^\d+$"), displayUserRequests)]
        },
        fallbacks = [
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT, unknown)
            ]
    )

    # List of handlers that the user can trigger based on their input.
    role_handlers = [
        requester_init,
        fulfiller_init,
        modifyRequest_handler
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RESTART: [CommandHandler("start", start)],
            ROLE: role_handlers
        },
        fallbacks=[CommandHandler("cancel", cancel)])
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("cancel", invalidCancel))
    application.add_handler(MessageHandler(filters.TEXT, unknown))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
