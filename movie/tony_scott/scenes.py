"""
Tony Scott documentary — 13-scene screenplay data.

Each scene has: title, act, description, archival_sources,
interview_targets, visual_direction, and emotional_beat.
"""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Scene:
    number: int
    title: str
    act: str
    logline: str
    archival_sources: list[str]
    interview_targets: list[str]
    visual_direction: str
    emotional_beat: str
    vo_text: str = ""       # populated by narrator.py via Ollama


SCENES: list[Scene] = [
    Scene(
        number=1,
        title="Stockton-on-Tees",
        act="Act 1",
        logline="Industrial northeast England, 1944. Two boys born into iron and coal country who will spend their lives chasing light.",
        archival_sources=[
            "Getty Images: Stockton-on-Tees 1940s-50s industrial footage",
            "ITV regional archive: northeast England post-war footage",
            "West Hartlepool College of Art: institutional records",
        ],
        interview_targets=[
            "Ridley Scott — childhood memories",
            "Local Stockton historians / friends of the family",
        ],
        visual_direction=(
            "Black and white. Still frames. Slow dissolves. "
            "The visual language of memory — slightly out of focus at edges. "
            "Then a SUDDEN cut to color — Tony's first commercial."
        ),
        emotional_beat="Origin. Where does the hunger for beauty come from when you grow up in a place that has none?",
    ),
    Scene(
        number=2,
        title="The Royal College of Art",
        act="Act 1",
        logline="London, 1964-1969. Tony makes his student film. It is haunting and nothing like Top Gun.",
        archival_sources=[
            "RCA Special Collections: student records, One of the Missing (1969)",
            "BAFTA archive: nomination records",
            "British short film database",
        ],
        interview_targets=[
            "RCA faculty who were there in the 1960s",
            "Fellow students from the 1964-69 cohort",
        ],
        visual_direction=(
            "Clip from One of the Missing alongside the student who made it. "
            "The dissonance is the point."
        ),
        emotional_beat="The road not taken. He was capable of something quieter. He chose something else.",
    ),
    Scene(
        number=3,
        title="The Commercial Years",
        act="Act 1",
        logline="RSA Films. Hundreds of commercials. The Chanel No. 5 ad with Catherine Deneuve. Learning the grammar of desire.",
        archival_sources=[
            "RSA Films archive: commercial reels 1970s-1982",
            "Campaign magazine UK: advertising trade coverage",
            "Chanel corporate archive: production records",
        ],
        interview_targets=[
            "RSA Films staff from the 1970s",
            "UK advertising directors who worked alongside Scott",
        ],
        visual_direction=(
            "The Chanel ad plays full. 30 seconds of pure Tony Scott aesthetics — "
            "in 1977. The DNA is all there: beautiful light, desire, speed."
        ),
        emotional_beat="Craft before art. He learned to make people feel things in 30 seconds.",
    ),
    Scene(
        number=4,
        title="The Hunger",
        act="Act 1",
        logline="His debut feature flops. The critics who will haunt him show up early.",
        archival_sources=[
            "MGM/UA archive: The Hunger production materials",
            "Contemporary reviews: Roger Ebert, Pauline Kael, Vincent Canby",
            "Box office records: Variety, 1983",
        ],
        interview_targets=[
            "David Bowie documentary footage (Bowie died 2016 — archival only)",
            "Susan Sarandon: working with Scott",
            "Catherine Deneuve: the Chanel relationship leading to The Hunger",
        ],
        visual_direction=(
            "Clip from The Hunger — the opening sequence with Bauhaus. "
            "Then a newspaper review, read aloud. Then Tony's face in a later interview."
        ),
        emotional_beat="The first wound. He wanted to be taken seriously. He wasn't.",
    ),
    Scene(
        number=5,
        title="Top Gun",
        act="Act 2a",
        logline="1986. $356 million. The Navy's best recruitment tool. The film that defines and traps him.",
        archival_sources=[
            "Paramount Pictures: Top Gun production archive",
            "DoD/Navy: cooperation agreement (FOIA)",
            "US Navy recruitment statistics 1986-87",
            "Contemporary reviews and box office records",
            "Tom Cruise and Bruckheimer interviews from the era",
        ],
        interview_targets=[
            "Jerry Bruckheimer: the production story",
            "Tom Cruise (archival footage — relationship soured post-production)",
            "Phil Strub (former DoD Hollywood liaison): the Navy deal",
            "Kelly McGillis, Val Kilmer (surviving cast)",
        ],
        visual_direction=(
            "F-14s at golden hour. The shot everyone remembers. "
            "Then: a Navy recruitment office. A line around the block. "
            "Cut to: a scathing Roger Ebert review."
        ),
        emotional_beat=(
            "The trap springs. The biggest success of his career "
            "becomes the ceiling above which critics will never place him."
        ),
    ),
    Scene(
        number=6,
        title="The Bruckheimer Machine",
        act="Act 2a",
        logline="Beverly Hills Cop II. Days of Thunder. The Last Boy Scout. The commercial director label hardens.",
        archival_sources=[
            "Bruckheimer Productions archive",
            "True Romance: original script vs. released film comparison",
            "Quentin Tarantino interviews about the ending dispute",
        ],
        interview_targets=[
            "Jerry Bruckheimer",
            "Quentin Tarantino (has spoken publicly about the True Romance dispute)",
            "Shane Black (Last Boy Scout writer)",
        ],
        visual_direction=(
            "Split screen: Tony Scott's True Romance ending (they drive away) vs. "
            "Tarantino's preferred ending (Clarence dies). "
            "Two directors. One film. One compromise."
        ),
        emotional_beat="He made movies for the audience. The audience loved them. That should be enough.",
    ),
    Scene(
        number=7,
        title="Crimson Tide",
        act="Act 2a",
        logline="1995. Denzel Washington. Gene Hackman. The submarine film that changes what critics think is possible for Tony Scott.",
        archival_sources=[
            "Disney/Hollywood Pictures: Crimson Tide production",
            "Hans Zimmer: score production materials",
            "Contemporary reviews — notable for relative critical warmth",
        ],
        interview_targets=[
            "Denzel Washington: the first Scott collaboration",
            "Hans Zimmer: composing for Scott",
            "Gene Hackman (archival)",
        ],
        visual_direction=(
            "The submarine sequences. Tight. Claustrophobic. "
            "Nothing like Top Gun. Critics notice."
        ),
        emotional_beat="He could do anything. The tragedy is that nobody would let him prove it.",
    ),
    Scene(
        number=8,
        title="Man on Fire / The Style Wars",
        act="Act 2b",
        logline="2004. The style is now fully unleashed. Multiple film stocks. Skip-bleach. 8fps and 96fps in the same scene. Critics call it unwatchable. Audiences make it a hit.",
        archival_sources=[
            "20th Century Fox: Man on Fire production",
            "American Cinematographer: interview with DP Dariusz Wolski",
            "Film criticism: AO Scott, Manohla Dargis New York Times reviews",
        ],
        interview_targets=[
            "Dariusz Wolski (DP): the technical decisions",
            "Daniel Mindel (DP): later films",
            "Chris Lebenzon (editor): what the cutting room felt like",
            "Denzel Washington: working in this visual environment",
        ],
        visual_direction=(
            "A technical breakdown of one scene — frame by frame — showing "
            "how many different film stocks and processes are in a single minute. "
            "Then: the same scene, watched as an audience would watch it. "
            "It just FEELS right."
        ),
        emotional_beat=(
            "The gap between how critics describe his work and how it actually "
            "FEELS to watch it. That gap is the whole argument."
        ),
    ),
    Scene(
        number=9,
        title="The Ridley Comparison",
        act="Act 2b",
        logline="Two brothers. One critical consensus. What does it cost to live in your brother's shadow when you love him?",
        archival_sources=[
            "Interviews where they appear together (rare)",
            "Scott Free Productions history",
            "Academy Award history: Ridley's nominations, Tony's absence",
        ],
        interview_targets=[
            "Ridley Scott: speaking about Tony post-2012",
            "People who knew both of them",
        ],
        visual_direction=(
            "Side by side: a Ridley Scott frame and a Tony Scott frame from the same year. "
            "Both beautiful. Different languages."
        ),
        emotional_beat=(
            "The comparison wasn't Tony's idea. He never sought it. "
            "He was proud of Ridley. Whether Ridley's success cost him something "
            "personally is the question we cannot answer."
        ),
    ),
    Scene(
        number=10,
        title="Unstoppable",
        act="Act 2b",
        logline="2010. His last film. Denzel Washington. A runaway train. A kinetic masterpiece that grosses $167 million. His last shot.",
        archival_sources=[
            "20th Century Fox: Unstoppable production",
            "Final press interviews and junket footage",
        ],
        interview_targets=[
            "Denzel Washington: the last film",
            "Rosario Dawson: co-star",
            "Chris Lebenzon: the editing of the final film",
        ],
        visual_direction=(
            "The train. Always moving. Never stopping. "
            "He didn't know it was his last film. That matters."
        ),
        emotional_beat="He was still at the height of his powers. Whatever was coming for him, it wasn't about the work.",
    ),
    Scene(
        number=11,
        title="The Last Year",
        act="Act 3",
        logline="2011-2012. Tony Scott is developing The Warriors remake and other projects. He seems fine. He isn't.",
        archival_sources=[
            "Trade press coverage of The Warriors remake announcement",
            "Final public appearances",
            "Donna Scott's post-death interviews (select)",
        ],
        interview_targets=[
            "Donna W. Scott (wife)",
            "Close friends and collaborators willing to speak",
        ],
        visual_direction=(
            "No archival footage in this section. "
            "Static camera. Long takes. The absence of kinetic energy is deliberate."
        ),
        emotional_beat=(
            "We don't know. That's the honest answer. "
            "The film does not pretend to know what we cannot know."
        ),
    ),
    Scene(
        number=12,
        title="The Vincent Thomas Bridge",
        act="Act 3",
        logline="August 19, 2012. San Pedro, California. A bridge 185 feet above Los Angeles Harbor.",
        archival_sources=[
            "Los Angeles County coroner's report (public record)",
            "Los Angeles Times: coverage of his death",
            "AP wire photos of the bridge",
        ],
        interview_targets=[
            "Donna W. Scott",
            "Ridley Scott: immediate reaction",
        ],
        visual_direction=(
            "The bridge, present day. Shot at golden hour — the same light "
            "Tony Scott would have used. "
            "The camera does not look down. It looks out at the harbor. "
            "The light on the water. "
            "No music. "
            "Just the sound of wind and traffic."
        ),
        emotional_beat="This is not an explanation. It is a fact. Facts do not explain grief.",
    ),
    Scene(
        number=13,
        title="What He Left",
        act="Act 3",
        logline="The work. The reassessment. The argument that his films are better than we knew. The argument that they are exactly as good as his defenders always said.",
        archival_sources=[
            "Post-2012 critical retrospectives: The Guardian, New Yorker, etc.",
            "Letterboxd and online film community reassessments",
            "Cinematheque retrospectives",
        ],
        interview_targets=[
            "Film critics who have reassessed his work",
            "Directors he influenced",
            "Denzel Washington: final statement",
        ],
        visual_direction=(
            "Return to Stockton-on-Tees. "
            "A student at an art school, sketching. "
            "The light comes through a window the way Tony Scott would find it: "
            "oblique, excessive, beautiful. "
            "Slow push in on the student's hand moving across the paper. "
            "TITLE CARD: Tony Scott. 1944-2012. "
            "SECOND TITLE CARD: He made movies about feelings."
        ),
        emotional_beat="The answer to the question the film has been asking: he was right.",
    ),
]


def get_scene(number: int) -> Scene | None:
    return next((s for s in SCENES if s.number == number), None)
