"""The Legend of Link instruction booklet: builds web/manual/index.html (the page links to it; its pictures are in
web/manual/img). python3 manual/gen.py; node manual/pdf.js web/manual/index.html out.pdf prints it.
The version on the cover is the build's (lol_seedcode.VERSION): bump it with every change set."""
import html, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "manual")
VERSION = re.search(r'VERSION = "([^"]+)"', open(os.path.join(HERE, "..", "build", "lol", "lol_seedcode.py")).read()).group(1)

# (key, display name, price, requires, effect) by tier; keys match lol_uptable's rows (icon order)
ORDER = ['beams', 'boomstick', 'regen', 'skull ring', 'sword mastery', 'fairy bottle', 'blue like likes', 'rupee speed',
         'ganon boomerang', 'critter crusher', 'statue jammer', 'bombsmith', 'potion pouch', 'bat potion', 'bow mastery',
         'ganon visible', 'slow fireballs', 'key hoarder', 'unlimited candle', 'misers bow', 'refilling bag',
         'map master', 'spider bomber', 'bow of greed', 'holy fire', 'xp boost', 'ghost hunter', 'healerang',
         'shield breaker', 'membership card', 'poison bait', 'heart snubber', 'divining rod', 'song of chaos',
         'zombie link', 'brain potion', 'x-ray glasses', 'boomerang mastery', 'bookworm', 'heavy bracelet', 'song of discovery']
ICON = {k: f"img/up_{i:02d}.png" for i, k in enumerate(ORDER)}

