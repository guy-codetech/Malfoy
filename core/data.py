import random

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_WEIGHTS = {"common": 62.0, "uncommon": 24.0, "rare": 10.0, "epic": 3.5, "legendary": 0.5}
RARITY_LABEL = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "epic": "Epic",
    "legendary": "Legendary",
}

_ANIMALS = [
    ("mouse", "Mouse", "common", 14),
    ("rabbit", "Rabbit", "common", 18),
    ("duck", "Duck", "common", 20),
    ("hen", "Hen", "common", 16),
    ("frog", "Frog", "common", 22),
    ("fox", "Fox", "uncommon", 48),
    ("owl", "Owl", "uncommon", 56),
    ("deer", "Deer", "uncommon", 62),
    ("hedgehog", "Hedgehog", "uncommon", 44),
    ("panda", "Panda", "rare", 160),
    ("wolf", "Wolf", "rare", 180),
    ("otter", "Otter", "rare", 140),
    ("tiger", "Tiger", "epic", 480),
    ("snow_leopard", "Snow Leopard", "epic", 560),
    ("unicorn", "Unicorn", "legendary", 1900),
    ("phoenix", "Phoenix", "legendary", 2400),
]

_FISH = [
    ("minnow", "Minnow", "common", 12),
    ("carp", "Carp", "common", 18),
    ("perch", "Perch", "common", 20),
    ("trout", "Trout", "uncommon", 46),
    ("salmon", "Salmon", "uncommon", 58),
    ("bass", "Bass", "uncommon", 52),
    ("koi", "Koi", "rare", 170),
    ("pufferfish", "Pufferfish", "rare", 150),
    ("swordfish", "Swordfish", "epic", 500),
    ("shark", "Shark", "epic", 580),
    ("golden_whale", "Golden Whale", "legendary", 2200),
    ("moon_jelly", "Moon Jelly", "legendary", 1800),
]

CATCHES = {}
POOLS = {"hunt": {r: [] for r in RARITY_ORDER}, "fish": {r: [] for r in RARITY_ORDER}}

for _kind, _rows in (("hunt", _ANIMALS), ("fish", _FISH)):
    for _id, _name, _rarity, _value in _rows:
        CATCHES[_id] = {"id": _id, "name": _name, "rarity": _rarity, "value": _value, "kind": _kind}
        POOLS[_kind][_rarity].append(_id)


def roll_catch(kind, lucky=False):
    weights = dict(RARITY_WEIGHTS)
    if lucky:
        for rarity in ("rare", "epic", "legendary"):
            weights[rarity] *= 3
    rarity = random.choices(RARITY_ORDER, weights=[weights[r] for r in RARITY_ORDER])[0]
    return CATCHES[random.choice(POOLS[kind][rarity])]


SHOP = {
    "padlock": {
        "name": "Padlock",
        "price": 1500,
        "icon": "LOCK",
        "desc": "Blocks the next robbery attempt against you.",
        "aliases": ["lock"],
    },
    "lootbox": {
        "name": "Lootbox",
        "price": 600,
        "icon": "GIFT",
        "desc": "Open it for a surprise payout between 150 and 3,000 coins.",
        "aliases": ["box", "loot"],
    },
    "bank_note": {
        "name": "Bank Note",
        "price": 4000,
        "icon": "BANK",
        "desc": "Permanently adds 10,000 to your bank capacity.",
        "aliases": ["banknote", "note"],
    },
    "lucky_charm": {
        "name": "Lucky Charm",
        "price": 2500,
        "icon": "STAR",
        "desc": "Triples rare catch odds on your next hunt or fish.",
        "aliases": ["charm", "luck"],
    },
}

LOOT_TABLE = [(150, 40), (400, 30), (900, 18), (1600, 8), (3000, 4)]

JOBS = [
    "delivered a stack of fresh dango",
    "served tea at a cozy cafe",
    "walked a very fluffy dog",
    "repaired a wobbly lantern",
    "sorted parcels at the post office",
    "painted a mural on the town wall",
    "tuned a music box for a customer",
    "gardened at the moonlit greenhouse",
    "baked a batch of mochi for the festival",
    "helped a traveller find their way",
]

BEG_LINES = [
    "A kind stranger dropped some coins in your hand",
    "A passing cat left a few coins at your feet",
    "A baker felt generous and gave you a tip",
    "A tourist thought you were a street performer",
]

BEG_FAILS = [
    "Nobody noticed you this time.",
    "A pigeon stole your hat and ran away.",
    "Everyone walked past with their headphones on.",
]

CRIME_WINS = [
    "pulled off a harmless prank heist at the candy store",
    "sold counterfeit lucky charms to a tourist",
    "swapped the museum cat statue and walked away",
    "won a shady card game behind the arcade",
]

CRIME_FAILS = [
    "got caught sneaking into the festival without a ticket",
    "tripped over the alarm while grabbing a golden fish",
    "were spotted by the night watch and had to pay a fine",
]

EIGHT_BALL = [
    "It is certain.",
    "Without a doubt.",
    "Yes, definitely.",
    "You may rely on it.",
    "Most likely.",
    "Signs point to yes.",
    "Ask again later.",
    "Cannot predict right now.",
    "Better not tell you now.",
    "Don't count on it.",
    "My sources say no.",
    "Very doubtful.",
]


def find_shop_item(query):
    q = query.lower().strip().replace(" ", "_")
    for key, item in SHOP.items():
        if q == key or q == item["name"].lower().replace(" ", "_") or q in item["aliases"]:
            return key
    return None
