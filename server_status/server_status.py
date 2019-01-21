import asyncio
import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from .utils import checks
from .utils.dataIO import dataIO
import json
import aiohttp
import datetime
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

    def __init__(self, updateTime, server_key):
        self.uptime_file = "data/server_status/server.json"
        self.uptime_data = dataIO.load_json(self.uptime_file)
        self.status = self.determine_status(updateTime, self.uptime_data[server_key], server_key)
        self.color = self.determine_color(self.status)
        self.uptime = self.determine_uptime(self.status, self.uptime_data[server_key])

    def determine_status(self, updateTime, uptime_data, server_key):
        now = arrow.utcnow()
        status = "Online"
        if "status" not in uptime_data:
            uptime_data["status"] = ""
        if (updateTime < now.shift(seconds=-60)):
            status = "Unhealthy"
        if (updateTime < now.shift(seconds=-100)):
            status = "Offline"
        if status != uptime_data["status"]:
            self.store_uptime(status, updateTime, server_key)
        return status

    def determine_color(self, status):
        if (status == "Online"):
            return 0x05e400
        if (status == "Unhealthy"):
            return 0xFF9700
        return 0xFF0000

    def determine_uptime(self, status, uptime_data):
        now = arrow.utcnow()
        if "status" not in self.get_uptime():
            return self.determine_delta(now, uptime_data["time"])
        if self.get_uptime()['status'] == status:
            current_uptime = self.determine_delta(now, uptime_data["time"])
            return current_uptime

    def get_uptime(self):
        return dataIO.load_json(self.uptime_file)

    def store_uptime(self, status, time, server_key):
        self.uptime_data[server_key]["status"] = status
        self.uptime_data[server_key]["time"] = time.for_json()
        dataIO.save_json(self.uptime_file, self.uptime_data)

    def determine_delta(self, current, change):
        delta = current - arrow.get(change)
        days = delta.days
        hours,remainder = divmod(delta.seconds,3600)
        minutes,seconds = divmod(remainder,60)
        return "{0} hours {1} minutes {2} seconds".format(
            hours, minutes, seconds
        )

