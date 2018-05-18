import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
import aiohttp
from bs4 import BeautifulSoup

class HoggitWiki:
    """
    Search the hoggit wiki
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.base_url = "http://wiki-beta.hoggitworld.com"

    def url(self, search):
        return self.base_url + "/index.php?title=Special%3ASearch&search={}&go=Go".format(search)

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

    async def parse_results(self, response):
        soup = BeautifulSoup(await response.text())
        search_results = soup.find_all("div", "mw-search-result-heading")
        results_parsed = 0
        max_results = 3
        parsed_results = []
        for ele in search_results:
            sr = ele.find("a")
            result = {}
            result["title"] = sr["title"]
            result["link"] = self.base_url + sr["href"]
            parsed_results.append(result)
            results_parsed+=1
            if (results_parsed >= max_results):
                break

        return parsed_results


    def format_results(self, results):
        formatted_results = []
        for result in results:
            formatted = "{}: <{}>".format(result["title"], result["link"])
            formatted_results.append(formatted)
        return formatted_results


    async def bot_say_multiple_results(self, response):
        results = await self.parse_results(response)
        formatted_results = self.format_results(results)
        message = "I couldn't find an exact match. But here's some suggestions:\n" + "\n".join(str(x) for x in formatted_results)
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
