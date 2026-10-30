"""Hand-curated world-knowledge tables for KHOP / KNOWLEDGE / CONTEXT (PLAN_R §7). Every row is unambiguous textbook
knowledge (one capital, one main currency, one continent unless ``transcontinental``, one main language unless
None). PLAN_R asked for Wikidata sampling with a frequency floor; this is the offline substitute (deviation recorded
in README.md): 52 countries, 40 landmarks, 40/17 elements, 40/40 scientists/composers, 40/40 mammals/birds.

Country row: name, capital, currency, continent, language, other_city (a well-known non-capital city of the same
country, used for the "not a capital" class and the R-C2-style false capital), landmark (None when no landmark is
unambiguous AND free of the country/capital name), landmark_city, landmark_in_capital, transcontinental.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    name: str
    capital: str | None
    currency: str
    continent: str
    language: str | None
    other_city: str
    landmark: str | None = None
    landmark_city: str | None = None
    landmark_in_capital: bool = False
    transcontinental: bool = False


COUNTRIES: list[Country] = [
    # Europe
    Country("France", "Paris", "the euro", "Europe", "French", "Marseille", "the Louvre", "Paris", True),
    Country("Italy", "Rome", "the euro", "Europe", "Italian", "Milan", "the Colosseum", "Rome", True),
    Country("Spain", "Madrid", "the euro", "Europe", "Spanish", "Barcelona", "the Sagrada Família", "Barcelona", False),
    Country("Germany", "Berlin", "the euro", "Europe", "German", "Munich", "the Brandenburg Gate", "Berlin", True),
    Country("the United Kingdom", "London", "the pound sterling", "Europe", "English", "Manchester", "Big Ben", "London", True),
    Country("Greece", "Athens", "the euro", "Europe", "Greek", "Thessaloniki", "the Acropolis", "Athens", True),
    Country("Portugal", "Lisbon", "the euro", "Europe", "Portuguese", "Porto", "the Jerónimos Monastery", "Lisbon", True),
    Country("the Netherlands", "Amsterdam", "the euro", "Europe", "Dutch", "Rotterdam", "the Rijksmuseum", "Amsterdam", True),
    Country("Belgium", "Brussels", "the euro", "Europe", None, "Antwerp", "the Atomium", "Brussels", True),
    Country("Austria", "Vienna", "the euro", "Europe", "German", "Graz", "Schönbrunn Palace", "Vienna", True),
    Country("Switzerland", "Bern", "the Swiss franc", "Europe", None, "Zurich"),
    Country("Sweden", "Stockholm", "the Swedish krona", "Europe", "Swedish", "Gothenburg", "the Vasa Museum", "Stockholm", True),
    Country("Norway", "Oslo", "the Norwegian krone", "Europe", "Norwegian", "Bergen"),
    Country("Denmark", "Copenhagen", "the Danish krone", "Europe", "Danish", "Aarhus", "the Little Mermaid statue", "Copenhagen", True),
    Country("Finland", "Helsinki", "the euro", "Europe", "Finnish", "Tampere"),
    Country("Poland", "Warsaw", "the złoty", "Europe", "Polish", "Kraków", "Wawel Castle", "Kraków", False),
    Country("the Czech Republic", "Prague", "the Czech koruna", "Europe", "Czech", "Brno", "Charles Bridge", "Prague", True),
    Country("Hungary", "Budapest", "the forint", "Europe", "Hungarian", "Debrecen"),
    Country("Ireland", "Dublin", "the euro", "Europe", "English", "Cork", "the Cliffs of Moher", "Liscannor", False),
    Country("Iceland", "Reykjavík", "the Icelandic króna", "Europe", "Icelandic", "Akureyri", "the Blue Lagoon", "Grindavík", False),
    Country("Russia", "Moscow", "the ruble", "Europe", "Russian", "Saint Petersburg", "the Kremlin", "Moscow", True, True),
    Country("Turkey", "Ankara", "the Turkish lira", "Asia", "Turkish", "Istanbul", "Hagia Sophia", "Istanbul", False, True),
    # Asia
    Country("Japan", "Tokyo", "the yen", "Asia", "Japanese", "Osaka", "Mount Fuji", "Fujinomiya", False),
    Country("China", "Beijing", "the yuan", "Asia", "Mandarin Chinese", "Shanghai", "the Forbidden City", "Beijing", True),
    Country("India", "New Delhi", "the Indian rupee", "Asia", "Hindi", "Mumbai", "the Taj Mahal", "Agra", False),
    Country("South Korea", "Seoul", "the won", "Asia", "Korean", "Busan", "Gyeongbokgung Palace", "Seoul", True),
    Country("Thailand", "Bangkok", "the baht", "Asia", "Thai", "Chiang Mai", "Wat Arun", "Bangkok", True),
    Country("Vietnam", "Hanoi", "the dong", "Asia", "Vietnamese", "Ho Chi Minh City", "Ha Long Bay", "Ha Long", False),
    Country("Indonesia", "Jakarta", "the rupiah", "Asia", "Indonesian", "Surabaya", "Borobudur", "Magelang", False),
    Country("Malaysia", "Kuala Lumpur", "the ringgit", "Asia", "Malay", "George Town", "the Petronas Towers", "Kuala Lumpur", True),
    Country("the Philippines", "Manila", "the Philippine peso", "Asia", "Filipino", "Cebu City"),
    Country("Cambodia", "Phnom Penh", "the riel", "Asia", "Khmer", "Siem Reap", "Angkor Wat", "Siem Reap", False),
    Country("Pakistan", "Islamabad", "the Pakistani rupee", "Asia", "Urdu", "Karachi"),
    Country("Iran", "Tehran", "the rial", "Asia", "Persian", "Isfahan", "Persepolis", "Marvdasht", False),
    Country("Saudi Arabia", "Riyadh", "the riyal", "Asia", "Arabic", "Jeddah", "the Kaaba", "Mecca", False),
    Country("the United Arab Emirates", "Abu Dhabi", "the dirham", "Asia", "Arabic", "Dubai", "the Burj Khalifa", "Dubai", False),
    Country("Jordan", "Amman", "the Jordanian dinar", "Asia", "Arabic", "Aqaba", "Petra", "Wadi Musa", False),
    Country("Nepal", "Kathmandu", "the Nepalese rupee", "Asia", "Nepali", "Pokhara"),
    Country("Bangladesh", "Dhaka", "the taka", "Asia", "Bengali", "Chittagong"),
    # Africa
    Country("Egypt", "Cairo", "the Egyptian pound", "Africa", "Arabic", "Alexandria", "the Pyramids of Giza", "Giza", False),
    Country("Kenya", "Nairobi", "the Kenyan shilling", "Africa", "Swahili", "Mombasa"),
    Country("Nigeria", "Abuja", "the naira", "Africa", "English", "Lagos"),
    Country("Morocco", "Rabat", "the Moroccan dirham", "Africa", "Arabic", "Casablanca"),
    Country("Ethiopia", "Addis Ababa", "the birr", "Africa", "Amharic", "Dire Dawa"),
    Country("Ghana", "Accra", "the cedi", "Africa", "English", "Kumasi"),
    Country("Senegal", "Dakar", "the CFA franc", "Africa", "French", "Saint-Louis"),
    # Americas
    Country("the United States", "Washington", "the US dollar", "North America", "English", "New York City", "the Statue of Liberty", "New York City", False),
    Country("Canada", "Ottawa", "the Canadian dollar", "North America", None, "Toronto", "the CN Tower", "Toronto", False),
    Country("Mexico", "Mexico City", "the Mexican peso", "North America", "Spanish", "Guadalajara", "Chichen Itza", "Tinum", False),
    Country("Cuba", "Havana", "the Cuban peso", "North America", "Spanish", "Santiago de Cuba"),
    Country("Brazil", "Brasília", "the real", "South America", "Portuguese", "São Paulo", "Christ the Redeemer", "Rio de Janeiro", False),
    Country("Argentina", "Buenos Aires", "the Argentine peso", "South America", "Spanish", "Córdoba"),
    Country("Chile", "Santiago", "the Chilean peso", "South America", "Spanish", "Valparaíso", "the moai statues of Easter Island", "Hanga Roa", False),
    Country("Peru", "Lima", "the sol", "South America", "Spanish", "Cusco", "Machu Picchu", "Aguas Calientes", False),
    Country("Colombia", "Bogotá", "the Colombian peso", "South America", "Spanish", "Medellín"),
    # Oceania
    Country("Australia", "Canberra", "the Australian dollar", "Oceania", "English", "Sydney", "the Sydney Opera House", "Sydney", False),
    Country("New Zealand", "Wellington", "the New Zealand dollar", "Oceania", "English", "Auckland"),
]

BY_NAME: dict[str, Country] = {c.name: c for c in COUNTRIES}


def bare(name: str) -> str:
    """'the United Kingdom' -> 'United Kingdom' (for candidate strings and in-text checks)."""
    return name[4:] if name.startswith("the ") else name


def with_landmark(in_capital: bool | None = None) -> list[Country]:
    out = [c for c in COUNTRIES if c.landmark]
    if in_capital is not None:
        out = [c for c in out if c.landmark_in_capital == in_capital]
    return out


# ------------------------------------------------------------------ elements (metalloids excluded)
METALS = ["Lithium", "Sodium", "Potassium", "Magnesium", "Calcium", "Iron", "Copper", "Zinc", "Silver", "Gold", "Platinum",
          "Aluminium", "Nickel", "Cobalt", "Chromium", "Manganese", "Titanium", "Tin", "Lead", "Mercury", "Tungsten",
          "Uranium", "Barium", "Strontium", "Caesium", "Rubidium", "Vanadium", "Palladium", "Cadmium", "Bismuth", "Gallium",
          "Indium", "Thallium", "Osmium", "Iridium", "Rhodium", "Ruthenium", "Molybdenum", "Zirconium", "Niobium"]
NONMETALS = ["Hydrogen", "Helium", "Carbon", "Nitrogen", "Oxygen", "Fluorine", "Neon", "Phosphorus", "Sulfur", "Chlorine",
             "Argon", "Selenium", "Bromine", "Krypton", "Iodine", "Xenon", "Radon"]

# ------------------------------------------------------------------ people
SCIENTISTS = ["Isaac Newton", "Albert Einstein", "Marie Curie", "Charles Darwin", "Galileo Galilei", "Nikola Tesla", "Niels Bohr",
              "Max Planck", "Richard Feynman", "Erwin Schrödinger", "Werner Heisenberg", "Michael Faraday", "James Clerk Maxwell",
              "Louis Pasteur", "Gregor Mendel", "Alexander Fleming", "Dmitri Mendeleev", "Johannes Kepler", "Nicolaus Copernicus",
              "Enrico Fermi", "Paul Dirac", "Stephen Hawking", "Rosalind Franklin", "Francis Crick", "James Watson", "Carl Linnaeus",
              "Antoine Lavoisier", "Robert Boyle", "Edwin Hubble", "Alan Turing", "Ada Lovelace", "Blaise Pascal", "Leonhard Euler",
              "Carl Friedrich Gauss", "Archimedes", "Tycho Brahe", "Ernest Rutherford", "Lise Meitner", "Linus Pauling", "Robert Hooke"]
COMPOSERS = ["Johann Sebastian Bach", "Wolfgang Amadeus Mozart", "Ludwig van Beethoven", "Franz Schubert", "Frédéric Chopin",
             "Franz Liszt", "Richard Wagner", "Giuseppe Verdi", "Johannes Brahms", "Pyotr Ilyich Tchaikovsky", "Antonín Dvořák",
             "Claude Debussy", "Maurice Ravel", "Igor Stravinsky", "Sergei Rachmaninoff", "Gustav Mahler", "Antonio Vivaldi",
             "George Frideric Handel", "Joseph Haydn", "Felix Mendelssohn", "Robert Schumann", "Hector Berlioz", "Edvard Grieg",
             "Jean Sibelius", "Giacomo Puccini", "Gioachino Rossini", "Georges Bizet", "Camille Saint-Saëns", "Modest Mussorgsky",
             "Nikolai Rimsky-Korsakov", "Bedřich Smetana", "Arnold Schoenberg", "Dmitri Shostakovich", "Sergei Prokofiev",
             "Béla Bartók", "Leoš Janáček", "Claudio Monteverdi", "Henry Purcell", "Edward Elgar", "Ralph Vaughan Williams"]

# ------------------------------------------------------------------ animals
MAMMALS = ["dog", "cat", "horse", "cow", "sheep", "goat", "pig", "lion", "tiger", "leopard", "cheetah", "elephant", "giraffe",
           "zebra", "hippopotamus", "rhinoceros", "gorilla", "chimpanzee", "orangutan", "kangaroo", "koala", "wolf", "fox",
           "bear", "deer", "moose", "rabbit", "squirrel", "beaver", "otter", "dolphin", "whale", "seal", "walrus", "bat",
           "camel", "llama", "hedgehog", "raccoon", "badger"]
BIRDS = ["eagle", "hawk", "falcon", "owl", "sparrow", "robin", "pigeon", "crow", "raven", "magpie", "swan", "goose", "duck",
         "penguin", "ostrich", "emu", "flamingo", "pelican", "heron", "stork", "parrot", "macaw", "toucan", "hummingbird",
         "woodpecker", "kingfisher", "peacock", "swallow", "chicken", "pheasant", "quail", "seagull", "albatross", "puffin",
         "vulture", "condor", "cuckoo", "nightingale", "canary", "finch"]

# ------------------------------------------------------------------ names (one whitespace token, common, gendered for pronoun facts)
MALE_NAMES = ["Adam", "Paul", "Eric", "Luke", "John", "Mark", "Tom", "James", "Peter", "David", "Simon", "Henry"]
FEMALE_NAMES = ["Emma", "Anna", "Lisa", "Kate", "Mary", "Sarah", "Laura", "Julia", "Clara", "Alice", "Helen", "Rose"]
NAMES = MALE_NAMES + FEMALE_NAMES


def check_tables() -> list[str]:
    """Static integrity: unique names/capitals/landmarks, landmark free of country and capital words."""
    problems: list[str] = []
    names = [c.name for c in COUNTRIES]
    if len(set(names)) != len(names):
        problems.append("duplicate country")
    caps = [c.capital for c in COUNTRIES if c.capital]
    if len(set(caps)) != len(caps):
        problems.append("duplicate capital")
    lms = [c.landmark for c in COUNTRIES if c.landmark]
    if len(set(lms)) != len(lms):
        problems.append("duplicate landmark")
    for c in COUNTRIES:
        if c.landmark:
            low = c.landmark.lower()
            for w in (bare(c.name).lower(), (c.capital or "").lower()):
                if w and w in low:
                    problems.append(f"{c.name}: landmark {c.landmark!r} names the country or capital")
        if c.landmark_in_capital and c.landmark_city != c.capital:
            problems.append(f"{c.name}: landmark_in_capital but city {c.landmark_city} != {c.capital}")
    for a, b in ((METALS, NONMETALS), (SCIENTISTS, COMPOSERS), (MAMMALS, BIRDS), (MALE_NAMES, FEMALE_NAMES)):
        if set(a) & set(b) or len(set(a)) != len(a) or len(set(b)) != len(b):
            problems.append("overlapping or duplicate class lists")
    return problems
