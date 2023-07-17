from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import DynamoDB
import MainMenu
import logging

####################################### Parameters ###########################################

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

GOOD = 1
BAD = 0

####################################### Helper Functions #####################################
def updateUserRatings(giver, receiver, rating):
    #TODO: update the counts of good and bad reviews given and received for the giver and receiver in a new reviews table
    return

####################################### Main Functions #######################################

async def inputUserRating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #TODO: prompt thumbs up/down emoji for user to rate
    return 