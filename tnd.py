from discord.ui import View,Button,Modal
import discord
from fns import *
class TruthDareView(View):
    def __init__(self):
        super().__init__(timeout=120)
    @discord.ui.button(label="Truth",style=discord.ButtonStyle.grey)
    async def truth(self,interaction:discord.Interaction,button:Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True    
        await interaction.message.edit(view=self)
        count = glob_fns().load_json("TND/track.json")
        truth_list = glob_fns().load_json("TND/truths.json")
        truth = truth_list[count['t']]
        leng = len(truth_list) - 1
        if count['t']<leng:
            count['t'] += 1
        else:
            count['t'] = 0
        embed = discord.Embed(
            title="Truth time!",
            description=f"{interaction.user.mention} chose **truth**: \n\n{truth}",
            color=discord.Color.gold()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1351195291616808981/1389261384331690228/ChatGPT_Image_Jun_30_2025_08_38_12_PM.png?ex=6863f9fd&is=6862a87d&hm=55479aff2368234d46c02e39a66147395a0f537c401ce63d06a8902cd9f4c87f&")
        view = TruthDareView()
        glob_fns().save_json(count,"TND/track.json")
        msg = await interaction.channel.send(embed=embed,view=view)
        self.stop()
    @discord.ui.button(label="Dare",style=discord.ButtonStyle.grey)
    async def dare(self,interaction:discord.Interaction,button:Button):
        try:
            await interaction.response.defer()
            for item in self.children:
                item.disabled = True
            count = glob_fns().load_json("TND/track.json")
            dare_list = glob_fns().load_json("TND/dares.json")
            dare = dare_list[count['d']]
            leng = len(dare_list) - 1
            if count['d']<leng:
                count['d'] += 1
            else:
                count['d'] = 0
            embed = discord.Embed(
                title="Dare Time!",
                description=f"{interaction.user.mention} chose **Dare**:\n\n{dare}",
                color=discord.Color.gold()
            )
            embed.set_image(url="https://cdn.discordapp.com/attachments/1351195291616808981/1389261384331690228/ChatGPT_Image_Jun_30_2025_08_38_12_PM.png?ex=6863f9fd&is=6862a87d&hm=55479aff2368234d46c02e39a66147395a0f537c401ce63d06a8902cd9f4c87f&")
            view = TruthDareView()
            glob_fns().save_json(count,"TND/track.json")
            await interaction.channel.send(embed=embed, view=view)
            self.stop()
        except Exception as e:
            print(f"Error in TruthDareView.dare: {e}")
            await interaction.channel.send("An error occurred while processing your dare. Please try again later.")
            self.stop()