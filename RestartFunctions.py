from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, ApplicationHandlerStop

import MainMenu
import logging
import RequesterDetails
import FulfillerDetails
import MatchingUsers
import RestartFunctions
import ModifyOrder
import DynamoDB
import configparser


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

####################################### Main Functions #######################################

async def restartInModify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Since the user has used the "/start" command while modifying their request, we have to delete the current request in DynamoDB.
    RequestID = context.user_data[MainMenu.REQUEST_MADE]["RequestID"]
    response = DynamoDB.table.delete_item(Key = {"RequestID": RequestID})

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Current operation cancelled.")

    # Store information about their action.
    logger.info("'%s' (chat_id: '%s') restarted using the '/start' command while modifying their request.", update.effective_user.name, update.effective_chat.id)

    # Reset user_data
    context.user_data.clear()

    return ConversationHandler.END