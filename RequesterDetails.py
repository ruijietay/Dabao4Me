from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import keys
import MenuHandler

bot_token = keys.bot_token

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

NAME, CANTEEN, FOOD, OFFER_PRICE = range(4)

async def requesterName(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requesterNameField = update.message.text

    # Store information about their name.
    user = update.message.from_user
    logger.info("Name of %s: %s", user.first_name, requesterNameField)

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

    await update.message.reply_text("Now, please select from the list of canteens below.", reply_markup=inlineCanteenTG)

    return CANTEEN

async def requesterCanteen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requesterCanteenField = update.callback_query

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await requesterCanteenField.answer()

    # Store information about their name.
    user = update.callback_query.from_user
    logger.info("Canteen of %s: %s", user.first_name, requesterCanteenField.message)

    await requesterCanteenField.message.reply_text("Great! Now, please state the food you'd like to order.")

    return FOOD

async def requesterFood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    requesterFoodField = update.message.text

    # Store information about their name.
    user = update.message.from_user
    logger.info("Food of %s: %s", user.first_name, requesterFoodField)

    await update.message.reply_text("Finally, please state the price you'd like to set for this request (excluding food prices)")

    return OFFER_PRICE

async def requesterPrice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requesterPriceField = update.message.text

    # Store information about their name.
    user = update.message.from_user
    logger.info("Food of %s: %s", user.first_name, requesterPriceField)

    return ConversationHandler.END