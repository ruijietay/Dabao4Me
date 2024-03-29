from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import MainMenu
import DynamoDB
import boto3
from boto3.dynamodb.conditions import Key
import configparser
from datetime import datetime

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

# Create table object
table = DynamoDB.table

####################################### Helper Functions #######################################

# Get and format requests from DynamoDB
def processRequests(requests):
    formatted_output = ""
    requestCounter = 1

    for request in requests:
        formattedCanteen = MainMenu.canteenDict[request["canteen"]]
        requestID = request["RequestID"]
        # The first 16 characters of the requestID is the unix timestamp of the request.
        # Only use 10 because we only care about accuracy to the second.
        unixTimestamp = float(requestID[:10])
        username = request["requester_user_name"]
        chat_id = request["requester_chat_id"]
        food = request["food"]
        tip_amount = request["tip_amount"]

        formattedTimestamp = datetime.fromtimestamp(unixTimestamp).strftime("%d %b %y %I:%M %p")

        # Get rating of requester
        response = DynamoDB.userRatingsTable.get_item(
            Key = {"user_chat_id": chat_id}
        )

        logger.info("User Ratings Table get_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

        # print(response["Item"])
        good_received = 0
        bad_received = 0

        try:
            good_received = int(response["Item"]["good_received"])
        except KeyError:
            pass

        try:
            bad_received = int(response["Item"]["bad_received"])
        except KeyError:
            pass

        total = int(good_received) + int(bad_received)
        
        if (total != 0):
            ratingPercent = float(good_received) / float(total)
            ratingPercent = int(ratingPercent * 100)
        else:
            ratingPercent = 0


        formatted_output += f"""{requestCounter}) Requested on: {formattedTimestamp}
Username / Name: {username} | {ratingPercent}% \U0001F44D out of {total} ratings.
Canteen: {formattedCanteen}
Food: {food}
Tip Amount: ${tip_amount}

"""
        requestCounter += 1
    
    return formatted_output

# Filter requests from dynamoDB by the specified canteen
def filterRequests(selected_canteen):
    response = table.query(
        IndexName = "canteen-request_status-index",
        KeyConditionExpression = Key("canteen").eq(selected_canteen) & Key("request_status").eq("Available"))

    logger.info("DynamoDB query response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    requests = response["Items"]
    sorted_requests = sorted(requests, key=lambda x: x["RequestID"][:16])

    return sorted_requests

# Get item from table (not index)
def get_item(primaryKey):
    response = table.get_item(
        Key = {
            "RequestID": primaryKey
        }
    )

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
    logger.info("Role of '%s' (chat_id: '%s'): '%s'", update.effective_user.name, update.effective_user.id, update.callback_query.data)

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
    # Get the canteen selected from the fulfiller.
    selectedCanteen = update.callback_query.data

    # Let user know their selected canteen.
    await update.callback_query.message.reply_text(text=f"You have chosen {MainMenu.canteenDict[selectedCanteen]} as your canteen.")

    # Store the input of the fulfiller's canteen into user_data
    context.user_data[MainMenu.CANTEEN] = selectedCanteen

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their canteen
    logger.info("Fulfiller '%s' (chat_id: '%s') selected '%s' as their canteen.", update.effective_user.name, update.effective_user.id, update.callback_query.data)

    # Show list of available requests, filtered by the selected canteen.
    
    # 2. Using DyanmoDB
    sortedRequests = filterRequests(selectedCanteen)

    if len(sortedRequests) == 0:
        await update.callback_query.message.reply_text(f"There are no requests at {MainMenu.canteenDict[selectedCanteen]}. Use /start to fulfill an order again.")
        return ConversationHandler.END
    else:
        await update.callback_query.message.reply_text("Great! Here's the list of available requests for the canteen you're currently at: \n\n" +
                                                   processRequests(filterRequests(selectedCanteen)))

    await update.callback_query.message.reply_text("To fulfill a request, use the /fulfil command, followed by the request number. e.g. \"/fulfil 1\"")

    return MainMenu.FULFIL_REQUEST
