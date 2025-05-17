#Currently down due to Genius Api Issues
import discord
from discord import app_commands
from discord.ext import commands
from lyricsgenius import Genius
import os
import re

# Initialize Genius API
GENIUS_TOKEN = os.getenv("GENIUS_API_TOKEN")
genius = Genius(GENIUS_TOKEN)

class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clean_lyrics(self, lyrics):
        # Remove the "Lyrics" header if present
        if lyrics.startswith('Lyrics'):
            lyrics = lyrics[lyrics.find('\n')+1:]

        # Remove contributor line and similar metadata
        lines = lyrics.split('\n')
        cleaned_lines = []
        skip_patterns = [
            r'^\d+ Contributors',
            r'^Translations',
            r'^Romanization',
            r'.*Lyrics\[.*\]',
        ]

        for line in lines:
            if not any(re.match(p, line) for p in skip_patterns):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @app_commands.command(name="lyrics", description="Fetch lyrics for a given song name")
    @app_commands.describe(song="The name of the song you want lyrics for")
    async def lyrics(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()
        try:
            results = genius.search_songs(song)
            if not results['hits']:
                await interaction.followup.send("\u274c No lyrics found for that song.")
                return

            top_hit = results['hits'][0]['result']
            song_title = top_hit['title']
            artist_name = top_hit['primary_artist']['name']
            album_art_url = top_hit['song_art_image_url']
            raw_lyrics = genius.lyrics(song_url=top_hit['url'])

            lyrics = self.clean_lyrics(raw_lyrics)

            if len(lyrics) > 4000:
                part1 = lyrics[:4000] + "..."
                embed = discord.Embed(title=song_title, description=part1, color=0x2ecc71)
                embed.set_author(name=f"Song by {artist_name}")
                embed.set_thumbnail(url=album_art_url)
                embed.set_footer(text="Lyrics provided by Genius")
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(title=song_title, description=lyrics, color=0x2ecc71)
                embed.set_author(name=f"Song by {artist_name}")
                embed.set_thumbnail(url=album_art_url)
                embed.set_footer(text="Lyrics provided by Genius")
                await interaction.followup.send(embed=embed)

        except Exception as e:
            error_message = str(e)
            
            # Check for specific 403 Forbidden error from Genius
            if "[Errno 403]" in error_message and "genius.com" in error_message:
                error_embed = discord.Embed(
                    title="Error",
                    description="\u274c Genius blocks shared IPs, which my bot \n)",
                    color=0xe74c3c
                )
            else:
                error_embed = discord.Embed(
                    title="Error",
                    description=f"\u274c An error occurred: {error_message}",
                    color=0xe74c3c
                )
            
            await interaction.followup.send(embed=error_embed)


def setup(bot):
    bot.add_cog(Lyrics(bot))
