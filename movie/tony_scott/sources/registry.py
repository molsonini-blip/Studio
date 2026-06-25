"""
Tony Scott Documentary — Source Material Registry

Tracks every source used in research, writing, or production.
Maintained for legal clearance, fair use documentation, and copyright compliance.

Legal framework:
  - Fair Use: 17 U.S.C. § 107 — commentary, criticism, education, transformative use
  - Defamation: all factual claims are sourced and verifiable
  - Right of Publicity: living subjects will require release forms before distribution
  - Archival Footage: tracked separately, requires studio/archive licensing
  - Music: tracked separately, requires sync + master licenses

Usage:
  from movie.tony_scott.sources.registry import Registry, Source, SourceType, UseType

  reg = Registry.load()
  reg.add(Source(
      url="https://...",
      title="Tony Scott: Man on Fire",
      author="Sight & Sound",
      publisher="BFI",
      date_published="2004-09-01",
      source_type=SourceType.ARTICLE,
      use_type=UseType.REFERENCE,
      fair_use_basis="Commentary and criticism of director's stated methods",
      content_summary="Scott describes his technique choices on Man on Fire",
  ))
  reg.save()

  # Export legal report
  reg.export_legal_report("sources/legal_report.md")
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

REGISTRY_FILE = Path(__file__).parent / "sources.json"
LEGAL_REPORT_FILE = Path(__file__).parent / "legal_report.md"


class SourceType(str, Enum):
    ARTICLE = "article"              # News/magazine article
    INTERVIEW = "interview"          # Published interview with subject/crew
    ACADEMIC = "academic"            # Peer-reviewed paper or thesis
    BOOK = "book"                    # Published book
    DOCUMENTARY = "documentary"      # Other film/documentary
    ARCHIVE_FOOTAGE = "archive_footage"  # Film clips, BTS, TV footage
    PHOTOGRAPH = "photograph"        # Still images
    SOCIAL_MEDIA = "social_media"    # Tweet, post, etc.
    OFFICIAL_RECORD = "official_record"  # Court filings, FOIA, coroner reports
    WEBSITE = "website"              # General website/blog
    PODCAST = "podcast"              # Audio interview or discussion
    FILM = "film"                    # The actual films themselves


class UseType(str, Enum):
    REFERENCE = "reference"          # Fact-checking only, not reproduced
    QUOTE_SHORT = "quote_short"      # Short quote (<50 words) — likely fair use
    QUOTE_LONG = "quote_long"        # Longer quote — may need permission
    CLIP = "clip"                    # Video clip — needs license or fair use analysis
    PHOTO_BACKGROUND = "photo_background"  # Incidental background use
    PHOTO_FEATURED = "photo_featured"      # Featured still — needs license
    INSPIRATION = "inspiration"      # Influenced direction, not reproduced


class CopyrightStatus(str, Enum):
    PUBLIC_DOMAIN = "public_domain"          # Pre-1928 or explicitly released
    FAIR_USE_LIKELY = "fair_use_likely"      # Commentary/criticism use, short
    FAIR_USE_UNCERTAIN = "fair_use_uncertain"  # Longer use, needs attorney review
    LICENSED = "licensed"                    # License obtained
    LICENSE_NEEDED = "license_needed"        # Commercial license required
    OFFICIAL_RECORD = "official_record"      # Government record, freely accessible
    CREATIVE_COMMONS = "creative_commons"    # CC licensed
    UNKNOWN = "unknown"                      # Not yet assessed


@dataclass
class Source:
    url: str
    title: str
    publisher: str
    source_type: SourceType
    use_type: UseType

    # Attribution
    author: str = ""
    date_published: str = ""        # ISO date or "unknown"
    date_accessed: str = field(default_factory=lambda: date.today().isoformat())

    # Legal
    copyright_status: CopyrightStatus = CopyrightStatus.FAIR_USE_LIKELY
    copyright_holder: str = ""
    fair_use_basis: str = ""        # Specific statutory basis (commentary, criticism, etc.)
    license_type: str = ""          # If licensed: CC-BY, sync license, etc.
    permission_obtained: bool = False
    permission_contact: str = ""
    attorney_review_needed: bool = False

    # Content
    content_summary: str = ""       # What this source contains relevant to the doc
    key_facts: list[str] = field(default_factory=list)  # Specific facts to cite
    quotes: list[str] = field(default_factory=list)     # Exact quotes to potentially use
    relevance_score: int = 3        # 1-5: how important is this source

    # Tracking
    source_id: str = ""
    added_by: str = "research_loop"
    verified: bool = False
    notes: str = ""

    def __post_init__(self):
        if not self.source_id:
            import hashlib
            self.source_id = hashlib.md5(self.url.encode()).hexdigest()[:12]
        if isinstance(self.source_type, str):
            self.source_type = SourceType(self.source_type)
        if isinstance(self.use_type, str):
            self.use_type = UseType(self.use_type)
        if isinstance(self.copyright_status, str):
            self.copyright_status = CopyrightStatus(self.copyright_status)


class Registry:
    def __init__(self, sources: list[Source] | None = None):
        self.sources: dict[str, Source] = {}
        for s in (sources or []):
            self.sources[s.source_id] = s

    @classmethod
    def load(cls, path: Path = REGISTRY_FILE) -> "Registry":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls([Source(**s) for s in data])
        return cls()

    def save(self, path: Path = REGISTRY_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(s) for s in sorted(self.sources.values(),
                                           key=lambda x: x.date_accessed, reverse=True)]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, source: Source, overwrite: bool = False) -> bool:
        """Add a source. Returns True if added, False if already exists."""
        if source.source_id in self.sources and not overwrite:
            return False
        self.sources[source.source_id] = source
        return True

    def get(self, source_id: str) -> Source | None:
        return self.sources.get(source_id)

    def has_url(self, url: str) -> bool:
        import hashlib
        sid = hashlib.md5(url.encode()).hexdigest()[:12]
        return sid in self.sources

    def by_type(self, t: SourceType) -> list[Source]:
        return [s for s in self.sources.values() if s.source_type == t]

    def needs_license(self) -> list[Source]:
        return [s for s in self.sources.values()
                if s.copyright_status == CopyrightStatus.LICENSE_NEEDED]

    def needs_attorney(self) -> list[Source]:
        return [s for s in self.sources.values() if s.attorney_review_needed]

    def export_legal_report(self, path: Path = LEGAL_REPORT_FILE) -> Path:
        """Generate human-readable legal clearance report."""
        lines = [
            "# Tony Scott Documentary — Source Material Legal Report",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*",
            f"*Total sources: {len(self.sources)}*",
            "",
            "---",
            "",
            "## Legal Framework",
            "",
            "This documentary is produced under the following legal principles:",
            "",
            "**Fair Use (17 U.S.C. § 107):** Documentary commentary, criticism, and",
            "biographical treatment of a public figure's public career. All factual",
            "claims are sourced. Quoted material is minimal and transformative.",
            "",
            "**Defamation Standard:** All statements of fact are sourced to verifiable",
            "public records, published interviews, or official documents. Opinion is",
            "clearly distinguished from fact.",
            "",
            "**Right of Publicity:** Living subjects depicted or quoted will be offered",
            "the opportunity to provide releases before distribution. Archival clips of",
            "public performances are fair use under copyright law.",
            "",
            "---",
            "",
            "## Sources Requiring Action",
            "",
        ]

        needs_lic = self.needs_license()
        needs_att = self.needs_attorney()

        if needs_lic:
            lines.append(f"### License Needed ({len(needs_lic)} sources)")
            for s in needs_lic:
                lines.append(f"- **{s.title}** ({s.publisher})")
                lines.append(f"  - URL: {s.url}")
                lines.append(f"  - Contact: {s.permission_contact or 'TBD'}")
                lines.append(f"  - Use: {s.use_type.value}")
                lines.append("")

        if needs_att:
            lines.append(f"### Attorney Review Needed ({len(needs_att)} sources)")
            for s in needs_att:
                lines.append(f"- **{s.title}** ({s.publisher})")
                lines.append(f"  - URL: {s.url}")
                lines.append(f"  - Issue: {s.notes}")
                lines.append("")

        lines += [
            "---",
            "",
            "## Complete Source Index",
            "",
        ]

        for stype in SourceType:
            sources_of_type = self.by_type(stype)
            if not sources_of_type:
                continue
            lines.append(f"### {stype.value.replace('_', ' ').title()} ({len(sources_of_type)})")
            lines.append("")
            for s in sorted(sources_of_type, key=lambda x: x.relevance_score, reverse=True):
                lines.append(f"#### {s.title}")
                lines.append(f"- **Publisher/Author:** {s.publisher} / {s.author or 'N/A'}")
                lines.append(f"- **Published:** {s.date_published or 'N/A'} | **Accessed:** {s.date_accessed}")
                lines.append(f"- **URL:** {s.url}")
                lines.append(f"- **Use:** {s.use_type.value} | **Copyright:** {s.copyright_status.value}")
                if s.fair_use_basis:
                    lines.append(f"- **Fair Use Basis:** {s.fair_use_basis}")
                if s.content_summary:
                    lines.append(f"- **Summary:** {s.content_summary}")
                if s.key_facts:
                    lines.append(f"- **Key Facts:**")
                    for f in s.key_facts:
                        lines.append(f"  - {f}")
                lines.append("")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def stats(self) -> dict:
        by_type = {}
        for t in SourceType:
            count = len(self.by_type(t))
            if count:
                by_type[t.value] = count
        return {
            "total": len(self.sources),
            "by_type": by_type,
            "needs_license": len(self.needs_license()),
            "needs_attorney": len(self.needs_attorney()),
            "verified": sum(1 for s in self.sources.values() if s.verified),
        }


# ---------------------------------------------------------------------------
# Seed the registry with known sources from our initial research
# ---------------------------------------------------------------------------

INITIAL_SOURCES: list[Source] = [
    Source(
        url="http://www.sensesofcinema.com/2020/great-directors/scott-tony/",
        title="Scott, Tony — Great Directors",
        publisher="Senses of Cinema",
        author="Senses of Cinema Editorial",
        date_published="2020-01-01",
        source_type=SourceType.ACADEMIC,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Academic commentary and criticism for documentary research",
        content_summary="Most thorough academic career synthesis. Full filmography analysis, visual style breakdown, auteur case.",
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://www.bfi.org.uk/sight-and-sound/features/man-fire-tony-scott",
        title="Man on Fire: Tony Scott",
        publisher="BFI Sight & Sound",
        author="Sight & Sound editors",
        date_published="2004-09-01",
        source_type=SourceType.INTERVIEW,
        use_type=UseType.QUOTE_SHORT,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="British Film Institute",
        fair_use_basis="Short quotes from published interview for critical commentary",
        content_summary="Tony Scott in his own words describing his technique choices on Man on Fire. Primary source.",
        key_facts=["Scott describes using hand-cranked 1910 camera", "Discusses bleach bypass and cross-processing", "Calls mistakes 'the magic that comes from accidents'"],
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://www.hollywoodreporter.com/news/general-news/tony-scott-death-ridley-scott-interview-364528/",
        title="Tony Scott's Unpublished Final Interview: 'My Family Is Everything to Me'",
        publisher="The Hollywood Reporter",
        author="Hollywood Reporter Staff",
        date_published="2012-08-20",
        source_type=SourceType.INTERVIEW,
        use_type=UseType.QUOTE_SHORT,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="The Hollywood Reporter",
        fair_use_basis="Short quotes from posthumously published interview for biographical documentary",
        content_summary="His final unpublished interview. Family focus. Released immediately after death.",
        key_facts=["'My family is everything to me'", "Was in development on multiple projects at time of death"],
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://www.thedailybeast.com/the-beautiful-bromance-between-filmmakers-tony-scott-and-ridley-scott/",
        title="The Beautiful Bromance Between Filmmakers Tony Scott and Ridley Scott",
        publisher="The Daily Beast",
        date_published="2012-08-20",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="The Daily Beast",
        fair_use_basis="Reference for biographical facts, no reproduction",
        content_summary="Documents the brothers' daily phone calls. Contains Ridley's last conversation with Tony — urging him to make a film, not knowing Tony was at the bridge.",
        key_facts=[
            "Brothers spoke by phone every single day",
            "Ridley was in France when Tony jumped",
            "Last call: Ridley said 'Have you made your mind up about this film yet? Get going!'",
            "Tony got jealous when Ridley cast Denzel in American Gangster",
        ],
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://theaviationist.com/2012/08/20/tony-scott/",
        title="Tony Scott Personally Paid $25,000 to Keep Aircraft Carrier on Course",
        publisher="The Aviationist",
        date_published="2012-08-20",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="The Aviationist",
        fair_use_basis="Reference for biographical/production fact",
        content_summary="Documents Scott writing a personal $25,000 check to USS Enterprise captain for 5 extra minutes of golden-hour F-14 footage.",
        key_facts=["$25,000 personal check to ship captain", "5 additional minutes of backlit F-14 footage", "This footage became Top Gun's iconic opening"],
        relevance_score=4,
        verified=True,
    ),
    Source(
        url="https://www.guidedolomiti.com/en/true-stories/tony-scott-climbing/",
        title="Tony Scott: Filmmaker and Alpinist",
        publisher="Guide Dolomiti",
        date_published="2012-08-01",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Reference for biographical fact about public figure",
        content_summary="40+ years of Dolomite climbing. 2008 incident: hailstorm on Cima Grande north face, Scott calmly photographed it. Guide's quote about his character.",
        key_facts=[
            "40+ years of Dolomite routes",
            "Climbed Via Comici-Dimai on Cima Grande north face",
            "2008: stopped mid-climb in hailstorm to take photographs",
            "Guide: 'He finds time to take photographs'",
        ],
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://thedirectorsseries.blog/2017/02/03/tony-scotts-loving-memory-1971/",
        title="Tony Scott's Loving Memory (1971)",
        publisher="The Directors Series",
        date_published="2017-02-03",
        source_type=SourceType.ACADEMIC,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Critical analysis reference for documentary commentary",
        content_summary="Analysis of Scott's 1971 Cannes student film. Shot by Chris Menges. Psychological horror, 52 minutes, 16mm B&W. Almost nobody writes about this.",
        key_facts=[
            "Loving Memory (1970/71) premiered at Cannes 1971",
            "Shot by Chris Menges (future Oscar DP)",
            "52-minute psychological drama, 16mm black-and-white",
            "Elderly couple kills cyclist, brings body home",
            "Tony appeared in Ridley's Boy and Bicycle; Ridley appeared in One of the Missing",
        ],
        relevance_score=5,
        verified=True,
    ),
    Source(
        url="https://digitalcommons.chapman.edu/film_studies_theses/16/",
        title="Obsessed With the Image: Vulgar Auteurism and Post-Cinematic Affect in the Films of Tony Scott",
        publisher="Chapman University",
        author="Ethan Cartwright",
        date_published="2020-01-01",
        source_type=SourceType.ACADEMIC,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Academic source for documentary commentary and criticism",
        content_summary="MA thesis treating Scott's late films through vulgar auteurism and post-cinematic affect theory.",
        relevance_score=3,
        verified=True,
    ),
    Source(
        url="https://collider.com/true-romance-ending-quentin-tarantino-tony-scott/",
        title="How Tony Scott's Ending for True Romance Won Quentin Tarantino Over",
        publisher="Collider",
        date_published="2023-01-01",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Reference for documented production fact",
        content_summary="Scott changed Tarantino's ending (Clarence dies → couple survives). Tarantino later agreed Scott was right for the film Scott made.",
        key_facts=[
            "Tarantino's original: Clarence dies, Alabama takes money without grief",
            "Scott's change: couple survives and is happy",
            "Tarantino objected, then conceded after seeing the finished film",
        ],
        relevance_score=4,
        verified=True,
    ),
    Source(
        url="https://collider.com/denzel-washington-quentin-tarantino-feud-crimson-tide/",
        title="Crimson Tide and the Quentin Tarantino Uncredited Rewrite",
        publisher="Collider",
        date_published="2022-01-01",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Reference for documented production conflict and resolution",
        content_summary="Tarantino did uncredited Crimson Tide rewrites. Denzel called dialogue 'racist'. Years later Denzel apologized and said he buried the hatchet.",
        key_facts=[
            "Tarantino added Silver Surfer/Star Trek dialogue to Crimson Tide",
            "Washington objected, calling certain lines 'racist'",
            "Washington later apologized personally to Tarantino",
        ],
        relevance_score=3,
        verified=True,
    ),
    Source(
        url="https://andscape.com/features/the-haunting-prescience-of-enemy-of-the-state/",
        title="The Haunting Prescience of Enemy of the State",
        publisher="Andscape (ESPN/Disney)",
        date_published="2021-06-01",
        source_type=SourceType.ARTICLE,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Reference for documented fact about real-world impact of film",
        content_summary="Documents NSA Director Hayden's real alarm at Enemy of the State's effect on public perception. Film made 3 years before 9/11 was accurate about mass surveillance.",
        key_facts=[
            "General Michael Hayden (NSA Director) concerned about public perception",
            "Said he 'couldn't let the agency be defined by the last Will Smith movie'",
            "Film preceded PRISM/Snowden revelations by 15 years",
        ],
        relevance_score=4,
        verified=True,
    ),
    Source(
        url="https://www.cnn.com/2012/08/20/showbiz/obit-tony-scott",
        title="Official: Director Tony Scott Left Notes in Car and Office",
        publisher="CNN",
        date_published="2012-08-20",
        source_type=SourceType.OFFICIAL_RECORD,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="CNN",
        fair_use_basis="News reporting, reference only",
        content_summary="Official confirmation of two notes: one in car on bridge with family contact info, one in LA office. Ed Winters (LA County Coroner spokesperson) confirmed no mention of health problems in notes.",
        key_facts=[
            "Two notes left: car on bridge (family contacts), office (for family)",
            "Coroner spokesperson: no mention of health problems in notes",
            "Notes suggest advance planning, not impulsive act",
        ],
        relevance_score=4,
        verified=True,
    ),
    Source(
        url="https://reframe.sussex.ac.uk/post-cinema/5-4-siegel/",
        title="Top Gun and the Emergence of the Post-Cinematic",
        publisher="University of Sussex / Reframe",
        date_published="2016-01-01",
        source_type=SourceType.ACADEMIC,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Academic commentary for documentary research",
        content_summary="Academic framing of Top Gun as a post-cinematic text — music video logic applied to feature film.",
        relevance_score=2,
        verified=True,
    ),
    Source(
        url="https://networks.h-net.org/group/announcements/20067490/call-chapters-refocus-films-tony-scott",
        title="Call for Chapters: ReFocus: The Films of Tony Scott",
        publisher="H-Net / Edinburgh University Press",
        date_published="2023-01-01",
        source_type=SourceType.ACADEMIC,
        use_type=UseType.REFERENCE,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        fair_use_basis="Reference — forthcoming academic anthology",
        content_summary="Forthcoming Edinburgh University Press anthology on Tony Scott films. Track contributors when published.",
        relevance_score=3,
        verified=False,
        notes="Book not yet published as of research date. Monitor for release.",
    ),
    Source(
        url="https://www.salon.com/2012/08/20/tony_scott_better_than_ridley/",
        title="Tony Scott: Better than Ridley",
        publisher="Salon",
        author="Alex Pareene",
        date_published="2012-08-20",
        source_type=SourceType.ARTICLE,
        use_type=UseType.QUOTE_SHORT,
        copyright_status=CopyrightStatus.FAIR_USE_LIKELY,
        copyright_holder="Salon Media Group",
        fair_use_basis="Short quote from published criticism for documentary commentary",
        content_summary="Day-after-death piece making the case Tony was the better craftsman. 'There's no unwatchable Tony Scott movie.' vs. Ridley's post-Gladiator decline.",
        key_facts=["'There is no unwatchable Tony Scott movie'"],
        relevance_score=4,
        verified=True,
    ),
]


def seed_registry() -> Registry:
    """Initialize registry with known sources if it doesn't exist."""
    reg = Registry.load()
    added = 0
    for s in INITIAL_SOURCES:
        if reg.add(s):
            added += 1
    if added:
        reg.save()
        print(f"Registry seeded with {added} initial sources.")
    return reg


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tony Scott source registry")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--export", action="store_true", help="Export legal report")
    parser.add_argument("--seed", action="store_true", help="Seed with known sources")
    args = parser.parse_args()

    if args.seed:
        reg = seed_registry()
    else:
        reg = Registry.load()

    if args.status or not any(vars(args).values()):
        stats = reg.stats()
        print(f"\nTony Scott Source Registry")
        print(f"  Total sources: {stats['total']}")
        print(f"  By type: {stats['by_type']}")
        print(f"  Needs license: {stats['needs_license']}")
        print(f"  Needs attorney review: {stats['needs_attorney']}")
        print(f"  Verified: {stats['verified']}")

    if args.export:
        path = reg.export_legal_report()
        print(f"Legal report exported to {path}")