UP = {
 1: [
  ("ganon visible", "Ganon Visible", 25, "", "Ganon can no longer hide. He stays in plain sight for the whole fight."),
  ("song of chaos", "Song of Chaos", 25, "Recorder and at least one triforce piece",
   "Play the recorder on the overworld and the whirlwind always comes. It sets you down on a random safe screen."),
  ("beams", "Sword Beams", 50, "A sword. Not with Heart Snubber", "Your sword shoots beams at any health, not only when your hearts are full."),
  ("skull ring", "Skull Ring", 50, "", "Bubbles can't touch you, so they can never take your sword away."),
  ("blue like likes", "Blue Like Likes", 50, "",
   "Like Likes turn blue and weaker. They drop bombs when beaten, and one that grabs you eats a bomb instead of your Magical Shield."),
  ("critter crusher", "Critter Crusher", 50, "", "Gels and Keese that touch you are stomped flat. No damage to you."),
  ("potion pouch", "Potion Pouch", 50, "A potion",
   "Potions stack. A blue potion adds one dose and a red one two, up to four doses."),
  ("slow fireballs", "Slow Fireballs", 50, "", "Enemy fireballs fly at half speed."),
  ("key hoarder", "Key Hoarder", 50, "", "Every key you pick up counts as two."),
  ("unlimited candle", "Unlimited Blue Candle", 50, "Blue candle (not the red)",
   "Your blue candle burns as often as you like, as the red one does."),
  ("misers bow", "Miser's Bow", 50, "Bow. Not with Bow of Greed", "Arrows cost no rupees, but they hit a little softer."),
  ("refilling bag", "Refilling Bomb Bag", 50, "A bomb upgrade (or swordless mode)",
   "A new bomb grows in your bag every 90 seconds until it's full. Using a bomb restarts the count."),
  ("map master", "Map Master", 50, "", "Every map at once: Levels 1-9 and all four shrines."),
  ("poison bait", "Poison Bait", 50, "Bait",
   "The bait turns blue. Moblins, Goriyas and Octoroks that nibble it slowly sicken and die, and it lures Gibdos too. But Gibdos love it: it heals them."),
  ("brain potion", "Brain Potion", 50, "Zombie Link and a potion. Not with Bat Potion",
   "Every potion becomes a brain potion, which refills a zombie completely."),
 ],
 2: [
  ("spider bomber", "Spider Bomber", 75, "A bomb upgrade", "Bombs hurt Gohma even with its eye shut."),
  ("zombie link", "Zombie Link", 75, "Exactly 3 hearts, no ring, no Regeneration",
   "Rare. See the Zombie Link page."),
  ("boomerang mastery", "Boomerang Mastery", 75, "A boomerang", "Your boomerangs hit 1 harder, so they hurt as well as stun."),
  ("heavy bracelet", "Heavy Bracelet", 75, "Power Bracelet",
   "Lets you push certain heavy rocks on the overworld. What's behind them? The heavy rocks show grey once you have it."),
  ("song of discovery", "Song of Discovery", 75, "Recorder",
   "Your recorder finds new places. Spots where it reveals something show a recorder once you have it."),
  ("boomstick", "Boomstick", 100, "Wand. Not with Divining Rod", "The wand's shot ends in a bomb blast where it hits a wall or a monster."),
  ("sword mastery", "Sword Mastery", 100, "A sword. Not with Heart Snubber", "Your sword hits one step harder."),
  ("rupee speed", "Rupee Speed", 100, "", "The more rupees you carry, the faster Link walks."),
  ("statue jammer", "Statue Jammer", 100, "", "Dungeon statues stop firing at you."),
  ("bow of greed", "Bow of Greed", 100, "Bow. Not with Miser's Bow", "Arrows hit twice as hard but cost 5 rupees a shot."),
  ("holy fire", "Holy Fire", 100, "A candle",
   "Candle fire burns the undead hard: Stalfos, Gibdos, Ghinis and Pols Voice. Even blue Pols Voice burn."),
  ("xp boost", "XP Boost", 100, "Fewer than 4 heart containers", "Rare. Enemies give double XP, bosses 5 more."),
  ("divining rod", "Divining Rod", 100, "Wand. Not with Boomstick",
   "Your wand becomes a wooden rod. It only stabs (a little weaker, no magic shot), but every compass comes with it."),
  ("regen", "Regeneration", 125, "Not with Zombie Link", "Get back 1/4 heart for every 10 seconds you go without being hit."),
  ("bat potion", "Bat Potion", 125, "A potion. Not with Brain Potion",
   "Every potion becomes a bat potion. Drink one and eight bats burst out and destroy ordinary enemies in their path (no XP or drops). Bosses are spared."),
  ("ghost hunter", "Ghost Hunter", 125, "", "Every Ghini you defeat drops 5 rupees."),
 ],
 3: [
  ("fairy bottle", "Fairy in a Bottle", 150, "",
   "When you fall, the fairy brings you back with up to 8 hearts. Visit a fairy fountain to catch a new one. While you have her, she shows beside your hearts."),
  ("ganon boomerang", "Ganon Boomerang", 150, "", "Your boomerang can wound Ganon, as hard as your sword would."),
  ("bombsmith", "Bombsmith", 150, "A bomb upgrade", "A bomb blast opens locked doors. No key needed."),
  ("bow mastery", "Bow Mastery", 150, "Bow and arrows",
   "Arrows pierce Wizzrobes, Gleeok and Patra, and stun Dodongos on touch."),
  ("healerang", "Healerang", 150, "A boomerang", "Finish an enemy with your boomerang to heal 1/4 heart."),
  ("shield breaker", "Shield Breaker", 150, "", "Strike Darknuts from the front. Their shields no longer block you."),
  ("membership card", "Membership Card", 200, "Only in the first upgrade cave you find", "Every shop price is cut in half."),
  ("heart snubber", "Heart Snubber", 200, "A sword, 3 hearts or fewer. Only in the second upgrade cave you find",
   "See the Heart Snubber page."),
  ("bookworm", "Bookworm", 200, "Level 8 or higher",
   "Books teach twice as much: the red book adds 2 to every hit, the blue book 4. Until you own a book, a dungeon old man always offers the red book, and every shop sells it for 25 rupees."),
  ("x-ray glasses", "X-ray Glasses", 200, "",
   "In dungeons, walls you can bomb glow grey and walls you can walk through glow orange."),
 ],
}
assert sum(len(v) for v in UP.values()) == 41 and {u[0] for v in UP.values() for u in v} == set(ORDER)


