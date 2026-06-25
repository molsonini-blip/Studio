"""
Jim Hall movie — scene data.
All 24 scenes with narration text, duration targets, and music cues.
Source: Phase1_Screenplay.md + Phase3_ProductionBreakdown.md
"""
from __future__ import annotations

SCENES: list[dict] = [
    {
        "id": 1,
        "slug": "prologue",
        "title": "Prologue: The Cars That Changed Everything",
        "duration_sec": 120,
        "priority": "HIGH",
        "music": "motif_3_fragment",
        "vo": (
            "Every racing car you see today — Formula 1, IndyCar, Le Mans — "
            "runs on ideas one man proved first. "
            "He didn't come from Europe. "
            "He didn't come from a factory racing program. "
            "He came from Midland, Texas. "
            "And he changed everything."
        ),
    },
    {
        "id": 2,
        "slug": "young_jim_model_a",
        "title": "Young Jim and the Model A (1949)",
        "duration_sec": 90,
        "priority": "MEDIUM",
        "music": "motif_1_horizon",
        "vo": (
            "James Ellis Hall was born July 23, 1935, in Abilene, Texas. "
            "The second of three sons of a West Texas oilman. "
            "He grew up in New Mexico, and by the time he was fourteen, "
            "he had already internalized the question that would define his life: "
            "not 'does it work?' but 'how could it work better?'"
        ),
    },
    {
        "id": 3,
        "slug": "the_phone_call",
        "title": "The Phone Call (1953)",
        "duration_sec": 75,
        "priority": "HIGH",
        "music": "silence",
        "vo": (
            "Just before Jim Hall was to enter the California Institute of Technology "
            "— Caltech — the greatest engineering school in America — "
            "his father, his stepmother, and his sister were killed in a plane crash. "
            "Jim Hall went to Caltech anyway. "
            "Because someone had to."
        ),
    },
    {
        "id": 4,
        "slug": "caltech",
        "title": "Caltech, 1953–1957",
        "duration_sec": 90,
        "priority": "LOW",
        "music": "motif_2_machine",
        "vo": (
            "He initially studied geology. "
            "Then he switched to mechanical engineering. "
            "He was interested in how things worked, "
            "and more specifically, how they could work better than they did. "
            "He graduated in 1957."
        ),
    },
    {
        "id": 5,
        "slug": "shelbys_dealership",
        "title": "Dallas, 1958: Shelby's Dealership",
        "duration_sec": 90,
        "priority": "LOW",
        "music": "period_jazz",
        "vo": (
            "The promised GM engineering position had evaporated in the 1958 recession. "
            "Hall ended up working at Carroll Shelby's dealership in Dallas. "
            "Shelby put him in race cars to evaluate them. "
            "Jim Hall kept winning. "
            "Word got around."
        ),
    },
    {
        "id": 6,
        "slug": "riverside_1960",
        "title": "Riverside, California, 1960: The US Grand Prix",
        "duration_sec": 120,
        "priority": "MEDIUM",
        "music": "motif_3_restrained",
        "vo": (
            "At the 1960 US Grand Prix at Riverside, "
            "Jim Hall ran competitively with the world's best drivers until the car failed. "
            "The performance didn't go unnoticed. "
            "Builders Troutman and Barnes approached him about co-funding a new sports racer. "
            "Hall agreed. "
            "He named it after the roadrunner — the bird of the Texas brush country. "
            "The chaparral."
        ),
    },
    {
        "id": 7,
        "slug": "building_chaparral",
        "title": "Midland, 1962: Building Chaparral",
        "duration_sec": 150,
        "priority": "HIGH",
        "music": "motif_2_machine",
        "vo": (
            "In 1962, Jim Hall and Hap Sharp officially formed Chaparral Cars, Incorporated. "
            "Sharp was a former oil company executive turned racer — "
            "the business mind that gave Hall the foundation and the freedom to experiment. "
            "Together they scouted the nation's leading aerospace companies "
            "for construction techniques nobody had brought to racing. "
            "Andy Green had designed fiberglass composite fairings "
            "for the B-58 Hustler — the world's first supersonic bomber. "
            "Hall hired him to apply those same aerospace techniques "
            "to the Chaparral 2's chassis. "
            "The result was the first successful full composite monocoque race car ever built. "
            "Four times stiffer than anything else on the starting grid."
        ),
    },
    {
        "id": 8,
        "slug": "rattlesnake_raceway",
        "title": "Rattlesnake Raceway",
        "duration_sec": 90,
        "priority": "MEDIUM",
        "music": "motif_1_with_engine",
        "vo": (
            "Rattlesnake Raceway was Hall's secret weapon. "
            "A private test track on the Midland scrubland — "
            "invisible to competitors, invisible to the press. "
            "While other teams tested on public circuits, "
            "Hall tested every idea at home, refined it to perfection, "
            "then showed up at races with answers "
            "others didn't even know were questions."
        ),
    },
    {
        "id": 9,
        "slug": "la_times_gp_1963",
        "title": "Los Angeles Times Grand Prix, Riverside, October 1963",
        "duration_sec": 150,
        "priority": "HIGH",
        "music": "motif_3_building",
        "vo": (
            "At the inaugural Los Angeles Times Grand Prix in October 1963, "
            "Jim Hall put the Chaparral 2A on pole position — "
            "ahead of Jim Clark, Graham Hill, and John Surtees. "
            "The three best drivers in Formula 1. "
            "The racing world noticed."
        ),
    },
    {
        "id": 10,
        "slug": "sebring_1965",
        "title": "Sebring, Florida, March 21, 1965: The Upset",
        "duration_sec": 240,
        "priority": "HIGH",
        "music": "motif_3_rain",
        "vo": (
            "March 21, 1965. The 12 Hours of Sebring. "
            "The factory-backed armies had gathered: "
            "Ford GTs driven by Gurney, McLaren, and Miles. "
            "Shelby Daytona Coupes. "
            "Factory Ferraris with Rodriguez and Graham Hill. "
            "The combined budgets of the opposition dwarfed Chaparral's entire program. "
            "The weather that day was biblical. "
            "The Chaparral 2A won the 1965 12 Hours of Sebring. "
            "In a monsoon. "
            "Against the most powerful factory racing programs in the world. "
            "A car built in Midland, Texas, "
            "by a handful of men who believed there was a better way."
        ),
    },
    {
        "id": 11,
        "slug": "gm_partnership",
        "title": "The Secret Partnership: Chevrolet",
        "duration_sec": 90,
        "priority": "LOW",
        "music": "motif_2_conspiratorial",
        "vo": (
            "General Motors had imposed a self-ban on factory racing in 1963. "
            "But they never stopped being interested in what Jim Hall was doing. "
            "The partnership was an open secret in racing — "
            "you weren't supposed to talk about it, and nobody did. "
            "In exchange, when GM faced antitrust litigation in the mid-1960s, "
            "Jim Hall testified on their behalf. "
            "It was a relationship built on trust and West Texas discretion."
        ),
    },
    {
        "id": 12,
        "slug": "chaparral_2e_wing_reveal",
        "title": "The Chaparral 2E Wing Reveal (1966)",
        "duration_sec": 240,
        "priority": "HIGHEST",
        "music": "silence_then_motif_2_then_motif_3",
        "vo": (
            "The Chaparral 2E introduced the concept of aerodynamic downforce to road racing. "
            "The wing was mounted on pillars directly connected to the rear suspension — "
            "so the downforce loaded the tires, not the chassis. "
            "Phil Hill could adjust the wing angle with his left foot, "
            "freed by Hall's semi-automatic transmission. "
            "On the straight: flat, minimum drag. "
            "On the brakes: angled, maximum grip. "
            "The crowd's reaction was universal. "
            "Nobody had ever seen anything like it. "
            "By 1968, every Formula 1 car had wings. "
            "By 1970, wings were standard on every serious race car in the world. "
            "Hall's idea. Hall's patent. Hall's Midland, Texas shop. "
            "A decade later, the FIA would be regulating wing dimensions "
            "on every car in every championship. "
            "The idea that was impossible in 1966 had become mandatory."
        ),
        "quote": "The car allowed you to out-brake everybody, out-corner everybody. — Phil Hill, Formula 1 World Champion",
    },
    {
        "id": 13,
        "slug": "nurburgring_brands_hatch",
        "title": "The Nürburgring and Brands Hatch, 1966–1967",
        "duration_sec": 90,
        "priority": "MEDIUM",
        "music": "motif_3_brief",
        "vo": (
            "The Chaparral 2D won the 1966 1000 Kilometers of the Nürburgring. "
            "The 2F — its successor — won the BOAC 500 at Brands Hatch in 1967. "
            "The FIA banned the Chaparral design immediately after that victory. "
            "They banned it because they couldn't beat it."
        ),
    },
    {
        "id": 14,
        "slug": "las_vegas_crash",
        "title": "Las Vegas, November 1968: The Crash",
        "duration_sec": 120,
        "priority": "HIGH",
        "music": "silence",
        "vo": (
            "The crash ended Jim Hall's driving career. "
            "He would attempt a comeback in 1970's Trans-Am, "
            "but the injury had taken something that couldn't be given back. "
            "He was 33 years old. "
            "He returned to Midland. "
            "He went back to the shop. "
            "And he built the most radical race car the world has ever seen."
        ),
    },
    {
        "id": 15,
        "slug": "chaparral_2j_fan_car",
        "title": "The Chaparral 2J: The Fan Car (1970)",
        "duration_sec": 300,
        "priority": "HIGHEST",
        "music": "motif_2_then_motif_3_with_fan",
        "vo": (
            "Conventional aerodynamic downforce depends on speed — "
            "the faster you go, the more grip you get. "
            "At slow speeds, through tight corners, you get very little. "
            "The 2J solved this problem completely. "
            "Two fans pumped air out from under the car's sealed floor, "
            "creating a partial vacuum. "
            "The suction pressed the car to the road "
            "with the same force at 30 miles per hour as at 150 miles per hour. "
            "The car could theoretically corner just as well "
            "in the pit lane as on the straight. "
            "At the 1970 Riverside Can-Am, "
            "the 2J qualified more than two full seconds "
            "faster than the championship-winning McLaren M8D. "
            "Two seconds. In qualifying. "
            "The entire field's best was two seconds slower "
            "than Hall's car that looked like a rolling refrigerator. "
            "The protests began before the car finished its first qualifying session. "
            "McLaren. Lola. The entire establishment of Can-Am racing. "
            "At year end, the SCCA agreed. The 2J was banned. "
            "Eight years later, Gordon Murray of Brabham "
            "built an almost identical car for Formula 1. "
            "The Brabham BT46B won its first race — the 1978 Swedish Grand Prix. "
            "F1 banned it after one race. "
            "Hall's idea was right in 1970. It was still right in 1978. "
            "The physics does not care about the rules. "
            "The Chaparral 2J remains, lap-for-lap, "
            "the fastest car that ever competed in Can-Am racing."
        ),
    },
    {
        "id": 16,
        "slug": "wilderness_years",
        "title": "The Wilderness Years, 1971–1973",
        "duration_sec": 45,
        "priority": "LOW",
        "music": "motif_1_patient",
        "vo": (
            "For three years, Jim Hall was mostly quiet. "
            "He managed. He consulted. He watched racing from outside. "
            "He was 36. "
            "The cars he had built had been banned, "
            "the crash had ended his driving, "
            "and the sport had moved on. "
            "Or so it appeared."
        ),
    },
    {
        "id": 17,
        "slug": "carl_haas_calls",
        "title": "The Comeback: Carl Haas Calls, 1973",
        "duration_sec": 90,
        "priority": "MEDIUM",
        "music": "motif_4_comeback",
        "vo": (
            "Carl Haas was the American importer for Lola racing cars, "
            "and one of the most resourceful men in motorsport. "
            "He didn't need to convince Jim Hall that he could win. "
            "He just needed to give Hall a reason to try again."
        ),
    },
    {
        "id": 18,
        "slug": "seven_championships",
        "title": "Seven in a Row: Haas-Hall F5000, 1974–1980",
        "duration_sec": 120,
        "priority": "MEDIUM",
        "music": "motif_4_building",
        "vo": (
            "Haas-Hall Racing won the SCCA Formula 5000 championship in their first season. "
            "Then they won it again. "
            "Seven consecutive championships through 1980 — "
            "an almost incomprehensible run of dominance. "
            "But Formula 5000 was not where Jim Hall was looking. "
            "He was looking at Indianapolis."
        ),
    },
    {
        "id": 19,
        "slug": "indianapolis_1978",
        "title": "Indianapolis Motor Speedway, May 1978",
        "duration_sec": 240,
        "priority": "HIGH",
        "music": "motif_4_to_motif_3",
        "vo": (
            "Al Unser won the 1978 Indianapolis 500 for Jim Hall and Carl Haas. "
            "Then he won the Pocono 500. "
            "Then the California 500. "
            "Three 500-mile races in a single season — "
            "what the sport calls the Triple Crown. "
            "No team had ever done it before. "
            "No team has done it since."
        ),
    },
    {
        "id": 20,
        "slug": "chaparral_2k_barnard",
        "title": "The Chaparral 2K and John Barnard, 1979",
        "duration_sec": 90,
        "priority": "MEDIUM",
        "music": "motif_2_returning",
        "vo": (
            "Hall commissioned British engineer John Barnard "
            "to design the Chaparral 2K — the first ground-effect IndyCar. "
            "Nicknamed the Yellow Submarine for its Pennzoil livery, "
            "it applied the tunnel aerodynamics Hall had pioneered in the 1960s "
            "to oval-track racing. "
            "When it appeared at Indianapolis in 1979, "
            "the IndyCar world had the same reaction "
            "the Can-Am world had in 1966: disbelief."
        ),
    },
    {
        "id": 21,
        "slug": "indianapolis_1980",
        "title": "Indianapolis 1980: Rutherford and the Championship",
        "duration_sec": 180,
        "priority": "HIGH",
        "music": "motif_3_to_motif_5",
        "vo": (
            "Johnny Rutherford won the 1980 Indianapolis 500 in the Chaparral 2K. "
            "Then he won the CART PPG championship — IndyCar's overall title. "
            "Hall's Yellow Submarine was the most dominant car in American open-wheel racing. "
            "From the Chaparral 2A to the 2K — "
            "from a shop in Midland, Texas, "
            "to the winner's circle at Indianapolis — "
            "the arc of Jim Hall's career spans the complete transformation of racing."
        ),
    },
    {
        "id": 22,
        "slug": "retirement_1996",
        "title": "Retirement, 1996",
        "duration_sec": 60,
        "priority": "LOW",
        "music": "motif_5_beginning",
        "vo": (
            "Jim Hall retired from racing at the end of the 1996 season, "
            "34 years after his first championship. "
            "His final win — Gil de Ferran at Cleveland — came in his last year of competition. "
            "He had won in every series he entered. "
            "He went home to Midland."
        ),
    },
    {
        "id": 23,
        "slug": "petroleum_museum_epilogue",
        "title": "The Petroleum Museum — Epilogue",
        "duration_sec": 180,
        "priority": "MEDIUM",
        "music": "motif_5_building",
        "vo": (
            "Seven Chaparrals are displayed at the Petroleum Museum in Midland, Texas. "
            "They are not static museum pieces. "
            "The engines still run. "
            "The cars are periodically driven to demonstrate their capabilities. "
            "Because Jim Hall built everything to work. "
            "Every wing on every racing car in the world "
            "carries a debt to the Chaparral 2E. "
            "Every composite monocoque chassis carries a debt to the Chaparral 2A. "
            "Every car that uses ground effect carries a debt to the 2J — and the 2K. "
            "Jim Hall didn't just race cars. "
            "He defined what a race car could be."
        ),
    },
    {
        "id": 24,
        "slug": "final_montage",
        "title": "Final Montage and Title Cards",
        "duration_sec": 120,
        "priority": "HIGH",
        "music": "motif_5_full",
        "vo": (
            "The question Jim Hall asked in a New Mexico driveway at fourteen years old — "
            "'how could this work better?' — "
            "turned out to be the most important question "
            "in the history of motor racing. "
            "He asked it every day for forty years. "
            "And every time he found an answer, the sport had to catch up."
        ),
    },
]

