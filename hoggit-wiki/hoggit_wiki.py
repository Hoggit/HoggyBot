import discord
from discord.ext import commands
import aiohttp

class HoggitWiki:
    """
    Search the hoggit wiki
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def url(self, search):
        return "http://wiki-beta.hoggitworld.com/index.php?search={}&title=Special%3ASearch&profile=default&fulltext=1".format(search)

    def fetch(self, session, url):
        async with session.get(url) as response:
            return response

    def was_redirect(self, response):
        return len(resp.history) > 0

    def bot_say_single_result(self, result_url):
        message = result_url
        await self.bot.say(message)


    def bot_say_multiple_results(self, response):
        message = "Got multiple results. Parsing coming soon"
        await self.bot.say(message)

    @commands.command()
    async def wiki(self, search_text):
        resp = await fetch(self.session, url)
        if (was_redirect(resp)):
            bot_say_single_result(resp.history[0].url)
        else:
            bot_say_multiple_results(resp)