def up_rows(items):
    out = []
    for key, name, price, req, eff in items:
        req_html = f'<div class="req">Needs: {html.escape(req)}</div>' if req else ""
        out.append(f'''<div class="up"><div class="ic"><img src="{ICON[key]}"></div>
<div class="ut"><div class="un">{html.escape(name)} <span class="pr">{price}<i class="rp"></i></span></div>
<div class="ue">{html.escape(eff)}</div>{req_html}</div></div>''')
    return "\n".join(out)


def shot(src, cap, cls=""):
    return f'<figure class="shot {cls}"><img src="{src}"><figcaption>{cap}</figcaption></figure>'


pages = []
P = pages.append

# ---------------- cover
cover_icons = "".join(f'<img src="{ICON[k]}">' for k in ORDER[:36])   # (a 9 x 4 grid)
P(f'''<section class="page cover">
<div class="cframe">
 <div class="ctop">INSTRUCTION BOOKLET</div>
 <div class="ctitle"><span class="the">THE</span>LEGEND<br>OF LINK</div>
 <div class="csub">A new randomized way to play a classic, world-renowned game.</div>
 <ul class="cfeat">
  <li>New dungeon designs</li>
  <li>An experience point based leveling system</li>
  <li>Enemies that get stronger as you level up</li>
  <li>New upgrades: things you always wanted, or didn't know you wanted until you see them in action</li>
 </ul>
 <div class="ctag">This isn't your grandparents' Legend of Zelda (but they'll enjoy it too).</div>
 <div class="cicons">{cover_icons}</div>
 <div class="cver">BETA {VERSION}</div>
</div>
</section>''')

# ---------------- contents
toc = [("Before You Begin", "BEFORE YOU BEGIN"), ("Building Your Game", "BUILDING YOUR GAME"),
       ("The Title and File Screens", "THE TITLE AND FILE"), ("What's New", "WHAT'S NEW"),
       ("Experience and Levels", "EXPERIENCE AND LEVELS"), ("Enemies That Grow With You", "ENEMIES THAT GROW"),
       ("The Overworld", "THE OVERWORLD"), ("Dungeons and Shrines", "DUNGEONS AND SHRINES</h1>"), ("Level 9", "LEVEL 9"),
       ("How Items Are Offered", "HOW ITEMS ARE OFFERED"), ("Old Men Cards and XP Bags", "OLD MEN CARDS"),
       ("Upgrade Caves", "UPGRADE CAVES"), ("Upgrade Catalog", "UPGRADE CATALOG: TIER 1"),
       ("Heart Snubber and Zombie Link", "HEART SNUBBER AND"), ("The Triforce Caves", "THE TRIFORCE CAVES"),
       ("Secret Modes", "SECRET MODES"), ("The End of Your Quest", "THE END OF YOUR"), ("Old Men's Hints and Tips", "OLD MEN'S HINTS")]
rows = "@@TOC@@"
P(f'''<section class="page"><h1 class="band">CONTENTS</h1>
<div class="toc">{rows}</div>
<div class="note">Legend of Link is a fan-made rework. It needs your own copy of the original game, and the randomizer page builds a patch for it in your browser.</div>
</section>''')

# ---------------- before you begin
P(f'''<section class="page"><h1 class="band">BEFORE YOU BEGIN</h1>
<p class="lead">Long ago the land was mapped, its caves were known and every dungeon was the same each time a hero set out. No more.</p>
<p>In <b>Legend of Link</b> the dungeons are built fresh for every seed, the caves hide different things behind every door, and Link grows stronger with every enemy he defeats. Shopkeepers sell new <b>upgrades</b>, dungeons hide <b>old men cards</b> that bring better treasure, and four <b>shrines</b> wait alongside the nine levels.</p>
<p>The enemies grow too. As Link gains heart containers, some of them become something more dangerous.</p>
<p>This booklet explains everything that is different from the original adventure. The controls:</p>
<table class="ctl">
<tr><th>Control Pad</th><td>Move Link</td></tr>
<tr><th>A Button</th><td>Swing the sword</td></tr>
<tr><th>B Button</th><td>Use the item chosen on the item screen</td></tr>
<tr><th>START</th><td>Open the item screen (pause)</td></tr>
<tr><th>SELECT</th><td>Swap items</td></tr>
</table>
<div class="hint"><b>HINT</b> Read the old men's hints. In Legend of Link they talk about this seed's upgrades and secrets.</div>
</section>''')

