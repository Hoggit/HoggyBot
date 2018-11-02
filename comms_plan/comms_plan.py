import csv
import aiohttp
import io
from discord.ext import commands


class CommsPlan:
    """
    Fetches the comms plan from discord
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        #Make configurable.
        self.comms_plan_url ="https://docs.google.com/spreadsheets/d/1a63VD2WXmShIwpiTTfHuK-5yWKw-3AtXLbv1LBjMyCE" 
        self.comms_plan_export = self.comms_plan_url + "/export?exportFormat=csv"

    async def fetch_comms_plan(self):
        resp = await self.session.get(self.comms_plan_export)
        if (resp.status != 200):
            await self.bot.say("Error getting comms plan. Check logs")
            raise Exception("Could not get status")
        return await resp.text()

    def is_number(self, number):
        try:
            float(number)
            return True
        except ValueError:
            return False
    
    def parse_comms_plan(self, plan):
        data = io.StringIO(plan)
        reader = csv.reader(data)
        comms_info = []
        for row in reader:
            if row[1] and self.is_number(row[1]):
                radio = {}
                radio['freq'] = row[1]
                radio['use'] = row[3]
                comms_info.append(radio)

        return comms_info

    async def respond_with_plan(self, plan):
        message_template = "```Address: dcs.hoggitworld.com\n%s```%s"
        plan_message = ""
        for radio in plan:
            plan_message += "%s: %s\n" % (radio['use'], radio['freq'])

        await self.bot.say(message_template % (plan_message, "Details: <%s>" % self.comms_plan_url))

    @commands.group(pass_context=True, aliases=["srs"])
    async def print_comms_plan(self, ctx):
        comms_plan = await self.fetch_comms_plan()
        comms_plan = self.parse_comms_plan(comms_plan)
        await self.respond_with_plan(comms_plan)


def setup(bot):
    bot.add_cog(CommsPlan(bot))
