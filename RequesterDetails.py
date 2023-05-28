from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from datetime import datetime

import logging
import MainMenu
import boto3
import configparser

# Create config parser and read config file
config = configparser.ConfigParser()
config.read("config.ini")


# Load bot token
bot_token = config["bot_keys"]["test_bot_token"]

# The name of our table in DynamoDB
tableName = "Dabao4Me_Requests"

# Create resource object to access DynamoDB
db = boto3.resource('dynamodb', 
                    region_name = config["dynamodb"]["region_name"], 
                    aws_access_key_id = config["dynamodb"]["aws_access_key_id"],
                    aws_secret_access_key = config["dynamodb"]["aws_secret_access_key"])

# Create table object with specified table name
table = db.Table(tableName)

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

NAME, CANTEEN, FOOD, OFFER_PRICE, ROLE = range(5)

# Define ConversationHandler.END in another variable for clarity.
ENDRequesterConv = ConversationHandler.END

# async def getDetails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     # Various function calls to get relevant details.
#     if (update.callback_query.data == "requester"):
#         # conv_handler_req = ConversationHandler(entry_points=[MessageHandler("requester", requesterName)],
#         #                                        states={
#         #                                            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, requesterName)],
#         #                                            CANTEEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, requesterCanteen)],
#         #                                            FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, requesterFood)],
#         #                                            OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, requesterPrice)],
#         #                                        },
#         #                                        fallbacks=MenuHandler.unknown)

#         await update.message.reply_text("Alright! Now, please state your name.")

#         requesterNameField = update.message.text

#         # Store information about their name.
#         user = update.message.from_user
#         logger.info("Name of %s: %s", user.first_name, requesterNameField)

#         return NAME
        
# async def requesterName(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     requesterNameField = update.message.text

#     # Store information about their name.
#     user = update.message.from_user
#     logger.info("Name of %s: %s", user.first_name, requesterNameField)

#     # Define the canteens using a 2D array.
#     inlineCanteen = [
#         [InlineKeyboardButton("The Deck", callback_data="deck")],
#         [InlineKeyboardButton("Frontier", callback_data="frontier")],
#         [InlineKeyboardButton("Fine Foods", callback_data="fine_foods")],
#         [InlineKeyboardButton("Flavours @ Utown", callback_data="flavours")],
#         [InlineKeyboardButton("TechnoEdge", callback_data="technoedge")],
#         [InlineKeyboardButton("PGPR", callback_data="pgpr")],
#     ]


#     # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
#     inlineCanteenTG = InlineKeyboardMarkup(inlineCanteen)

#     await update.message.reply_text("Now, please select from the list of canteens below.", reply_markup=inlineCanteenTG)

#     return CANTEEN

async def promptCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the role selected from the user.
    roleSelected = update.callback_query.data

    # Store the input of the user's role into user_data.
    context.user_data[ROLE] = roleSelected

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their role.
    user = update.callback_query.from_user
    logger.info("Role of %s: %s", user.first_name, update.callback_query.message)

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
    # Get the canteen selected from the requester.
    canteenSelected = update.callback_query.data

    # Store the input of the requester's canteen into user_data
    context.user_data[CANTEEN] = canteenSelected

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await update.callback_query.answer()

    # Store information about their name.
    user = update.callback_query.from_user
    logger.info("Requester %s selected %s as their canteen.", user.first_name, update.callback_query.message)  # why is this not update.callback_query.data? (or canteenSelected for that matter)

    await update.callback_query.message.reply_text("Great! Now, please state the food you'd like to order.")

    return FOOD

async def requesterFood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    # Get the food requested from the requester.
    requesterFood = update.message.text

    # Store the input of the requester's choice of food into user_data
    context.user_data[FOOD] = requesterFood

    # Store information about their name.
    user = update.message.from_user
    logger.info("Food of %s: %s", user.first_name, requesterFood)

    await update.message.reply_text("Finally, how much would you like to tip the fulfiller for your request? (excluding food prices)")

    return OFFER_PRICE

async def requesterPrice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the tipping amount from the requester.
    requesterPrice = update.message.text

    # Store the input of the requester's tipping amount into user_data.
    context.user_data[OFFER_PRICE] = requesterPrice

    # Store information about their name.
    user = update.message.from_user
    logger.info("Food of %s: %s", user.first_name, requesterPrice)

    # Put details of request into data structure.
    MainMenu.available_requests.append({
        # Potential Issue: Not every telegram account has a username.
        "username" : update.effective_user.name,
        "canteen" : context.user_data[CANTEEN],
        "food" : context.user_data[FOOD],
        "tip_amount" : context.user_data[OFFER_PRICE]
    })




    # Columns in our DynamoDB table
    columns = ["RequestID", "requester_telegram_username", "canteen", "food", "tip_amount"]

    # RequestID which consists of time + telegram username
    requestID = "{}{}".format(datetime.now().timestamp(), update.effective_user.name)

    # Function to put item in table
    def put_item(requestID, requester_telegram_username, canteen, food, tip_amount):
        data = {
            columns[0]: requestID,
            columns[1]: requester_telegram_username,
            columns[2]: canteen,
            columns[3]: food,
            columns[4]: tip_amount
        }

        response = table.put_item(Item = data)

        logger.info("DynamoDB put_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    # Actually put item in table
    put_item(requestID, 
             update.effective_user.name, 
             context.user_data[CANTEEN], 
             context.user_data[FOOD], 
             context.user_data[OFFER_PRICE])




    await update.message.reply_text(parse_mode="MarkdownV2", 
                                    text="Request placed\! \n__*Summary*__ " + 
                                    "\nCanteen: " + MainMenu.canteenDict[context.user_data[CANTEEN]] + 
                                    "\nFood: " + context.user_data[FOOD] +
                                    "\nTip Amount: SGD$" + context.user_data[OFFER_PRICE])
    
    await update.message.reply_text("To restart, send /start again.")


    return ENDRequesterConv
