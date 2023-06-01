from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import MainMenu
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

# Stages of the conversation
CANTEEN, REQUESTS, ROLE, RESTART = range(4)

# Define ConversationHandler.END in another variable for clarity.
ENDFulfillerConv = ConversationHandler.END

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


####################################### Helper Functions #######################################

# Get and format requests from python storage 
def processRequests(available_requests, selected_canteen):

    formatted_output = ""
    for requests in available_requests:
        canteen = requests["canteen"]
        
        if canteen == selected_canteen:
            formattedCanteen = MainMenu.canteenDict[selected_canteen]
            username = requests["username"]
            food = requests["food"]
            tip_amount = requests["tip_amount"]

            formatted_output += f"Username: {username}\nCanteen: {formattedCanteen}\nFood: {food}\nTip Amount: SGD${tip_amount}\n\n"
    
    return formatted_output

# Get and format requests from DynamoDB
def processRequests(canteen):
    formatted_output = ""

    response = table.query(IndexName = 'canteen-index',
                           KeyConditionExpression = Key('canteen').eq(canteen))
    
    logger.info("DynamoDB query response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    for request in response["Items"]:
        formattedCanteen = MainMenu.canteenDict[canteen]
        requestID = request["RequestID"]
        unixTimestamp = float(requestID[:17])
        username = request["requester_telegram_username"]
        food = request["food"]
        tip_amount = request["tip_amount"]

        formattedTimestamp = datetime.fromtimestamp(unixTimestamp).strftime('%d %b %y  %I:%M %p')

        formatted_output += f"""Requested on: {formattedTimestamp}
Username: {username}
Canteen: {formattedCanteen}
Food: {food}
Tip Amount: ${tip_amount}

"""
    
    return formatted_output

####################################### Main Functions #######################################

async def promptCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the role selected from the user.
    roleSelected = update.callback_query.data

    # Store the input of the user's role into user_data.
    context.user_data[ROLE] = roleSelected

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

    return CANTEEN

async def selectCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the canteen selected from the fulfiller.
    selectedCanteen = update.callback_query.data

    # Store the input of the fulfiller's canteen into user_data
    context.user_data[CANTEEN] = selectedCanteen

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their name.
    user = update.callback_query.from_user
    logger.info("Canteen of %s: %s", user.first_name, update.callback_query.data)

    # Show list of available requests, filtered by the selected canteen.
    
    # await update.callback_query.message.reply_text("Great! Here's the list of available requests for the canteen you're currently at: \n\n" + processRequests(MainMenu.available_requests, selectedCanteen))
    await update.callback_query.message.reply_text("Great! Here's the list of available requests for the canteen you're currently at: \n\n" + processRequests(selectedCanteen))

    await update.callback_query.message.reply_text("To restart, send /start again.")

    return ENDFulfillerConv