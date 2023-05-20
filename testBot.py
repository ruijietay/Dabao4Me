import asyncio
import telegram


async def main():
    bot = telegram.Bot("5937019735:AAGHDxML3WPmbSuIw4NxPxeww0UP5Wezvw0")
    async with bot:
        print(await bot.get_me())


if __name__ == '__main__':
    asyncio.run(main())