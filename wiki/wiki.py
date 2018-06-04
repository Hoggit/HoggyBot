import asyncio
import os
import aiohttp
import discord
import arrow
import json
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
        self.base_url = "https://wiki.hoggitworld.com"
        self.recent_changes_url = self.base_url + "/api.php?action=query&list=recentchanges&rcprop=user|title|timestamp&format=json&rctype=edit"
        self.last_wiki_check = arrow.utcnow()
        self.alerts = fileIO('data/iki/alerts.json', 'load')
        self.start_alerts()

    def start_alerts(self):
        channel = self.alerts["channel"]
        if channel:
            print("Starting alerting to channel: " + channel.name)
            asyncio.ensure_future(self.alert(channel))
        else:
            print("No alerts to start")

    def format_recent_changes(self, results):
        formatted = []
        for result in results:
            formatted_result = "{} by {} - {}".format(
                result["title"],
                result["user"],
                arrow.get(result["timestamp"]).humanize()
                )
            formatted.append(formatted_result)
        return formatted


    async def alert(self, channel: discord.Channel):
        await asyncio.sleep(600) #10 minutes
        timestamp = self.last_wiki_check.format('YYYY-MM-DDTHH:mm:ss')
        url = self.recent_changes_url + "&rcend=" + timestamp
        try:
            response = self.session.get(url)
            recent_changes = json.loads(await response.text())
            results = recent_changes["query"]["recentchanges"]
            formatted_results = self.format_recent_changes(results)
            self.bot.send_message(channel, formatted_results)
        except:
            print("Unexpected error sending wiki recent changes: " + sys.exc_info()[0])
        finally:
            if self.alerts["channel"] == channel:
                asyncio.ensure_future(self.alert(channel))

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
        links_used = []
        for ele in search_results:
            sr = ele.find("a")
            result = dict()
            result["title"] = sr["title"]
            result["link"] = self.base_url + sr["href"]
            if result["link"] not in links_used:
                parsed_results.append(result)
                links_used.append(result["link"])
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
            syn = query.split('>')[0].strip().lower()
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
        if query.lower() in self.synonyms.keys():
            query = self.synonyms[query.lower()]

        resp = await self.session.get(self.url(query))
        if HoggitWiki.was_redirect(resp):
            await self.bot_say_single_result(resp.url)
        else:
            await self.bot_say_search_results(resp)

    @wiki.command(name="alert", no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def _add_alert(self, chan: discord.Channel):
        """
        Configures alerts for the hoggit wiki to be sent to the given channel.

        `channel` must be a channel that the bot can send messages to
        """
        self.alerts["channel"] = chan
        self.start_alerts()

def setup(bot):
    if not os.path.exists("data/wiki"):
        print("Creating data/wiki folder...")
        os.makedirs("data/wiki")

    f = "data/wiki/synonyms.json"
    if not fileIO(f, "check"):
        print("Creating empty synonyms.json...")
        fileIO(f, "save", {})

    f = "data/wiki/alerts.json"
    if not fileIO(f, "check"):
        print("Creating empty alerts.json...")
        fileIO(f, "save", {})

    bot.add_cog(HoggitWiki(bot))
