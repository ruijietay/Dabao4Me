# Code that prompts the users with menu for them to select the appropriate choices when using the application.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import RequesterDetails
import FulfillerDetails
import MatchingUsers
import configparser

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

RESTART, ROLE, CANTEEN, FOOD, OFFER_PRICE, AWAIT_FULFILLER, REQUESTS, FULFILL_REQUEST, FULFILLER_IN_CONVO, REQUEST_CHOSEN = range(10)

available_requests = []

canteenDict = {
    "deck": "The Deck",
    "frontier": "Frontier",
    "fine_foods": "Fine Foods",
    "flavours": "Flavours @ Utown",
    "technoedge": "TechnoEdge",
    "pgpr": "PGPR"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Define the menu using a 2D array.
    inlineMenu = [
        [InlineKeyboardButton("Request an order", callback_data="requester")],
        [InlineKeyboardButton("Fulfil an order", callback_data="fulfiller")],
    ]

    # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
    inlineMenuTG = InlineKeyboardMarkup(inlineMenu)

    await update.message.reply_text("Welcome to Dabao4Me! What would you like to do today?:", reply_markup=inlineMenuTG)

    return ROLE


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command. Send /start to begin using the bot.")


# Method to cancel current transaction
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Current operation cancelled.")
    # Store information about their name.
    user = update.message.from_user
    logger.info("%s cancelled a transaction.", user.first_name)

    return ConversationHandler.END


# If user tries to cancel outside of a transaction, send a slightly more helpful response
async def invalidCancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="There is no ongoing operation to cancel.")


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    requester_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(RequesterDetails.promptCanteen, pattern = "requester")],
        states  = {
            CANTEEN: [CallbackQueryHandler(RequesterDetails.selectCanteen)],
            FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)],
            AWAIT_FULFILLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.awaitFulfiller)]
        },
        fallbacks = [CommandHandler("cancel", cancel)],
        map_to_parent= {
            RequesterDetails.ENDRequesterConv : ConversationHandler.END
        }
    )

    fulfiller_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(FulfillerDetails.promptCanteen , pattern = "fulfiller")],
        states = {
            CANTEEN: [CallbackQueryHandler(FulfillerDetails.selectCanteen)],
            FULFILL_REQUEST: [CommandHandler("fulfill", MatchingUsers.fulfillRequest)],
            FULFILLER_IN_CONVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardFulfillerMsg)]
        },
        fallbacks = [CommandHandler("cancel", cancel)],
        map_to_parent= {
            FulfillerDetails.ENDFulfillerConv : ConversationHandler.END
        }
    )

    # List of handlers that the user can trigger based on their input.
    role_handlers = [
        requester_conv,
        fulfiller_conv
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
