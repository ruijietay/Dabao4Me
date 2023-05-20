import asyncio
import telegram


async def main():
    bot = telegram.Bot("5937019735:AAGHDxML3WPmbSuIw4NxPxeww0UP5Wezvw0")
    async with bot:
        print((await bot.get_updates())[0].message.from_user.id)
        await bot.send_message(text="Hi", chat_id=(await bot.get_updates())[0].message.from_user.id)


if __name__ == '__main__':
    asyncio.run(main())

#update to test branch