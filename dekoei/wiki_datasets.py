"""The koei-wiki exports (persons-export, places-export, biography, stats-export): dataset -> the module that reads it
and what it exports, one table for all of them (docs/backlog/code-consolidation.md). The second field lists the kinds;
"kind=module" when that kind is read by another module. What a module provides for each kind:

    persons  persons(game_dir) -> [row]                                     (persons_export.py)
    places   places(game_dir, out_dir) -> [row]; optional world_check(game_dir, rows) -> (checked, problems) and
             ONE_WAY, the (from, to) adjacencies that are one-way in the game data          (places_export.py)
    bios     bios(game_dir) -> {id: [(kind, text)]}, bio_names(game_dir) -> {id: name}, BIO_LANG     (biography.py)
    stats    stats(game_dir) -> [(id, name, {ability: value})]              (wiki_stats.py)
"""
import importlib

DATASETS = {
    "nobu2-pc88": ("wiki_nobu2", "persons places"),
    "nobu3-pc98": ("wiki_nobu3", "persons places"),
    "nobu4-pc98": ("wiki_nobu4", "persons places"),
    "nobu5pk-win": ("wiki_nobu5", "persons places bios"),
    "nobu5pk-pc98": ("wiki_nobu5_pc98", "persons places bios"),
    "nobu6pk-pc98": ("wiki_nobu6", "persons places bios"),
    "nobu7pk-win": ("wiki_nobu7", "persons places bios"),
    "nobu8pk-win": ("wiki_nobu8", "persons places bios"),
    "nobu9pk-win": ("wiki_nobu9", "persons places bios"),
    "nobu10pk-win": ("wiki_nobu10", "persons places bios"),
    "nobu11pk-win": ("wiki_nobu11", "persons places bios"),
    "nobu12pk-win": ("wiki_nobu12", "persons places bios"),
    "nobu13pk-win": ("wiki_nobu13", "persons places bios"),
    "nobu14pk-win": ("wiki_nobu14", "persons places bios"),
    "nobu15pk-win": ("wiki_nobu15", "persons places bios"),
    "nobu16pk-win": ("wiki_nobu16", "persons places bios"),
    "san8pk-win": ("wiki_san8", "persons places bios=san8_extras stats"),
    "san9pk-win": ("wiki_san9", "persons places bios=san9_extras stats"),
    "san10pk-win": ("wiki_san10", "persons places bios=san10_extras stats"),
    "san11pk-win": ("wiki_san11", "persons places bios=san11_extras stats"),
    "san12pk-win": ("wiki_san12", "persons places bios=san12_extras stats"),
    "san13pk-win": ("wiki_san13", "persons places bios stats"),
    "san14pk-win": ("wiki_san14", "persons places bios stats"),
    "genghis-pc98": ("wiki_genghis", "persons places=genghis_extras"),
    "genchou-pc98": ("wiki_genchou", "persons places=genchou_extras"),
    "genghis4pk-win": ("wiki_genghis4", "persons places=genghis4_extras bios"),
    "genpei-pc98": ("wiki_genpei", "persons places"),
    "ishin-pc98": ("wiki_ishin", "persons places"),
    "koukai-pc98": ("wiki_koukai", "persons places"),
    "koukai2-pc98": ("wiki_koukai2", "persons places"),
    "koukai3-win": ("wiki_koukai3", "persons places"),
    "san1-pc98": ("wiki_san1", "persons places stats"),
    "san2-pc98": ("wiki_san2", "persons places stats"),
    "san3-pc98": ("wiki_san3", "persons places stats"),
    "san4pk-pc98": ("wiki_san4", "persons places stats"),
    "san5pk-pc98": ("wiki_san5", "persons places stats"),
    "san6pk-win": ("wiki_san6", "persons places bios stats"),
    "san7pk-win": ("wiki_san7", "persons places bios=san7_extras stats"),
    "suikoden-dos": ("wiki_suikoden", "persons places"),
    "kouryuuki-dos": ("wiki_kouryuuki", "persons places=kouryuuki_extras"),
    "koukai4pk-win": ("wiki_koukai4", "persons places"),
    "koukaigd-win": ("wiki_koukaigd", "persons places"),
    "lempe-dos": ("wiki_lempe", "persons places"),
    "ishin2-win": ("wiki_ishin2", "persons"),
    "taikoh-pc98": ("wiki_taikoh", "persons places"),
    "taikoh2-pc98": ("wiki_taikoh2", "persons"),
    "taikoh3-win": ("wiki_taikoh3", "persons"),
    "taikoh4-win": ("wiki_taikoh4", "persons"),
    "taikoh5dx-win": ("wiki_taikoh5", "persons"),
    "eiketsu3-win": ("wiki_eiketsu3", "persons"),
    "eiketsu4-win": ("wiki_eiketsu4", "persons"),
    "tk-pc98": ("wiki_tk", "persons"),
    "tk2pk-pc98": ("wiki_tk2", "persons"),
    "tk3pk-pc98": ("wiki_tk3", "persons"),
    "liberty-pc98": ("wiki_liberty", "persons"),
    "europe-pc98": ("wiki_europe", "persons"),
    "royal-pc98": ("wiki_royal", "persons places bios"),
    "eiketsu-dos": ("wiki_eiketsu", "persons"),
    "eiketsu-pc98": ("wiki_eiketsu", "persons"),
    "koumei-win": ("wiki_koumei", "persons"),
    "eiketsu5-win": ("wiki_eiketsu5", "persons"),
    "nobu2-dos": ("wiki_nobu2_dos", "places"),
    "lempe-pc98": ("wiki_lempe_pc98", "places"),
    "san4pk-dos": ("wiki_san4", "bios"),
    "san5pk-dos": ("wiki_san5", "bios"),
}


def datasets(kind: str) -> list[str]:
    """The datasets with an export of this kind, in table order."""
    return [d for d, (_, kinds) in DATASETS.items() if any(k.split("=")[0] == kind for k in kinds.split())]


def module(dataset: str, kind: str):
    """The module that reads this kind of the dataset."""
    main, kinds = DATASETS[dataset]
    for k in kinds.split():
        name, _, other = k.partition("=")
        if name == kind:
            return importlib.import_module(other or main)
    raise KeyError(f"{dataset} has no {kind} export")