# ---------------- building
P(f'''<section class="page"><h1 class="band">BUILDING YOUR GAME</h1>
<p>Open the Legend of Link randomizer page and choose your own <b>Legend of Zelda (USA)</b> ROM, either PRG0 or PRG1. Everything happens in your browser, and your ROM is never uploaded.</p>
<h2>Settings</h2>
<dl>
<dt>Seed (numbers only)</dt><dd>The seed decides the whole game: dungeons, caves, upgrades and hints. Players with the same seed and settings play the same game. Leave it blank and one is picked for you.</dd>
<dt>Dungeon set</dt><dd>Where the dungeon shapes come from: Legend of Link's own maps, the 1st, 2nd, 3rd or 4th Quest shapes, random shapes, Random (any four grids) or Mixed (each level from any set). Shrines always use Legend of Link maps or random shapes.</dd>
<dt>Link's colors</dt><dd>His tunic color with no ring, the blue ring and the red ring. "From your ROM" keeps your ROM's colors.</dd>
<dt>Mix enemy groups</dt><dd>Deals the enemies into new groups, so new mixes of enemies meet in dungeons and on the overworld.</dd>
<dt>Unseeded</dt><dd>The old way: each new file deals its own dungeons and caves inside the game.</dd>
</dl>
<p>Press <b>Build</b> and download either the finished game or an IPS patch.</p>
<div class="hint"><b>CUSTOM SPRITES</b> A ROM whose only changes are the sprites of Link, the items and the enemies works too. Anything else changed, even colors, and the page turns it down.</div>
</section>''')

# ---------------- title & file
P(f'''<section class="page"><h1 class="band">THE TITLE AND FILE SCREENS</h1>
{shot("img/titletext.png", "The title screen shows the version and your seed.", "wide")}
<p>Wait at the title screen and the story scroll is replaced by a list of every upgrade the caves can sell: <b>Upgrades to Buy with Rupees</b>.</p>
<div class="two">{shot("img/fileselect.png", "The seed code beside CODE.")}{shot("img/titlelist.png", "The upgrade list on the title screen.")}</div>
<h2>The Seed Code</h2>
<p>There is only one save file, so the file screen's heading now reads <b>CODE</b> followed by four item pictures. They are worked out from your finished game. When your four pictures match a friend's, you are both playing exactly the same game. The randomizer page shows the same four pictures, with their names, under its download buttons.</p>
</section>''')

# ---------------- what's new
P(f'''<section class="page"><h1 class="band">WHAT'S NEW</h1>
<ul class="new">
<li><b>Experience.</b> Defeating enemies earns XP. Every 50 XP gives a heart container, up to 16.</li>
<li><b>Enemies grow with you.</b> Some enemies change as Link gains hearts.</li>
<li><b>New dungeons every seed.</b> Nine levels and four shrines (A-D), each with its own nickname.</li>
<li><b>Every door is a surprise.</b> Each cave, shop and dungeon entrance on the overworld is dealt out at random.</li>
<li><b>Old men offer choices.</b> In each level an old man lets you take one of two items.</li>
<li><b>Shrines and prizes.</b> Beat a shrine's guardian to claim its prize.</li>
<li><b>Upgrades.</b> 41 upgrades for sale, three upgrade caves to find, and one purchase in each.</li>
<li><b>Old men cards.</b> Collect cards in dungeons that bring better items from shops, old men and shrines.</li>
<li><b>New items.</b> The bomb upgrade, the blue book and XP bags.</li>
<li><b>Triforce caves.</b> Rewards for 4 and for all 8 triforce pieces.</li>
<li><b>Secret modes.</b> Swordless and Hard mode can be found in any game.</li>
<li><b>A final report.</b> Your time, cards, upgrades and treasure after the credits.</li>
</ul>
{shot("img/start.png", "The XP count sits below the rupees on the status bar.", "small")}
</section>''')

