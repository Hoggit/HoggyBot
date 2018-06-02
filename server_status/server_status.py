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


    async def get_status(self):
        url = self.base_url + self.key_data["key"]
        resp = await self.session.get(url)
        status = json.loads(await resp.text())
        return status

    def embedMessage(self, status):
        embed=discord.Embed(color=0x05e400)
        embed.set_author(name="Dedicated Server", icon_url="https://i.imgur.com/KEd7OQJ.png")
        embed.set_thumbnail(url="https://i.imgur.com/KEd7OQJ.png")
        embed.add_field(name="Players", value="{}/{}".format(status.players, status.maxPlayers), inline=False)
        embed.add_field(name="Map", value="{}".format(status.serverName), inline=True)
        embed.set_footer(text="Brought to you by Hoggit")
        return embed


    @commands.command(pass_context=True)
    async def server_status(self, ctx):
        if ctx.invoked_subcommand is None:
            if (self.key_data == {}):
                await self.bot.say("Configure the key first bud")
            else:
                status = await self.get_status()
                message = self.embedMessage(status)
                await self.boy.say(embed=embed)

    @commands.command(name = "server_status_key")
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
