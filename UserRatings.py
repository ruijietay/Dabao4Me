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

# Define GOOD and BAD for easier readability
GOOD = 1
BAD = 0

####################################### Helper Functions #####################################
def updateRatingTable(giver_chat_id, receiver_chat_id, rating):
    # If GOOD rating given
    if (rating == GOOD):
        # Increment giver's good_given
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": giver_chat_id},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD good_given :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

        # Increment receiver's good_received
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": receiver_chat_id},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD good_received :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    if (rating == BAD):
        # Increment giver's bad_given
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": giver_chat_id},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD bad_given :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

        # Increment receiver's good_received
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": receiver_chat_id},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD bad_received :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

####################################### Main Functions #######################################

async def inputUserRating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Define the options using a 2D array.
    userRatingOptions = [
        [InlineKeyboardButton("\U0001F44D", callback_data = GOOD)],
        [InlineKeyboardButton("\U0001F44E", callback_data = BAD)]
    ]

    # Transform the 2D array into an actual inline keyboard (IK) that can be interpreted by Telegram.
    userRatingOptionsIK = InlineKeyboardMarkup(userRatingOptions)

    # Prompt user to select a rating option
    await update.callback_query.message.reply_text("How would you rate your interaction with this user?", reply_markup = userRatingOptionsIK)

    return MainMenu.UPDATE_RATINGS

async def updateUserRatings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the rating input by the user
    ratingInput = update.callback_query.data

    # TODO: obtain the chat IDs of the fulfiller and requester, and call updateRatingTable() accordingly

    giver_chat_id = "PLACEHOLDER"
    receiver_chat_id = "PLACEHOLDER"

    # Updates the table that stores user ratings
    updateRatingTable(giver_chat_id, receiver_chat_id, ratingInput)

    return ConversationHandler.END