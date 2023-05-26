# Code that prompts the users with menu for them to select the appropriate choices when using the application.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import keys
import RequesterDetails
import FulfillerDetails

bot_token = keys.bot_token

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

ROLE = range(1)

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
        [InlineKeyboardButton("Requester", callback_data="requester")],
        [InlineKeyboardButton("Fulfiller", callback_data="fulfiller")],
    ]

    # Transform the 2D array into an actual inline keyboard that can be interpreted by Telegram.
    inlineMenuTG = InlineKeyboardMarkup(inlineMenu)

    await update.message.reply_text("Welcome to Dabao4Me! Please choose your role:", reply_markup=inlineMenuTG)

    return ROLE


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I don't understand what you've said.")


# Method to cancel current transaction
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Current transaction cancelled.")
    # Store information about their name.
    user = update.message.from_user
    logger.info("%s cancelled a transaction.", user.first_name)

    return ConversationHandler.END


# If user tries to cancel outside of a transaction, send a slightly more helpful response
async def invalidCancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="There is no ongoing transaction to cancel.")


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    requester_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(RequesterDetails.promptCanteen, pattern = "requester")],
        states  = {
            RequesterDetails.CANTEEN: [CallbackQueryHandler(RequesterDetails.requesterCanteen)],
            RequesterDetails.FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            RequesterDetails.OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)]
        },
        fallbacks = [CommandHandler("cancel", cancel)]
    )

    fulfiller_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(FulfillerDetails.promptCanteen , pattern = "fulfiller")],
        states = {
            FulfillerDetails.CANTEEN: [CallbackQueryHandler(FulfillerDetails.fulfillerCanteen)],
            FulfillerDetails.REQUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, FulfillerDetails.availableRequests)],
        },
        fallbacks = [CommandHandler("cancel", cancel)]
    )

    # List of handlers that the user can trigger based on their input.
    role_handlers = [
        requester_conv,
        fulfiller_conv
    ]

    conv_handler_req = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: role_handlers
        },
        fallbacks=[CommandHandler("cancel", cancel)])
    
    application.add_handler(conv_handler_req)
    application.add_handler(CommandHandler("cancel", invalidCancel))
    application.add_handler(MessageHandler(filters.TEXT, unknown))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
