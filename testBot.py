import logging
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

## just testing branches again

# Function that runs when /start is received
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

# Function to echo user's message
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

# /caps command
async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

# Unknown command
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

if __name__ == '__main__':
    # Creates the bot Application
    application = ApplicationBuilder().token('5937019735:AAGHDxML3WPmbSuIw4NxPxeww0UP5Wezvw0').build()
    
    # Creates a CommandHandler that handles /start commands
    start_handler = CommandHandler('start', start)

    # Creates a MessageHandler that echoes the user's messages
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    # Creates CommandHandler that handles /caps commands
    caps_handler = CommandHandler('caps', caps)

    # MessageHandler that handles unknown commands
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    # Add handlers
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)
    application.add_handler(unknown_handler)

    application.run_polling()