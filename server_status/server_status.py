import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from .utils import checks
from .utils.dataIO import dataIO
import json
import aiohttp
import os
import arrow
from bs4 import BeautifulSoup

class ErrorGettingStatus(Exception):
    def __init__(self, statusCode):
        self.status=statusCode

class ServerHealth():
    """
    Returns a ServerHealth with a health status string indicating "Online", "Unhealthy", "Offline"
    and a `color` for use in graphics.
    Green - Online
    Orange - Unhealthy
    Red - Offline
    """

    def __init__(self, updateTime):
        self.status = determine_status(updateTime)
        self.color = self.determine_color(self.status)


    def determine_status(self, updateTime):
        now = arrow.utcnow()
        status = "Online"
        if (updateTime < now.shift(minutes=-5)):
            status = "Unhealthy"
        if (updateTime < now.shift(minutes=-10)):
            status = "Offline"
        return status


    def determine_color(self, status):
        if (status == "Online"):
            return 0x05e400
        if (status == "Unhealthy"):
            return 0xFF9700
        return 0xFF0000


class DCSServerStatus:
    """
    Returns the status of your DCS server
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.key_file = "data/server_status/server.json"
        self.key_data = dataIO.load_json(self.key_file)
        self.base_url = "http://status.hoggitworld.com/"

    def store_key(self, key):
        self.key_data = key
        dataIO.save_json(self.key_file, self.key_data)


    async def get_status(self):
        url = self.base_url + self.key_data["key"]
        resp = await self.session.get(url)
        if (resp.status != 200):
            raise ErrorGettingStatus()
        status = json.loads(await resp.text())
        return status

    def determine_health(self, status):
        last_update = arrow.get(status["updateTime"])
        return ServerHealth(last_update)

    def embedMessage(self, status):
        health = self.determine_health(status)
        embed=discord.Embed(color=health.color)
        embed.set_author(name=status["serverName"], icon_url="https://i.imgur.com/KEd7OQJ.png")
        embed.set_thumbnail(url="https://i.imgur.com/KEd7OQJ.png")
        embed.add_field(name="Status", value=health.status, inline=False)
        embed.add_field(name="Players", value="{}/{}".format(status["players"], status["maxPlayers"]), inline=False)
        #Omit the map until we can get it.
        #embed.add_field(name="Map", value="{}".format(status["serverName"]), inline=True)
        embed.set_footer(text="Brought to you by Hoggit")
        return embed


    @commands.group(pass_context=True, aliases=["server"])
    async def server_status(self, ctx):
        if ctx.invoked_subcommand is None:
            if (self.key_data == {} or self.key_data["key"] == ''):
                await self.bot.say("Configure the key first bud")
            else:
                try:
                    status = await self.get_status()
                    message = self.embedMessage(status)
                    await self.bot.say(embed=message)
                except ErrorGettingStatus as e:
                    await self.bot.say("Can't get status right now. Got {}".format(e.status))

    @server_status.command()
    @checks.mod_or_permissions(manage_server=True)
    async def key(self, *, text = ""):
        key = {}
        key["key"] = text
        self.store_key(key)
        await self.bot.say("Updated Key to {}".format(key["key"]))

def check_folders():
    if not os.path.exists("data/server_status"):
        print("Creating the server_status folder")
        os.makedirs("data/server_status")

def check_file():
    f = "data/server_status/server.json"
    if not dataIO.is_valid_json(f):
        print("Creating the server file to hold your api key...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_file()
    bot.add_cog(DCSServerStatus(bot))
