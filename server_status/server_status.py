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

    def __init__(self, updateTime):
        self.uptime_file = "data/server_status/server.json"
        self.uptime_data = dataIO.load_json(self.uptime_file)
        self.status = self.determine_status(updateTime, self.uptime_data)
        self.color = self.determine_color(self.status)
        self.uptime = self.determine_uptime(self.status, self.uptime_data)

    def determine_status(self, updateTime, uptime_data):
        now = arrow.utcnow()
        status = "Online"
        if "status" not in uptime_data:
            uptime_data["status"] = ""
        if (updateTime < now.shift(seconds=-30)):
            status = "Unhealthy"
        if (updateTime < now.shift(minutes=-1)):
            status = "Offline"
        if status != uptime_data["status"]:
            self.store_uptime(status, updateTime)
        return status

    def determine_color(self, status):
        if (status == "Online"):
            return 0x05e400
        if (status == "Unhealthy"):
            return 0xFF9700
        return 0xFF0000

    def determine_uptime(self, status, uptime_data):
        now = arrow.utcnow()
        if self.get_uptime()['status'] == status:
            current_uptime = self.determine_delta(now, uptime_data["time"])
            return current_uptime

    def get_uptime(self):
        return dataIO.load_json(self.uptime_file)

    def store_uptime(self, status, time):
        self.uptime_data["status"] = status
        self.uptime_data["time"] = time.for_json()
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
        self.base_url = "http://status.hoggitworld.com/"
        self.killPoll = False
        self.start_polling()


    def __unload(self):
        #kill the polling
        self.killPoll = True

    def start_polling(self):
        asyncio.ensure_future(self.poll())
        print("Server Status polling started")


    async def poll(self):
        print("Server Status: Poll...")
        try:
            status = await self.get_status()
            print("Server Status Poll: {}".format(status))
            await self.set_presence(status)
        except:
            print("Server Status poll encountered an error. skipping this poll.")
        finally:
            if self.killPoll:
                print("Server Status poll killswitch received. Not scheduling another poll")
                return
            await asyncio.sleep(20)
            asyncio.ensure_future(self.poll())


    def store_key(self, key):
        self.key_data = key
        dataIO.save_json(self.key_file, self.key_data)

    async def set_presence(self, status):
        await self.bot.wait_until_ready()
        game="{} players on {}".format(status["players"], status["missionName"])
        health=self.determine_health(status)
        bot_status=discord.Status.online
        if health.status == "Unhealthy":
            bot_status=discord.Status.idle
            game="Slow updates - " + game
        elif health.status == "Offline":
            bot_status=discord.Status.dnd
            game="Server offline"
        print("Server Status: Trying to set status to {}. Game to {}".format(bot_status, game))
        await self.bot.change_presence(status=bot_status, game=discord.Game(name=game))

    async def get_status(self):
        url = self.base_url + self.key_data["key"]
        resp = await self.session.get(url)
        if (resp.status != 200):
            raise ErrorGettingStatus(resp.status)
        status = json.loads(await resp.text())
        #Hoggy Server counts himself among the players.
        status["players"] = status["players"] - 1
        status["maxPlayers"] = status["maxPlayers"] - 1
        return status

    def determine_health(self, status):
        last_update = arrow.get(status["data"]["updateTime"])
        return ServerHealth(last_update)

    def humanize_time(self, updateTime):
        print("Got time: {}".format(updateTime))
        arrowtime = arrow.get(updateTime)
        print("humanize time: {}".format(arrowtime.humanize()))
        return arrowtime.humanize()
    
    def get_mission_time(self, status):
        time_seconds = datetime.timedelta(seconds=status["data"]["uptime"])
        return str(time_seconds).split(".")[0]

    def embedMessage(self, status):
        health = self.determine_health(status)
        embed=discord.Embed(color=health.color)
        embed.set_author(name=status["serverName"], icon_url="https://i.imgur.com/KEd7OQJ.png")
        embed.set_thumbnail(url="https://i.imgur.com/KEd7OQJ.png")
        embed.add_field(name="Status", value=health.status, inline=True)
        embed.add_field(name="Mission", value=status["missionName"], inline=True)
        embed.add_field(name="Map", value=status["map"], inline=True)
        embed.add_field(name="Players", value="{}/{}".format(status["players"], status["maxPlayers"]), inline=True)
        if health.status == "Online":
            embed.add_field(name="Mission Time", value=self.get_mission_time(status), inline=True)
        else:
            embed.add_field(name="{} Since".format(health.status), value=health.uptime, inline=True)
        embed.set_footer(text="Last update: {} -- See my status light for up-to-date status.".format(self.humanize_time(status["updateTime"])))
        return embed


    @commands.group(pass_context=True, aliases=["server"])
    async def server_status(self, ctx):
        if ctx.invoked_subcommand is None:
            if (self.key_data == {} or self.key_data["key"] == ''):
                await self.bot.say("Configure the key first bud")
            else:
                if not ctx.message.channel.is_private:
                    await self.bot.send_message(ctx.message.author, "Please only use `!server` in PMs with me.")
                try:
                    print(ctx.message)
                    status = await self.get_status()
                    message = self.embedMessage(status)
                    await self.bot.send_message(ctx.message.author, embed=message)
                    await self.set_presence(status)
                except ErrorGettingStatus as e:
                    await self.bot.send_message(ctx.message.author, "Status unknown right now.")
                    print("Error getting status. Response code was " + str(e.status))

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
