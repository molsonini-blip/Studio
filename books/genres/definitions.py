"""
All book genre definitions.
Each genre specifies: description, style, target length, and Ollama prompting guidance.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GenreDef:
    name: str
    description: str
    style_notes: str
    books_per_series: int       # 20+ for romance, 10 for others
    chapters_per_book: int
    words_per_chapter: int
    series_prompt: str          # what to tell Ollama when generating series concept
    chapter_style: str          # tone/voice guidance for chapter writing
    references: list[str]       # comp titles / authors


GENRES: dict[str, GenreDef] = {

    "romance": GenreDef(
        name="romance",
        description="Dime-store romance novels — fast reads, high emotion, satisfying HEA endings",
        style_notes="Steamy but tasteful. Snappy dialogue. Alpha heroes, fierce heroines. Tropes welcome.",
        books_per_series=22,
        chapters_per_book=20,
        words_per_chapter=3000,
        series_prompt=(
            "Create a 22-book dime-store romance series. "
            "Give it a setting (small town, big city, ranch, billionaire world, military, etc.), "
            "a cast of recurring characters (town residents, family members, friends), "
            "and standalone couple per book. Each book focuses on one new couple "
            "from the community — their enemies-to-lovers / second chance / forced proximity story. "
            "The series should feel like one rich world readers want to live in."
        ),
        chapter_style=(
            "Write in third-person limited, alternating between hero and heroine POV. "
            "Prose should be fast-paced and emotionally engaging. "
            "Show physical attraction and emotional vulnerability. "
            "Each chapter should end with a hook or unresolved tension."
        ),
        references=["Nora Roberts", "Lisa Kleypas", "Julia Quinn", "Vi Keeland", "Penelope Ward"],
    ),

    "thriller": GenreDef(
        name="thriller",
        description="Psychological and action thrillers — page-turning suspense",
        style_notes="Tight pacing. High stakes. Twists that recontextualize everything. Morally complex.",
        books_per_series=10,
        chapters_per_book=25,
        words_per_chapter=2500,
        series_prompt=(
            "Create a 10-book thriller series with a recurring protagonist (detective, operative, "
            "journalist, or profiler). Each book is a standalone case but builds character arc. "
            "Set in a specific world (FBI, CIA, private investigator, crime journalist). "
            "Give the protagonist a compelling flaw or wound that drives them."
        ),
        chapter_style=(
            "Write in tight third-person or first-person. Short chapters, punchy sentences. "
            "Build dread gradually. Plant clues the reader won't recognize until the reveal. "
            "Every scene must either raise tension or reveal character — no filler."
        ),
        references=["Lee Child", "Gillian Flynn", "Thomas Harris", "Tess Gerritsen", "John Grisham"],
    ),

    "mystery": GenreDef(
        name="mystery",
        description="Classic whodunits and cozy mysteries — puzzle-forward storytelling",
        style_notes="Fair play clues. Satisfying solution. Eccentric detective. Strong sense of place.",
        books_per_series=10,
        chapters_per_book=22,
        words_per_chapter=2500,
        series_prompt=(
            "Create a 10-book mystery series with a recurring amateur or professional detective. "
            "Set it in a specific location that becomes a character itself "
            "(English village, American small town, Scottish island, Italian hill town, etc.). "
            "The detective should have a unique method, personality, and cast of recurring allies."
        ),
        chapter_style=(
            "Write in the tradition of classic mystery fiction. "
            "Introduce suspects with clear motives. Distribute clues fairly — the reader "
            "should be able to solve it in retrospect. "
            "Dialogue should reveal character. Setting should be vivid and atmospheric."
        ),
        references=["Agatha Christie", "Richard Osman", "Alexander McCall Smith", "Louise Penny"],
    ),

    "sci_fi": GenreDef(
        name="sci_fi",
        description="Science fiction — space opera, hard SF, dystopian, cyberpunk",
        style_notes="Big ideas. Plausible speculation. Character-driven despite the scale.",
        books_per_series=10,
        chapters_per_book=24,
        words_per_chapter=3000,
        series_prompt=(
            "Create a 10-book science fiction series. Choose a specific subgenre: "
            "space opera, hard SF, cyberpunk, dystopian, first contact, generation ship, etc. "
            "Build a consistent universe with rules, history, and political factions. "
            "The protagonist should change across the arc. Each book escalates the stakes."
        ),
        chapter_style=(
            "Write with a sense of wonder and dread in equal measure. "
            "Ground alien/future concepts in human emotional experience. "
            "Show don't tell the technology — let it emerge from action, not exposition. "
            "Build the world through details embedded in scene, not info-dumps."
        ),
        references=["Isaac Asimov", "Ursula K. Le Guin", "Andy Weir", "N.K. Jemisin", "William Gibson"],
    ),

    "horror": GenreDef(
        name="horror",
        description="Horror fiction — psychological, supernatural, body horror, cosmic dread",
        style_notes="Earn the scares. Build atmosphere. The unknown is scarier than the revealed.",
        books_per_series=10,
        chapters_per_book=22,
        words_per_chapter=2800,
        series_prompt=(
            "Create a 10-book horror series. Choose a consistent mythology or monster type "
            "(haunted locations, cursed bloodlines, cosmic entities, cults, psychological horror). "
            "Each book stands alone but expands the mythology. "
            "A recurring investigator or connected cast ties the books together."
        ),
        chapter_style=(
            "Write with slow dread building to visceral terror. "
            "Ground horror in the mundane — the familiar made wrong. "
            "Use sensory detail to make the horror tactile and real. "
            "Psychological horror should make the reader question what's real."
        ),
        references=["Stephen King", "Shirley Jackson", "Paul Tremblay", "Carmen Maria Machado"],
    ),

    "western": GenreDef(
        name="western",
        description="Western fiction — frontier justice, outlaws, gunslingers, the lawless West",
        style_notes="Spare prose. Moral clarity tested by gray situations. Landscape as character.",
        books_per_series=10,
        chapters_per_book=20,
        words_per_chapter=2500,
        series_prompt=(
            "Create a 10-book western series. Set it in a specific region and era "
            "(1870s Texas, Montana Territory, Arizona Territory, post-Civil War frontier). "
            "A recurring lawman, outlaw, or wanderer serves as protagonist. "
            "Each book is a standalone story but builds the character's legend."
        ),
        chapter_style=(
            "Write with economy and grit. Short sentences. Strong verbs. "
            "Let silence and landscape do heavy lifting. "
            "Characters reveal themselves through action, not introspection. "
            "Violence should feel real and consequential — not glorified."
        ),
        references=["Cormac McCarthy", "Elmore Leonard", "Larry McMurtry", "Louis L'Amour"],
    ),

    "fantasy": GenreDef(
        name="fantasy",
        description="Epic and urban fantasy — magic systems, quests, power and consequence",
        style_notes="Internally consistent world. Magic has cost. Characters earn their victories.",
        books_per_series=10,
        chapters_per_book=26,
        words_per_chapter=3500,
        series_prompt=(
            "Create a 10-book fantasy series with a fully realized world. "
            "Design a specific magic system with clear rules and limitations. "
            "Build political factions, history, and geography. "
            "The protagonist's arc should span all 10 books — from nobody to world-changer. "
            "Each book resolves a major conflict while advancing the overarching threat."
        ),
        chapter_style=(
            "Write epic fantasy in close third-person. "
            "World-building should emerge from character experience, not lecture. "
            "Action sequences should be choreographed and consequential. "
            "Emotional beats matter as much as plot beats. "
            "Make readers care about characters before putting them in danger."
        ),
        references=["Brandon Sanderson", "Patrick Rothfuss", "Robin Hobb", "N.K. Jemisin", "Joe Abercrombie"],
    ),

    "historical": GenreDef(
        name="historical",
        description="Historical fiction — specific eras brought to life through compelling characters",
        style_notes="Authentic period detail. Human stakes. The personal and the historical intertwined.",
        books_per_series=10,
        chapters_per_book=24,
        words_per_chapter=3000,
        series_prompt=(
            "Create a 10-book historical fiction series set in a specific era and location "
            "(Tudor England, Ancient Rome, Revolutionary France, WWI trenches, "
            "1920s Harlem, Silk Road medieval, Feudal Japan, etc.). "
            "Follow one family or connected cast across the series. "
            "Each book covers a pivotal moment in history through their eyes."
        ),
        chapter_style=(
            "Write with period-accurate detail woven naturally into scene. "
            "Avoid anachronistic thinking — characters should see the world through their era's lens. "
            "Show how large historical forces ripple into private lives. "
            "Dialogue should feel of the period without being incomprehensible."
        ),
        references=["Hilary Mantel", "Ken Follett", "Anthony Burgess", "Colleen McCullough", "Philippa Gregory"],
    ),
}


def get_genre(name: str) -> GenreDef:
    if name not in GENRES:
        raise ValueError(f"Unknown genre '{name}'. Available: {list(GENRES)}")
    return GENRES[name]
