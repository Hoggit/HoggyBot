import asyncio
import os
import aiohttp
import discord
import arrow
import json
import sys
from bs4 import BeautifulSoup
from .utils.chat_formatting import pagify
from .utils import checks
from .utils.dataIO import fileIO, dataIO
from discord.ext import commands
from urllib.parse import urlencode


class HoggitWiki:
    """
    Search the hoggit wiki
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.killSwitch = False
        self.synonyms = fileIO('data/wiki/synonyms.json', 'load')
        self.base_url = "https://wiki.hoggitworld.com"
        self.recent_changes_url = self.base_url + "/api.php?action=query&list=recentchanges&rcprop=user|title|timestamp&format=json&rctype=edit"
        self.last_wiki_check = arrow.utcnow()
        self.alerts = fileIO('data/wiki/alerts.json', 'load')
        asyncio.ensure_future(self.start_alerts())


    def __unload(self):
        #Needed to not reschedule the next check.
        self.killswitch = True

    async def start_alerts(self):
        await self.bot.wait_until_ready()
        if "channel" not in self.alerts:
            print("Wiki: No alerts to start")
        else:
            channel = self.alerts["channel"]
            print("Wiki: Starting alerting to channel: " + self.bot.get_channel(channel).name)
            asyncio.ensure_future(self._alert(channel))

    def format_recent_changes(self, results):
        embed=discord.Embed(title="Wiki changes since {}".format(self.last_wiki_check.humanize()))
        results_length = len(results)
        trimmed_results = results[:5]
        for result in trimmed_results:
            url = self.base_url + "/view/" + urlencode(result["title"])
            print("Wiki: Setting url for field: " + url)
            embed.add_field(
                    name=result["title"],
                    value="{} - {}".format(result["user"], arrow.get(result["timestamp"]).humanize()),
                    url=url)

        if results_length > 5:
            embed.set_footer(text="And {} more changes omitted".format(results.length - 5))
        return embed


    async def _alert(self, chan_id):
        await asyncio.sleep(3600) #1 hour
        if self.killSwitch:
            return
        timestamp = self.last_wiki_check.format('YYYY-MM-DDTHH:mm:ss')
        url = self.recent_changes_url + "&rcend=" + timestamp
        try:
            response = await self.session.get(url)
            recent_changes = json.loads(await response.text())
            results = recent_changes["query"]["recentchanges"]
            if not results:
                print("Wiki-Alerts: Checked wiki but no updates. Continuing...")
            else:
                formatted_results = self.format_recent_changes(results)
                self.last_wiki_check = arrow.utcnow()
                channel = self.bot.get_channel(chan_id)
                await self.bot.send_message(channel, embed=formatted_results)
        except Exception as e:
            print("Wiki: Unexpected error sending wiki recent changes: " + e)
        finally:
            if self.alerts["channel"] == chan_id and not self.killSwitch:
                asyncio.ensure_future(self._alert(chan_id))

    def url(self, search):
        return self.base_url + "/index.php?title=Special%3ASearch&search={}&go=Go".format(search)

    @staticmethod
    def was_redirect(resp):
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

    @commands.command(pass_context=True)
    async def wiki(self, ctx, *search_text):
        print("Wiki: Invoked subcommand? {}".format(ctx.invoked_subcommand))
        print("Wiki: subcommand? {}".format(ctx.subcommand_passed))
        if ctx.invoked_subcommand is None:
            query = ' '.join(search_text)
            if query.lower() in self.synonyms.keys():
                query = self.synonyms[query.lower()]

            resp = await self.session.get(self.url(query))
            if HoggitWiki.was_redirect(resp):
                await self.bot_say_single_result(resp.url)
            else:
                await self.bot_say_search_results(resp)

    @commands.command(name="embed-test")
    async def embed_test(self):
        embed=discord.Embed()
        embed.add_field(name="[F/A-18C](http://www.google.com)", value="Acidictadpole - 3 minutes ago", inline=False)
        await self.bot.say(embed=embed)

    @commands.command(name="wiki-alert")
    @checks.mod_or_permissions(manage_server=True)
    async def alert(self, chan: discord.Channel):
        """
        Configures alerts for the hoggit wiki to be sent to the given channel.

        `channel` must be a channel that the bot can send messages to
        """
        print("Wiki: New alert requested for channel {}".format(chan.name))
        self.alerts["channel"] = chan.id
        await self.start_alerts()
        dataIO.save_json('data/wiki/alerts.json', self.alerts)
        await self.bot.say("Started an alert for {}".format(chan.name))

def setup(bot):
    if not os.path.exists("data/wiki"):
        print("Wiki: Creating data/wiki folder...")
        os.makedirs("data/wiki")

    f = "data/wiki/synonyms.json"
    if not fileIO(f, "check"):
        print("Wiki: Creating empty synonyms.json...")
        fileIO(f, "save", {})

    f = "data/wiki/alerts.json"
    if not fileIO(f, "check"):
        print("Wiki: Creating empty alerts.json...")
        dataIO.save_json(f, {})

    bot.add_cog(HoggitWiki(bot))