# ---------------- experience
P(f'''<section class="page"><h1 class="band">EXPERIENCE AND LEVELS</h1>
<p>Every enemy is worth some experience (<b>XP</b>). The higher Link's level, the <b>less XP</b> ordinary enemies give him, until the weakest ones give nothing at all. <b>Bosses</b> always give their full XP, whatever his level.</p>
<p>Every <b>50 XP</b> (100 in Hard mode) gives Link a new <b>heart container</b>, up to 16. The XP count is shown on the status bar.</p>
<h2>Link's Level</h2>
<p>Link's <b>level</b> is his number of heart containers. It decides which items the old men, shrines and shops offer, which enemies have grown stronger, and which upgrades appear. Old men cards raise the level used for offers (see page @@CARDS@@).</p>
<div class="hint"><b>XP BAGS</b> Keep an eye out for them, in dungeon cellars and elsewhere. An orange bag gives 15 XP and a blue bag 25.</div>
</section>''')

# ---------------- enemies
P(f'''<section class="page"><h1 class="band">ENEMIES THAT GROW WITH YOU</h1>
<p>Enemies watch Link's heart containers. When he reaches these, they change. In Hard mode they change 3 hearts sooner.</p>
<table class="grid lvl">
<tr><th>Hearts</th><th>Enemies</th></tr>
<tr><td>8</td><td>Red Moblins, Gibdos</td></tr>
<tr><td>9</td><td>Red Darknuts</td></tr>
<tr><td>10</td><td>Red Octoroks, Aquamentus, Pols Voice</td></tr>
<tr><td>12</td><td>Wallmasters, Vires, Gleeok, Blue Goriyas (the Goriya Charger)</td></tr>
</table>
{shot("img/gibdo.png", "Orange Gibdos.", "mid")}
<div class="hint"><b>HINT</b> Listen to the old men. They know a thing or two about these.</div>
</section>''')

# ---------------- overworld
P(f'''<section class="page"><h1 class="band">THE OVERWORLD</h1>
<p>The overworld map is the one you know, but what waits behind each cave, door and staircase is dealt out for every seed. Only the wood sword cave stays where it was. The 71 entrances hold:</p>
<table class="grid">
<tr><td>Levels 1-9</td><td>9</td><td>Upgrade caves</td><td>3</td></tr>
<tr><td>Shrines A-D</td><td>4</td><td>Gambling caves</td><td>5</td></tr>
<tr><td>Shops</td><td>12</td><td>Secret rupees (10, 30, 100)</td><td>13</td></tr>
<tr><td>4-triforce cave</td><td>1</td><td>8-triforce cave</td><td>1</td></tr>
<tr><td colspan="2">Hint caves</td><td colspan="2">all the rest</td></tr>
</table>
<h2>Shops</h2>
<p>Shops offer three items picked for Link's level. The offer changes as he gains hearts or shop cards. One shop is special: it sells as if Link were one level higher.</p>
<h2>Hint Caves</h2>
<p>Old men share hints: some about dungeons and enemies, some about the upgrades for sale in this seed, and some just for fun. Each hint cave has its own quote.</p>
<h2>Burning Bushes</h2>
<p>The <b>blue candle</b> can only burn <b>brown</b> bushes. The <b>red candle</b> burns both <b>green</b> and <b>brown</b> bushes.</p>
<div class="hint"><b>HINT</b> Play some music in the forest two screens south of the big bridge.</div>
</section>''')

# ---------------- dungeons (2 pages)
P(f'''<section class="page"><h1 class="band">DUNGEONS AND SHRINES</h1>
<p>Every level and shrine is built from a <b>design</b> with a nickname, such as the Robber, the Piranha or the Sock Puppet. The seed decides each level's design, enemies, colors, boss and treasure.</p>
<h2>Levels 1-8</h2>
<ul>
<li>An <b>old man</b> with a choice of items. Take one and the other disappears.</li>
<li>A <b>triforce piece</b>.</li>
<li><b>Old men cards</b> or <b>XP bags</b> in the cellars.</li>
<li>At least one <b>blue potion</b>.</li>
</ul>
<h2>Shrines A-D</h2>
<p>Shrines are smaller dungeons with a <b>guardian</b> boss. Beat it to reach the shrine's <b>prize</b>, an item picked for Link's level. The status bar reads SHRINE-A to SHRINE-D.</p>
{shot("img/subscreen.png", "Shrine letters beside TRIFORCE: here A and C are done.", "mid")}
</section>''')

