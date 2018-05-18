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
        return "http://wiki-beta.hoggitworld.com/index.php?title=Special%3ASearch&search={}&go=Go".format(search)

    def fetch(self, session, url):
        return session.get(url)

    def was_redirect(self, resp):
        print("==============================================")
        print(resp)
        print("==============================================")
        print(resp.status)
        print("++++++++++++++++++++++++++++++++++++++++++++++")
        print(resp.history)
        print("----------------------------------------------")
        return len(resp.history) > 0

    async def bot_say_single_result(self, result_url):
        message = result_url
        print("Sending message: {}".format(message))
        await self.bot.say(message)


    async def bot_say_multiple_results(self, response):
        message = "Got multiple results. Parsing coming soon"
        print("Multiple results")
        await self.bot.say(message)

    @commands.command()
    async def wiki(self, search_text):
        resp = await self.session.get(self.url(search_text))
        if (self.was_redirect(resp)):
            await self.bot_say_single_result(resp.url)
        else:
            await self.bot_say_multiple_results(resp)

def setup(bot):
    bot.add_cog(HoggitWiki(bot))