# ── GPU render prompts (FLUX images + CogVideoX video) ────────────────────────
# Keyed by scene id. Merged into SCENES at module load.
# image_prompts: list of FLUX text-to-image prompts for this scene
# video_prompt:  CogVideoX text-to-video prompt (single clip, ~6 sec)
# video_negative: things to avoid in the video

_GPU_PROMPTS: dict[int, dict] = {
    1: {  # Prologue
        "image_prompts": [
            "West Texas Permian Basin aerial view, oil pump jacks silhouetted against golden sunset sky, flat horizon, sparse mesquite scrub, Kodachrome 1960s film look, cinematic 2.39:1 widescreen",
            "White Chaparral 2A sports prototype race car at speed, 1963, Road America circuit, trees blurring, low tracking shot, 35mm film grain, warm period color",
            "Chaparral 2E white race car with enormous elevated rear wing in Can-Am paddock 1966, crowd of spectators frozen in disbelief, 35mm film grain",
        ],
        "video_prompt": "Aerial drone shot pushing forward over West Texas oil fields at golden hour, oil pump jacks nodding rhythmically, flat horizon, sparse desert brush, warm amber light, cinematic 2.39:1, film grain",
        "video_negative": "modern buildings, cars, people, text, watermark, digital artifacts, CGI look",
    },
    3: {  # The phone call
        "image_prompts": [
            "American teenage boy 17 years old in 1953 home interior, receiving bad news on rotary telephone, standing very still, evening light through window, Kodachrome warm color, 35mm film grain, quiet devastation",
            "Small propeller aircraft very distant against Texas sky, late afternoon, becoming smaller, ominous stillness, 1953 period, 16mm film grain",
        ],
        "video_prompt": "Interior 1950s American home, teenage boy standing at telephone table, hand holding phone receiver, face still and controlled, processing devastating news, evening window light, Kodachrome warm tones, very slow push-in, 35mm film grain",
        "video_negative": "modern objects, color grading, digital look, fast movement, bright colors",
    },
    9: {  # LA Times GP 1963
        "image_prompts": [
            "1963 Los Angeles Times Grand Prix qualifying, Riverside International Raceway California, white Chaparral 2A on pole position timing board showing it ahead of Jim Clark and Graham Hill, hand-chalked board, race officials staring in surprise, 35mm film grain",
            "Chaparral 2A white sports prototype at speed through Riverside raceway corner, 1963, California desert mountains visible in background, low camera angle, motion blur, 35mm film grain period accurate",
            "Racing paddock 1963 Riverside California, Graham Hill and Phil Hill standing with others staring at a timing board in disbelief, period racing suits, 35mm film grain",
        ],
        "video_prompt": "White Chaparral 2A race car blazing through qualifying lap at Riverside International Raceway 1963, low camera tracking alongside at corner, California mountains in background, motion blur, 35mm film grain, urgent racing energy",
        "video_negative": "modern cars, digital sharpness, teal color grading, CGI, slow motion",
    },
    10: {  # Sebring 1965
        "image_prompts": [
            "12 Hours of Sebring 1965, Florida airfield circuit, heavy monsoon rain, white Chaparral 2A at speed through standing water, massive spray rooster-tail behind it, gray overcast sky, headlights on, raw and urgent, 35mm film grain",
            "Sebring 1965 race start, Florida airfield circuit, factory Ford GT40s and Ferrari racers on the grid in pre-dawn mist, massive impressive machines, the white Chaparral smaller among them, pre-race tension, 35mm film grain",
            "Chaparral victory at Sebring 1965, checkered flag in heavy rain, small Texas team celebrating around the white car, Hap Sharp arms raised, raw joy, rain-soaked marshals, 35mm film grain",
        ],
        "video_prompt": "White Chaparral 2A racing through heavy Florida rain at Sebring 1965, massive spray, standing water on track, gray overcast sky, car finding grip where others slide, urgent documentary footage style, 35mm 16mm film grain",
        "video_negative": "sunshine, dry track, modern cars, digital sharpness, CGI",
    },
    12: {  # 2E wing reveal
        "image_prompts": [
            "Chaparral 2E white race car being wheeled from transporter at Can-Am paddock 1966, the massive rear wing on tall vertical struts entering frame first, spectators and mechanics frozen mid-step staring, other conventional race cars visible for scale, 35mm film grain",
            "Close-up of Chaparral 2E rear wing detail 1966, enormous flat wing element on tall vertical struts above the car body, white painted surface, pivot mechanism visible at base, shallow depth of field, 35mm film grain",
            "Phil Hill World Champion racing driver circling the Chaparral 2E 1966, the massive wing framing the shot above his head, Can-Am paddock, expression of genuine astonishment, period racing suit, 35mm film grain",
            "Chaparral 2E white race car at full speed at Can-Am circuit 1966, enormous elevated rear wing clearly angled for downforce in corner, other cars visibly slower and smaller in background, track level shot, motion blur, 35mm film grain",
        ],
        "video_prompt": "Chaparral 2E white race car with massive elevated rear wing being slowly rolled from the transporter at a 1966 Can-Am paddock, wing appears before car body, spectators and mechanics stop and stare in disbelief, other conventional race cars visible for scale, 35mm film grain, slow deliberate reveal",
        "video_negative": "fast movement, modern cars, modern crowd, digital sharpness, teal grading, CGI",
    },
    14: {  # Las Vegas crash
        "image_prompts": [
            "Aftermath of a racing accident in the Nevada desert 1968, a white Chaparral race car resting in desert scrub beyond the barrier, dust settling, marshals running toward it, Las Vegas circuit visible in background, 35mm film grain, quiet and serious",
            "Hospital room 1968, American man in bed with heavily bandaged knee, staring at the ceiling, afternoon light through window, quiet recovery, 35mm film grain",
        ],
        "video_prompt": "Desert racing circuit Las Vegas Nevada 1968, sudden racing accident, car airborne at high speed, lands in desert scrub, dust cloud rising, complete stillness after impact, marshals running, very brief and shocking, 35mm film grain, documentary style",
        "video_negative": "slow motion, dramatic music, modern safety equipment, gore, spectacle",
    },
    15: {  # 2J fan car
        "image_prompts": [
            "Chaparral 2J white boxy fan car at Riverside International Raceway 1970, unusual rectangular body with Lexan skirts hanging around perimeter, two large circular fan openings at rear, other sleek McLaren M8D orange cars visible in background looking elegant by comparison, 35mm 16mm film grain",
            "Chaparral 2J interior fan detail, two circular rear fan housings visible, Lexan skirt edges touching the ground, mechanical and functional, no glamour, close-up, shallow depth of field, 35mm film grain",
            "Can-Am paddock 1970, team manager Denny Hulme staring at timing board showing Chaparral 2J two full seconds faster than the McLaren field, expression of disbelief and concern, period racing team atmosphere, 35mm film grain",
        ],
        "video_prompt": "Chaparral 2J boxy white fan car qualifying at Riverside Raceway 1970, the unusual square shape cornering impossibly flat while sleek orange McLarens slide and fight, distinctive two-stroke fan motor whine audible, 16mm documentary film grain, desert hills background",
        "video_negative": "modern cars, digital sharpness, slow motion overdone, CGI, beautiful aesthetics",
    },
    19: {  # Indianapolis 1978
        "image_prompts": [
            "Indianapolis Motor Speedway race start 1978, 33 IndyCars accelerating, enormous grandstands packed with 250,000 spectators, the Yard of Bricks at start finish line, Haas-Hall Lola prominent, period accurate 1978 IndyCar, 35mm film grain",
            "Jim Hall on the pit wall at Indianapolis 1978, stopwatch in hand, silver-streaked dark hair, team jacket, eyes focused on track, the controlled focus of a man about to win, 35mm film grain",
            "Al Unser Indianapolis 500 1978 Victory Lane, checkered flag, Haas-Hall crew celebrating, Jim Hall approaching with quiet satisfaction, confetti, massive grandstands behind, period accurate 1978, 35mm film grain",
        ],
        "video_prompt": "Indianapolis Motor Speedway 1978, the pace car pulls away and 33 IndyCars accelerate from green flag down the front straight, enormous crowd in grandstands, the roar building, Yard of Bricks visible, period accurate cars, cinematic wide shot, 35mm film grain",
        "video_negative": "modern cars, HANS devices, modern safety equipment, digital look, slow motion",
    },
    21: {  # Indianapolis 1980
        "image_prompts": [
            "Chaparral 2K Yellow Submarine IndyCar in Victory Lane at Indianapolis Motor Speedway 1980, Pennzoil yellow and white livery, Johnny Rutherford standing in cockpit arms raised, Jim Hall walking over with quiet satisfaction, crew celebrating, confetti, period accurate, 35mm film grain",
            "Chaparral 2K Yellow Submarine leading the 1980 Indianapolis 500, front view of the Pennzoil yellow and white ground-effect IndyCar on the oval, grandstands packed, dominant and fast, 35mm film grain",
        ],
        "video_prompt": "Pennzoil yellow and white Chaparral 2K IndyCar taking the checkered flag at Indianapolis 500 1980, Victory Lane celebration, Johnny Rutherford raising arms, Jim Hall approaching pit wall, crew erupting, confetti, grandstand crowd visible, earned triumph not spectacle, 35mm film grain",
        "video_negative": "modern cars, modern equipment, digital sharpness, teal grading, slow motion",
    },
    23: {  # Museum epilogue
        "image_prompts": [
            "Permian Basin Petroleum Museum Midland Texas Chaparral Gallery, modern day, seven white Chaparral race cars displayed under warm halogen spotlights, 2A 2E 2J 2K visible, polished concrete floor, intimate gallery space, no film grain — clean modern look",
            "Chaparral 2J in museum display under warm gallery lighting, boxy white fan car with Lexan skirts visible, fan housings at rear, period racing photographs on wall behind it, ready to run despite being a museum piece",
        ],
        "video_prompt": "Permian Basin Petroleum Museum Chaparral Gallery modern day, slow camera movement past the seven Chaparral race cars under warm gallery lighting, the 2A through the 2K, each unique and revolutionary, respectful and quiet, clean modern photography no film grain",
        "video_negative": "crowds, noise, film grain, period artifacts, dark lighting",
    },
}

# Merge GPU prompts into SCENES
for _scene in SCENES:
    if _scene["id"] in _GPU_PROMPTS:
        _scene.update(_GPU_PROMPTS[_scene["id"]])

NARRATOR_VOICE_ID = "M48xFCmxS3NPBQYh5ULb"  # Marcus Webb — deep, resonant, measured
NARRATOR_ANCHOR_ID = "marcus_webb"

OLLAMA_HOSTS = [
    "http://127.0.0.1:11434",        # when running on the server itself (IPv4 explicit)
    "http://162.251.146.56:11434",   # StatsDBServer01 from external
]
OLLAMA_MODEL = "llama3.2:3b"
