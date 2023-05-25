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

available_requests = {}

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


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    # # Set up second level ConversationHandler (adding a person)
    # add_member_conv = ConversationHandler(
    #     entry_points=[CallbackQueryHandler(select_level, pattern="^" + str(ADDING_MEMBER) + "$")],
    #     states={
    #         SELECTING_LEVEL: [
    #             CallbackQueryHandler(select_gender, pattern=f"^{PARENTS}$|^{CHILDREN}$")
    #         ],
    #         SELECTING_GENDER: [description_conv],
    #     },
    #     fallbacks=[
    #         CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
    #         CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
    #         CommandHandler("stop", stop_nested),
    #     ],
    #     map_to_parent={
    #         # After showing data return to top level menu
    #         SHOWING: SHOWING,
    #         # Return to top level menu
    #         END: SELECTING_ACTION,
    #         # End conversation altogether
    #         STOPPING: END,
    #     },
    # )

    requester_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(RequesterDetails.promptCanteen, pattern = "requester")],
        states  = {
            RequesterDetails.CANTEEN: [CallbackQueryHandler(RequesterDetails.requesterCanteen)],
            RequesterDetails.FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            RequesterDetails.OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)]
        },
        fallbacks = [CommandHandler("cancel", unknown)]
    )

    fulfiller_conv = ConversationHandler(
        entry_points = [CallbackQueryHandler(FulfillerDetails.promptCanteen , pattern = "fulfiller")],
        states = {
            FulfillerDetails.CANTEEN: [CallbackQueryHandler(FulfillerDetails.fulfillerCanteen)],
            FulfillerDetails.REQUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, FulfillerDetails.availableRequests)],
        },
        fallbacks = [CommandHandler("cancel", unknown)]
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

            # RequesterDetails.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterName)],
            # RequesterDetails.CANTEEN: [CallbackQueryHandler(RequesterDetails.requesterCanteen)],
            
        },
        fallbacks=[CommandHandler("cancel", unknown)])
    
    application.add_handler(conv_handler_req)
    application.add_handler(MessageHandler(filters.TEXT, unknown))

    
    

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
