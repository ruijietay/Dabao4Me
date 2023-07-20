from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import DynamoDB
import MainMenu
import logging
import FulfillerDetails

####################################### Parameters ###########################################

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define GOOD and BAD for easier readability
GOOD = 1
BAD = 0

# Define the options using a 2D array.
userRatingOptions = [
    [InlineKeyboardButton("\U0001F44D", callback_data = GOOD)],
    [InlineKeyboardButton("\U0001F44E", callback_data = BAD)]
]

# Transform the 2D array into an actual inline keyboard (IK) that can be interpreted by Telegram.
userRatingOptionsIK = InlineKeyboardMarkup(userRatingOptions)

####################################### Helper Functions #####################################
def updateRatingTable(giver_chat_id, receiver_chat_id, rating):
    # If GOOD rating given
    if (int(rating) == GOOD):
        # Increment giver's good_given
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": str(giver_chat_id)},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD good_given :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

        # Increment receiver's good_received
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": str(receiver_chat_id)},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD good_received :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

    if (int(rating) == BAD):
        # Increment giver's bad_given
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": str(giver_chat_id)},
            ExpressionAttributeValues = {":inc": 1},
            UpdateExpression = "ADD bad_given :inc"
        )

        logger.info("DynamoDB update_item response: %s", response["ResponseMetadata"]["HTTPStatusCode"])

        # Increment receiver's bad_received
        response = DynamoDB.userRatingsTable.update_item(
            Key = {"user_chat_id": str(receiver_chat_id)},
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
    await update.callback_query.answer()

    # Get the rating input by the user
    ratingInput = update.callback_query.data

    # Query the DB for the request made.
    response = FulfillerDetails.get_item(context.user_data[MainMenu.REQUEST_MADE]["RequestID"])
    # Log DynamoDB response
    logger.info("DynamoDB get_item response for RequestID '%s': '%s'", context.user_data[MainMenu.REQUEST_MADE]["RequestID"], response["ResponseMetadata"]["HTTPStatusCode"])

    # Get the request the requester has put out.
    request = response["Item"]

    # TODO: obtain the chat IDs of the fulfiller and requester, and call updateRatingTable() accordingly

    user_chat_id = update.effective_chat.id

    requester_chat_id = request['requester_chat_id']
    fulfiller_chat_id = request['fulfiller_chat_id']

    giver_chat_id = user_chat_id
    receiver_chat_id = "PLACEHOLDER"

    if (int(user_chat_id) == int(fulfiller_chat_id)):
        receiver_chat_id = requester_chat_id
    else:
        receiver_chat_id = fulfiller_chat_id


    # Updates the table that stores user ratings
    updateRatingTable(giver_chat_id, receiver_chat_id, ratingInput)

    await context.bot.send_message(chat_id = user_chat_id, text = "Rating submitted!")

    return ConversationHandler.END