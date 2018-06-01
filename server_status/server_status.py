import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from .utils import checks
from .utils.dataIO import dataIO
import json
import aiohttp
import os
from bs4 import BeautifulSoup

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


    def get_status(self):
        url = self.base_url + self.key_data.key
        resp = self.session.get(url)
        status = json.load(resp.text())
        return status

    @commands.group(name="server", pass_context=True)
    async def server(self, ctx):
        if ctx.invoked_subcommand is None:
            if (self.key_data == {}):
                await self.bot.say("Configure the key first bud")
            else:
                status = self.get_status()
                await self.bot.say("Would look up status if I worked... Thanks")

    @commands.group(name="server")
    @checks.mod_or_permissions(manage_server=True)
    async def key(self, *, text = ""):
        key = {}
        key["key"] = text
        self.store_key(key)
        await self.bot.say("Updated Key to {}".format(key.key))

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
