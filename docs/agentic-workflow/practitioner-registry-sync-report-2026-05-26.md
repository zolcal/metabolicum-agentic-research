# Practitioner Registry Sync Report - 2026-05-26

Sources:
- `/home/zoltan/Projects/metabolicum-research/output/social-discovery/practitioner-registry.json`
- `/home/zoltan/Projects/metabolicum-research/config/practitioners.yaml`
- `/home/zoltan/Projects/metabolicum-research/research/practitioners/MetabolicumGlobalPractitionerResearcherDirectory-v0.4.md`

Merge summary:
- matched social entries: 30
- added practitioners/entities: 80
- added aliases: 522
- added surfaces: 84
- added website surfaces: 25
- added YouTube surfaces: 31
- added Twitter/X surfaces: 20
- added podcast surfaces: 8

Post-merge coverage:
- registry entries: 125
- entries with website: 37
- entries with YouTube: 32
- entries with Twitter/X: 20
- entries with podcast: 9

Newly added entries:
- Paul Saladino
- David Perlmutter
- Thomas Seyfried
- Tomas Duraj
- Sten Ekberg
- Casey Means
- Dale Bredesen
- Terry Wahls
- Andrew Huberman
- Bret Scher
- Sara Gottfried
- Amy Myers
- Barbra Allen Bradshaw
- Gerry Krystal
- Jay Wortman
- Grant Brinkworth
- Manny Noakes
- James Muecke
- David Raubenheimer
- Caryn Zinn
- Andrew Koutnik
- Aseem Malhotra
- Michael Mosley
- Rangan Chatterjee
- Zoë Harcombe
- Nicolai Worm
- Anne Fleck
- Jörn Klasen
- Maximilian Schiele
- Andreas Pfeiffer
- Stephan Bischoff
- Jacques Lucas
- Laurent Chevallier
- Michel de Lorgeril
- Jean-Michel Lecerf
- Emanuele F. M. Di Angelantonio
- Paolo Raggi
- Antonio M. Gotto Jr.
- Francisco Martinez
- Javier González-Gallego
- Rafael Máñquez
- José L. G. Luna
- Kees K. J. van den Heuvel
- Yvo Sijpkens
- Eric Sijbrands
- Hanno Pijl
- Fredrik Nyström
- Peter Jönsson
- Anssi H. Manninen
- Jaakko Halonen
- Christophe G. Lagasse
- Koenraad K. J. van den Heuvel
- Zoltán Szabó
- Katalin V. Kovács
- András Tóth
- Orsolya T. Fehér
- Bence T. Károly
- Anna M. Szilágyi
- István Takács
- Miklós Szathmáry
- Anna K. Fehér
- Zoltán Rakonczay Jr.
- Ken Berry
- Shawn Baker
- Chris Palmer
- Georgia Ede
- Thomas Fordham Brewer
- Lily Nichols
- Kyle Gillett
- Dave Feldman
- Judy Cho
- Siim Land
- Low Carb Down Under
- The Primal Podcast
- The Feldman Protocol
- Nutrition with Judy
- Physionic
- Mind & Matter Podcast
- Keto Connect
- Keto Savage


## Expanded YouTube Smoke Test

Command: `python -m code.discovery.youtube --live --max-videos-per-channel 5 --rank-only` against enriched registry.

- YouTube seeds attempted: 32
- Ranked video rows written: 85
- Channel errors written: 7

Channel errors were quota/rate-limit failures, not parse failures. Retry after quota reset.
- person:lily-nichols: Lily Nichols (https://www.youtube.com/channel/UCmT8m7iL6jIZ6qp83L3Ewnw)
- person:low-carb-down-under: Low Carb Down Under (https://www.youtube.com/channel/UCcTTiHZtNpiqD2EubIO5HFw)
- conference:metabolic-health-summit: Metabolic Health Summit (https://www.youtube.com/channel/UCYHR-dn_ohWIoPt8LeumbNA)
- person:mind-matter-podcast: Mind & Matter Podcast (https://www.youtube.com/channel/UC_dJ5ThfEhj39zkEPQbNdPg)
- person:paul-saladino: Paul Saladino (https://www.youtube.com/channel/UC0XkvurBkdGA2Y8dnDhIwBw)
- person:physionic: Physionic (https://www.youtube.com/channel/UCj3p_1jOCJXB_L_we-DjLbA)
- person:shawn-baker: Shawn Baker (https://www.youtube.com/channel/UC5apkKkeZQXRSDbqSalG8CQ)

Duplicate YouTube channel surfaces requiring editorial decision:
- `https://www.youtube.com/channel/UCLacwQCp7k4YscqoKxpwLFg`: person:dave-feldman (Dave Feldman), person:the-feldman-protocol (The Feldman Protocol)
- `https://www.youtube.com/channel/UCgXrNUokx_Zgprns3z6zqSg`: person:judy-cho (Judy Cho), person:nutrition-with-judy (Nutrition with Judy)
