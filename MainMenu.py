# Code that prompts the users with menu for them to select the appropriate choices when using the application.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, ApplicationHandlerStop

import logging
import RequesterDetails
import FulfillerDetails
import MatchingUsers
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

RESTART, SELECT_ORDER_TO_MODIFY, ROLE, CANTEEN, FOOD, OFFER_PRICE, AWAIT_FULFILLER, REQUEST_MADE, FULFIL_REQUEST, FULFILLER_IN_CONVO, REQUEST_CHOSEN, REQUESTER_IN_CONVO, DELETE_ORDER, EDIT_CANTEEN, EDIT_CANTEEN_PROMPT, EDIT_FOOD, EDIT_TIP, EDIT_ORDER, REQUESTER_CONFIRM, RATE_USER = range(20)

available_requests = []

canteenDict = {
    "deck": "The Deck",
    "frontier": "Frontier",
    "fine_foods": "Fine Foods",
    "flavours": "Flavours @ Utown",
    "technoedge": "TechnoEdge",
    "pgpr": "PGPR"
}

# Create table object
table = DynamoDB.table

####################################### Main Functions #######################################

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

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') sent an unknown command.", update.effective_user.name, update.effective_chat.id)

    return ConversationHandler.END


# Method to cancel current transaction
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Current operation cancelled.")

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') cancelled an operation.", update.effective_user.name, update.effective_chat.id)

    return ConversationHandler.END


# If user tries to cancel outside of a transaction, send a slightly more helpful response
async def invalidCancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="There is no ongoing operation to cancel.")

    # Store information about their action.
    user = update.message.from_user
    logger.info("'%s' (chat_id: '%s') sent an invalid '/cancel' command.", update.effective_user.name, update.effective_chat.id)

############################## Main Program Entry Point ##############################

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    ############################## Other Handlers ##############################

    modifyRequest_handler = ConversationHandler(
            entry_points = [
                CallbackQueryHandler(RequesterDetails.editCanteenPrompt, pattern = "editCanteen"),
                CallbackQueryHandler(RequesterDetails.editFoodPrompt, pattern = "editFood"),
                CallbackQueryHandler(RequesterDetails.editTipPrompt, pattern = "editTip")
            ],
            states = {
                EDIT_CANTEEN: [CallbackQueryHandler(RequesterDetails.editCanteen)],
                EDIT_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.editFood)],
                EDIT_TIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.editTip)]
            },
            fallbacks = [
                CommandHandler("cancel", cancel),
            ],
            map_to_parent = {
                RequesterDetails.END_EDITING : AWAIT_FULFILLER
            }
        )

    ############################## Requester Handlers ##############################

    requester_in_conv = ConversationHandler(
            entry_points = [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardRequesterMsg)],
            states = {
                REQUESTER_IN_CONVO: [CommandHandler("complete", MatchingUsers.requesterComplete), MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardRequesterMsg)],
            },
            fallbacks = [CommandHandler("end", MatchingUsers.requesterEndConv)],
            map_to_parent = {
                MatchingUsers.ENDConv : ConversationHandler.END
            }
        )

    requester_init = ConversationHandler(
        entry_points = [CallbackQueryHandler(RequesterDetails.promptCanteen, pattern = "requester")],
        states  = {
            CANTEEN: [CallbackQueryHandler(RequesterDetails.selectCanteen)],
            FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterFood)],
            OFFER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, RequesterDetails.requesterPrice)],
            # TODO: include the command for "end" through messagehandler filters so that it can be passed onto the next conversationhandler in requester_in_conv
            AWAIT_FULFILLER: [
                CommandHandler("end", MatchingUsers.requesterEndConv),
                CommandHandler("cancel", MatchingUsers.requesterCancelSearch),
                CommandHandler("edit", MatchingUsers.promptEditRequest),
                CommandHandler("complete", MatchingUsers.requesterComplete),
                MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.awaitFulfiller)
            ],
            REQUESTER_IN_CONVO: [requester_in_conv],
            EDIT_ORDER: [modifyRequest_handler]
        },
        fallbacks = [CommandHandler("cancel", cancel)],
        map_to_parent= {
            MatchingUsers.ENDRequesterConv : ConversationHandler.END
        }
    )

    ############################## Fulfiller Handlers ##############################
    fulfiller_in_conv = ConversationHandler(
            entry_points = [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardFulfillerMsg), CommandHandler("end", MatchingUsers.fulfillerEndConv)],
            states = {
                FULFILLER_IN_CONVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, MatchingUsers.forwardFulfillerMsg)]
            },
            fallbacks = [CommandHandler("end", MatchingUsers.fulfillerEndConv)],
            map_to_parent = {
                MatchingUsers.ENDConv : ConversationHandler.END
            }
        )

    fulfiller_init = ConversationHandler(
            entry_points = [CallbackQueryHandler(FulfillerDetails.promptCanteen , pattern = "fulfiller")],
            states = {
                CANTEEN: [CallbackQueryHandler(FulfillerDetails.selectCanteen)],
                FULFIL_REQUEST: [CommandHandler("fulfil", MatchingUsers.fulfilRequest)],
                FULFILLER_IN_CONVO: [fulfiller_in_conv]
            },
            fallbacks = [CommandHandler("cancel", cancel)],
            map_to_parent = {
                MatchingUsers.ENDFulfillerConv : ConversationHandler.END
            }
        )

    # List of handlers that the user can trigger based on their input.
    role_handlers = [
        requester_init,
        fulfiller_init,
        modifyRequest_handler
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states = {
            RESTART: [CommandHandler("start", start)],
            ROLE: role_handlers
        },
        fallbacks = [
            CommandHandler("cancel", cancel),
            CommandHandler("start", start)
            ],
        allow_reentry = True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("cancel", invalidCancel))
    application.add_handler(MessageHandler(filters.TEXT, unknown))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()