class DCSServerStatus:
    """
    Returns the status of your DCS server
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.key_file = "data/server_status/server.json"
        self.key_data = dataIO.load_json(self.key_file)
        self.base_url = "https://status.hoggitworld.com/"
        self.killPoll = False
        self.last_key_checked = None
        self.start_polling()
        self.presence_cycle_time_seconds = 5

    def __unload(self):
        #kill the polling
        self.killPoll = True

    def start_polling(self):
        asyncio.ensure_future(self.poll())
        print("Server Status polling started")

    def get_next_key(self):
        key = None
        if not self.last_key_checked:
            if len(self.key_data) > 0:
                key = list(self.key_data.keys())[0]
            else:
                return None
        else:
            key = self.last_key_checked
            found = False
            for k in self.key_data.keys():
                if found:
                    key = k
                    break
                if k == key:
                    found = True
            if key == self.last_key_checked:
                key = list(self.key_data.keys())[0]
        self.last_key_checked = key
        return key


    async def poll(self):
        try:
            key = self.get_next_key()
            if key == None:
                print ("No keys to poll on. skipping")
            else:
                data = self.key_data[key]
                status = await self.get_status(data["key"])
                await self.set_presence(status, key)
        except Exception as e:
            print("Server Status poll encountered an error. skipping this poll: ", e)
        finally:
            if self.killPoll:
                print("Server Status poll killswitch received. Not scheduling another poll")
                return
            await asyncio.sleep(self.presence_cycle_time_seconds)
            asyncio.ensure_future(self.poll())


    def store_key(self, key):
        self.key_data[key["alias"].lower()] = key
        self.save_key_data(self.key_data)

    def delete_key(self, alias):
        if alias.lower() in self.key_data:
            del self.key_data[alias.lower()]
            self.save_key_data(self.key_data)

    def save_key_data(self, key_data):
        dataIO.save_json(self.key_file, key_data)

    async def set_presence(self, status, server_key):
        await self.bot.wait_until_ready()
        server_data = self.key_data[server_key]
        game="{} players on {} playing on {}".format(status["players"], server_data["alias"], status["missionName"])
        health=self.determine_health(status, server_key)
        bot_status=discord.Status.online
        if health.status == "Unhealthy":
            bot_status=discord.Status.idle
            game="Slow updates - " + game
        elif health.status == "Offline":
            bot_status=discord.Status.dnd
            game="{} Server offline".format(server_data["alias"])
        await self.bot.change_presence(status=bot_status, game=discord.Game(name=game))

    async def get_status(self, key):
        url = self.base_url + key
        resp = await self.session.get(url)
        if (resp.status != 200):
            raise ErrorGettingStatus(resp.status)
        status = json.loads(await resp.text())
        #Hoggy Server counts himself among the players.
        status["players"] = status["players"] - 1
        status["maxPlayers"] = status["maxPlayers"] - 1
        return status

    def determine_health(self, status, server_key):
        last_update = arrow.get(status["data"]["updateTime"])
        return ServerHealth(last_update, server_key)

    def humanize_time(self, updateTime):
        arrowtime = arrow.get(updateTime)
        return arrowtime.humanize()

    def get_mission_time(self, status):
        time_seconds = datetime.timedelta(seconds=status["data"]["uptime"])
        return str(time_seconds).split(".")[0]

    def get_metar(self, status):
        if "metar" in status["data"]:
            metar = status["data"]["metar"]
            if metar:
                return metar
        return "Unavailable"

    def embedMessage(self, status, alias):
        health = self.determine_health(status, alias)
        embed=discord.Embed(color=health.color)
        embed.set_author(name=status["serverName"], icon_url="https://i.imgur.com/KEd7OQJ.png")
        embed.set_thumbnail(url="https://i.imgur.com/KEd7OQJ.png")
        embed.add_field(name="Status", value=health.status, inline=True)
        embed.add_field(name="Mission", value=status["missionName"], inline=True)
        embed.add_field(name="Map", value=status["map"], inline=True)
        embed.add_field(name="Players", value="{}/{}".format(status["players"], status["maxPlayers"]), inline=True)
        embed.add_field(name="METAR", value=self.get_metar(status))
        if health.status == "Online":
            embed.add_field(name="Mission Time", value=self.get_mission_time(status), inline=True)
        else:
            embed.add_field(name="{} Since".format(health.status), value=health.uptime, inline=True)
        embed.set_footer(text="Last update: {} -- See my status light for up-to-date status.".format(self.humanize_time(status["updateTime"])))
        return embed

    @commands.group(pass_context=True, aliases=["serverlist"])
    async def _servers(self, ctx):
        servers = self.key_data.items()
        message = "Tracking the following servers:\n"
        for key, server in servers:
            message += ":desktop: -- {}\n".format(server["alias"])
        message += "\n\nUse `!server <servername>` to get the status of that server"
        await self.bot.say(message)

    @commands.group(pass_context=True, aliases=["server"])
    async def server_status(self, ctx, alias):
        """Gets the server status for the provided alias. Use !serverlist to see all the servers we're tracking"""
        if ctx.invoked_subcommand is None:
            alias = alias.lower()
            if alias not in self.key_data:
                await self.bot.send_message(ctx.message.author, "We aren't tracking a server called {}".format(alias))
            if (self.key_data == {}):
                await self.bot.say("Configure the key first bud")
                return
            else:
                if not ctx.message.channel.is_private:
                    await self.bot.send_message(ctx.message.author, "Please only use `!server` in PMs with me.")
                try:
                    if alias not in self.key_data:
                        await self.bot.send_message(ctx.message.author, "No server by that alias.")
                        return
                    status = await self.get_status(self.key_data[alias]["key"])
                    message = self.embedMessage(status, alias)
                    await self.bot.send_message(ctx.message.author, embed=message)
                except ErrorGettingStatus as e:
                    await self.bot.send_message(ctx.message.author, "Status unknown right now.")
                    print("Error getting status. Response code was " + str(e.status))

    @commands.group(pass_context=True, aliases=["serverconf"])
    async def _serverconf(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @_serverconf.command()
    @checks.mod_or_permissions(manage_server=True)
    async def delete(self, alias):
        self.delete_key(alias)
        await self.bot.say("Removed key for {}".format(alias))

    @_serverconf.command()
    @checks.mod_or_permissions(manage_server=True)
    async def key(self, alias, *, text = ""):
        key = {}
        key["key"] = text
        key["alias"] = alias
        self.store_key(key)
        await self.bot.say("Updated Key for {} to {}".format(key["alias"], key["key"]))

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