P(f'''<section class="page"><h1 class="band">DUNGEONS AND SHRINES (CONT.)</h1>
<h2>The Item Screen</h2>
<p>Once a shrine's prize is taken, its letter appears beside the word TRIFORCE: A and B on the left, C and D on the right.</p>
<h2>Roars</h2>
<p>In Level 9 and the shrines, the rooms next to Ganon or a shrine's guardian echo with its roar while it lives. Follow the sound.</p>
<h2>Secret Walls</h2>
<p>With the <b>X-ray Glasses</b>, walls you can bomb glow grey and walls you can walk through glow orange.</p>
{shot("img/xray.png", "X-ray Glasses: a grey bomb wall above, orange walk-through walls to each side.", "mid")}
<div class="hint"><b>DUNGEON SETS</b> With quest shapes, only the shape of the old dungeon is borrowed. Doors, rooms, enemies and items are all new.</div>
</section>''')

# ---------------- level 9
P(f'''<section class="page"><h1 class="band">LEVEL 9</h1>
<p>An old man guards Level 9's entrance. He will not let Link pass until he holds all <b>8 triforce pieces</b>.</p>
<ul>
<li>Level 9's <b>compass</b> points to Princess Zelda's room.</li>
<li>Its <b>item staircase</b> gives the next thing Link is missing from: a book, a ring, a sword, arrows or the magic key. With all of them, a red potion.</li>
<li>Ganon waits within. With <b>Ganon Visible</b> he cannot hide, and with <b>Ganon Boomerang</b> your boomerang wounds him.</li>
</ul>
<div class="hint"><b>HINT</b> The 8-triforce cave (page @@TRI@@) has a reward waiting once you have all eight pieces.</div>
</section>''')

# ---------------- item offers
P(f'''<section class="page"><h1 class="band">HOW ITEMS ARE OFFERED</h1>
<p>Dungeon old men, shrine prizes and shops each have their own list of items for every level from 1 to 16. The seed shuffles each list, putting likelier items toward the front.</p>
<p>When an offer is made, the game walks down the list for Link's level and gives the first items he can use. Items he owns are skipped, and so is anything he isn't ready for yet.</p>
<h2>First Things First</h2>
<p>If the list lands on a better version of an item Link doesn't have yet, he gets the first version instead:</p>
<table class="grid">
<tr><th>The list says</th><th>Without</th><th>You get</th></tr>
<tr><td>Magical sword</td><td>White sword</td><td>White sword</td></tr>
<tr><td>Red candle</td><td>Blue candle</td><td>Blue candle</td></tr>
<tr><td>Red ring</td><td>Blue ring</td><td>Blue ring</td></tr>
<tr><td>Silver arrows</td><td>Wood arrows</td><td>Wood arrows</td></tr>
<tr><td>Blue book</td><td>Red book</td><td>Red book</td></tr>
</table>
<p>An old man's offer and a shrine's prize are fixed the first time Link enters the room. Shops change as Link gains hearts or shop cards.</p>
<div class="hint"><b>BLUE BOOK</b> A new, stronger book. Like the red book, it makes all of Link's weapons deal more damage.</div>
</section>''')

# ---------------- cards
P(f'''<section class="page"><h1 class="band">OLD MEN CARDS AND XP BAGS</h1>
<p><b>Old men cards</b> are collected in dungeons. Each card adds one level, for one kind of offer, to the level Link's offers are picked by. That brings better items sooner. You can hold up to three of each, and a fourth becomes an orange XP bag.</p>
<table class="grid">
<tr><th>Card</th><th>Looks like</th><th>Improves</th></tr>
<tr><td>S - Shop</td><td>Brown border</td><td>What shops sell</td></tr>
<tr><td>D - Dungeon</td><td>White border, red old man</td><td>Dungeon old men's choices</td></tr>
<tr><td>X - Shrine</td><td>White border, blue old man</td><td>Shrine prizes</td></tr>
</table>
<p><b>XP bags</b> turn up in dungeon cellars and other places: orange for 15 XP and blue for 25 XP.</p>
<p>The bomb upgrade adds 4 to the most bombs Link can carry (up to 20) and fills the bag.</p>
<div class="hint"><b>HINT</b> Cards are counted on the final report: see how many you found.</div>
</section>''')

