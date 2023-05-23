# Code that prompts the users with menu for them to select the appropriate choices when using the application.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

import logging
import keys
import RequesterDetails

bot_token = keys.bot_token

# Enable logging
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

ROLE = range(1)

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

async def selectRole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    roleSelected = update.callback_query

    # Once the user clicks a button, we need to "answer" the CallbackQuery.
    await roleSelected.answer()

    # Store information about their role.
    user = update.callback_query.from_user
    logger.info("Role of %s: %s", user.first_name, roleSelected.data)

    await roleSelected.message.reply_text(text=f"You have chosen to be a {roleSelected.data}. "
                                   "Now, we need some details so we can match you with a potential fulfiller.")

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

    await roleSelected.message.reply_text("First off, please select a canteen:", reply_markup=inlineCanteenTG)
    
    return RequesterDetails.CANTEEN

# Fallback method if user sends unknown command or text
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

    conv_handler_req = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [CallbackQueryHandler(selectRole)],
            RequesterDetails.CANTEEN: [CallbackQueryHandler(RequesterDetails.requesterCanteen)],
            RequesterDetails.FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            RequesterDetails.OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)])
    
    application.add_handler(conv_handler_req)
    application.add_handler(CommandHandler("cancel", invalidCancel))
    application.add_handler(MessageHandler(filters.TEXT, unknown))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
