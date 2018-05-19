import os
import aiohttp
from bs4 import BeautifulSoup
from .utils.chat_formatting import pagify
from .utils import checks
from .utils.dataIO import fileIO
from discord.ext import commands


class HoggitWiki:
    """
    Search the hoggit wiki
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

        self.synonyms = fileIO('data/wiki/synonyms.json', 'load')
        self.base_url = "http://wiki.hoggitworld.com"

    def url(self, search):
        return self.base_url + "/index.php?title=Special%3ASearch&search={}&go=Go".format(search)

    @staticmethod
    def was_redirect(resp):
        print("==============================================")
        print(resp)
        print("==============================================")
        print(resp.status)
        print("++++++++++++++++++++++++++++++++++++++++++++++")
        print(resp.history)
        print("----------------------------------------------")
        return len(resp.history) > 0

    async def bot_say_single_result(self, result_url):
        message = "<{}>".format(result_url)
        await self.bot.say(message)

    async def parse_results(self, response):
        soup = BeautifulSoup(await response.text())
        search_results = soup.find_all("div", "mw-search-result-heading")
        results_parsed = 0
        max_results = 3
        parsed_results = []
        for ele in search_results:
            sr = ele.find("a")
            result = dict()
            result["title"] = sr["title"]
            result["link"] = self.base_url + sr["href"]
            parsed_results.append(result)
            results_parsed += 1
            if results_parsed >= max_results:
                break

        return parsed_results

    @staticmethod
    def format_results(results):
        formatted_results = []
        for result in results:
            formatted = "{}: <{}>".format(result["title"], result["link"])
            formatted_results.append(formatted)
        return formatted_results

    async def bot_say_search_results(self, response):
        results = await self.parse_results(response)
        formatted_results = HoggitWiki.format_results(results)
        if len(formatted_results) == 0:
            message = "Could not find any results :("
        else:
            message = "I couldn't find an exact match. But here's some suggestions:\n{0}\n".format(
                    "\n".join(str(x) for x in formatted_results))
            await self.bot.say(message)

    @commands.command()
    @checks.mod_or_permissions(manage_server=True)
    async def wiki_syn(self, command, *args):
        query = ' '.join(args)
        if command == "add":
            syn = query.split('>')[0].strip()
            target = query.split('>')[1].strip()
            self.synonyms[syn] = target

            fileIO('data/wiki/synonyms.json', 'save', self.synonyms)
            await self.bot.say("Synonym {0} -> {1} added".format(syn, target))

        if command == "remove":
            syn = query.split('>')[0].strip().lower()
            if syn not in self.synonyms.keys():
                await self.bot.say("Synonym {0} not found.".format(syn))
            else:
                target = self.synonyms[syn]
                del self.synonyms[syn]
                fileIO('data/wiki/synonyms.json', 'save', self.synonyms)
                await self.bot.say("Synonym {0} -> {1} removed".format(syn, target))

    @commands.command()
    async def wiki(self, *search_text):
        query = ' '.join(search_text)
        if query in self.synonyms.keys():
            query = self.synonyms[query]

        resp = await self.session.get(self.url(query))
        if HoggitWiki.was_redirect(resp):
            await self.bot_say_single_result(resp.url)
        else:
            await self.bot_say_search_results(resp)


def setup(bot):
    if not os.path.exists("data/wiki"):
        print("Creating data/wiki folder...")
        os.makedirs("data/wiki")

    f = "data/wiki/synonyms.json"
    if not fileIO(f, "check"):
        print("Creating empty synonyms.json...")
        fileIO(f, "save", {})

    bot.add_cog(HoggitWiki(bot))