# ---------------- upgrade caves
P(f'''<section class="page"><h1 class="band">UPGRADE CAVES</h1>
{shot("img/upcave.png", "An upgrade cave: one upgrade from each tier.", "mid")}
<p>Three caves on the overworld sell <b>upgrades</b> for rupees. Each seed picks up to 10 upgrades per tier for its shops.</p>
<ul>
<li>Each cave offers one upgrade from each <b>tier</b>: tier 1 (25-50 rupees), tier 2 (75-125) and tier 3 (150-200).</li>
<li>The first time Link enters a cave, it takes the next upgrade in each tier's line that he can use. Those three stay in that cave from then on.</li>
<li>You can buy <b>only one</b> upgrade in each cave. After a purchase, its other two disappear.</li>
<li>Some upgrades need something first, like a bow or a candle. Others only appear in the first or second cave you find.</li>
</ul>
<div class="hint"><b>HINT</b> The old men's hints about upgrades only mention ones that this seed can actually sell.</div>
</section>''')

# ---------------- catalog
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 1</h1>
<div class="ups">{up_rows(UP[1][:8])}</div></section>''')
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 1 (CONT.)</h1>
<div class="ups">{up_rows(UP[1][8:])}</div></section>''')
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 2</h1>
<div class="ups">{up_rows(UP[2][:7])}</div></section>''')
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 2 (CONT.)</h1>
<div class="ups">{up_rows(UP[2][7:])}</div></section>''')
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 3</h1>
<div class="ups">{up_rows(UP[3][:6])}</div></section>''')
P(f'''<section class="page"><h1 class="band">UPGRADE CATALOG: TIER 3 (CONT.)</h1>
<div class="ups">{up_rows(UP[3][6:])}</div></section>''')

# ---------------- snubber & zombie
P(f'''<section class="page"><h1 class="band">HEART SNUBBER AND ZOMBIE LINK</h1>
<div class="feat"><img src="{ICON['heart snubber']}"><div><h2>Heart Snubber <span class="pr">200<i class="rp"></i></span></h2>
<p>Only sold in the second upgrade cave you find, to a Link with 3 hearts or fewer. Link stays at <b>3 hearts for good</b>, but his level keeps climbing. From level 4 his sword's power grows with him, up to 8. No new swords or sword upgrades are offered after that, and the hearts row shows a sword for every 2 levels.</p></div></div>
<div class="feat"><img src="{ICON['zombie link']}"><div><h2>Zombie Link <span class="pr">75<i class="rp"></i></span></h2>
<p>Rare. Only for a Link with exactly 3 hearts, no ring and no Regeneration. Link turns undead: his life drops to nothing (he keeps his containers) on purchase and after every continue.</p>
<ul>
<li>Healing hurts: a potion drains half his hearts, a fairy 3, a heart 1.</li>
<li>Sword and wand swings deal <b>double</b>. Hits on Darknuts, Moblins, Goriyas, Lynels, Ropes and Wizzrobes heal him.</li>
<li>He takes double damage, but only half from the undead (Pols Voice, Gibdos, Ghinis, Stalfos).</li>
<li>Rings are never offered. Find the <b>Brain Potion</b> to refill him.</li>
</ul></div></div>
</section>''')

# ---------------- triforce caves
P(f'''<section class="page"><h1 class="band">THE TRIFORCE CAVES</h1>
<div class="two">{shot("img/tri4.png", "The 4-triforce cave.")}{shot("img/tri8.png", "The 8-triforce cave.")}</div>
<h2>4 Triforce Pieces</h2>
<p>This old man rewards 4 triforce pieces with the first item Link is missing. Once he has the white sword, that's a book (red, then blue). Otherwise the white sword, then the bow, arrows, wand, ladder, recorder, bracelet, raft, book, boomerang and more.</p>
<h2>All 8 Pieces</h2>
<p>This old man gives the first item from this list that Link can still use:</p>
<p class="list">Silver arrows, magic key, book (red, then blue), sword (white, then magical), ring (blue, then red), bow, ladder, recorder, power bracelet, raft, wand. With everything, a red potion.</p>
<div class="hint"><b>HINT</b> Each triforce cave gives its reward once.</div>
</section>''')

# ---------------- secret modes
P(f'''<section class="page"><h1 class="band">SECRET MODES</h1>
<p>Two secret modes are hidden in every game. How to find them is up to you. Some old men may know a thing or two.</p>
<h2>Swordless</h2>
<p>No sword for Link. Every offer of the white or magical sword becomes a bomb upgrade while Link holds fewer than 32 bombs.</p>
<h2>Hard Mode</h2>
<p>Link loses 2 heart containers (at least 1 is left). A heart container now takes 100 XP, and enemies grow stronger 3 hearts sooner.</p>
<div class="hint"><b>HINT</b> Some old men know more than they say.</div>
</section>''')

# ---------------- end
P(f'''<section class="page"><h1 class="band">THE END OF YOUR QUEST</h1>
<p>After the credits, press <b>START</b> to see your final report. START flips between its two pages and SELECT goes on.</p>
<div class="two">{shot("img/st_p1.png", "Page 1: every dungeon's nickname and its treasure.")}{shot("img/st_p2.png", "Page 2: time, cards, upgrades and inventory.")}</div>
<p>Page 1 lists Levels 1-9 and Shrines A-D with their nicknames and the item each old man or prize gave. Page 2 shows your time from the start of the file, your old men cards, the upgrades you bought and everything you carried.</p>
<div class="hint"><b>RACE</b> Same seed, same game: compare times with friends whose four-picture code matches yours.</div>
</section>''')

# ---------------- tips
P(f'''<section class="page"><h1 class="band">OLD MEN'S HINTS AND TIPS</h1>
<ul class="tips">
<li>Levels 1-8 all hold an old man. Seek them out.</li>
<li>Shrines A-D have a prize if you make it to the end.</li>
<li>Blue Dodongos don't mind smoke.</li>
<li>The blue candle can only burn brown bushes.</li>
<li>Don't forget the push block in west Death Mountain.</li>
<li>Something is under the push block east of the waterfall.</li>
<li>Orange Gibdos are fast!</li>
<li>Blue Pols Voice can only be damaged with bombs.</li>
<li>Have you ever tried to poison that meat you have?</li>
<li>Grow too strong and Gleeok sees red.</li>
</ul>
<div class="end">GOOD LUCK, HERO!</div>
<p class="small">Legend of Link is a free fan project and is not affiliated with or endorsed by Nintendo. You need your own copy of The Legend of Zelda (USA) to play.</p>
</section>''')

def find(mark):
    return next(i for i, pg in enumerate(pages) if ('class="band">' + mark) in pg)
rows = "".join(f'<div class="tr"><span>{html.escape(t)}</span><span class="dots"></span><span>{find(m) + 1}</span></div>' for t, m in toc)
pages[1] = pages[1].replace("@@TOC@@", rows)
pages[:] = [pg.replace("@@TRI@@", str(find("THE TRIFORCE CAVES") + 1)).replace("@@CARDS@@", str(find("OLD MEN CARDS") + 1)) for pg in pages]
for i, p in enumerate(pages):
    if i:
        pages[i] = p.replace("</section>", f'<div class="pg">{i + 1}</div></section>')

css = open(os.path.join(HERE, "manual.css")).read()
# on screen: the pages stacked on a dark desk, scaled down to fit a phone
fit = """<script>(function(){function f(){var w=document.documentElement.clientWidth,s=Math.min(1,(w-24)/528);
document.querySelector('.book').style.zoom=s;}f();addEventListener('resize',f);})();</script>"""
doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Legend of Link Instruction Booklet</title><style>{css}</style></head>
<body><div class="book">{"".join(pages)}</div>{fit}</body></html>'''
open(os.path.join(OUT, "index.html"), "w").write(doc)
print(len(pages), "pages")
