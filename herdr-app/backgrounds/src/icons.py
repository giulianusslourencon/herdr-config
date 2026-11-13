"""Medieval-fantasy icon set for the Wrath mods (24x24, stroked with currentColor)."""
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round">'

ICONS = {
    # Grimoire: a clasped spellbook with a rune on the cover (Settings)
    "settings": (1.8, '<path d="M5 3.5h11.5a2 2 0 0 1 2 2V20.5H6.5A1.5 1.5 0 0 1 5 19Z"/><path d="M5 19a1.5 1.5 0 0 1 1.5-1.5h12"/>'
                      '<path d="M18.5 9h1.8v4h-1.8"/><path d="M11.75 7l2.2 3.5-2.2 3.5-2.2-3.5Z"/>'),
    # Crystal ball (Scrying) for search
    "search": (1.8, '<circle cx="12" cy="10" r="6.5"/><path d="M9 7.5a3.5 3.5 0 0 1 3-1.5"/><path d="M7 16.5 5.5 20.5h13L17 16.5"/><path d="M4.5 20.5h15"/>'),
    # Arcane spark (summon) for +
    "plus": (1.8, '<path d="M12 3v18M3 12h18"/><path d="M12 7.5 13.2 10.8 16.5 12l-3.3 1.2L12 16.5l-1.2-3.3L7.5 12l3.3-1.2Z" fill="currentColor" stroke="none"/>'),
    # Unrolled scroll (sidebar toggle)
    "sidebar": (1.8, '<path d="M7 4h11a2 2 0 0 1 0 4h-1v10a2 2 0 0 1-2 2H5a2 2 0 0 1 0-4h1V6a2 2 0 0 1 1-2"/><path d="M6 16h9a2 2 0 0 1 0 4"/><path d="M9.5 9h4.5M9.5 12h4.5"/>'),
    # Watchtower (this computer: the Material Plane)
    "monitor": (1.8, '<path d="M6 21V9h12v12"/><path d="M5 9V5h2.5v2h2V5h5v2h2V5H19v4"/><path d="M10.5 21v-4a1.5 1.5 0 0 1 3 0v4"/><path d="M4 21h16"/><path d="M12 11.5v2"/>'),
    # Portal arch (another machine / plane)
    "server": (1.8, '<path d="M5 21V11a7 7 0 0 1 14 0v10"/><path d="M8.5 21v-9a3.5 3.5 0 0 1 7 0v9"/><path d="M3.5 21h17"/><path d="M12 3v1.5M5.6 5.6l1 1M18.4 5.6l-1 1"/>'),
    # Forked staff (branch)
    "branch": (1.8, '<path d="M8 21V9"/><path d="M8 13c0-3 8-2 8-6V4"/><circle cx="16" cy="3.5" r="1.3"/><circle cx="8" cy="7" r="1.6"/><path d="M6 21h4"/>'),
    "git-branch": (1.8, '<path d="M8 21V9"/><path d="M8 13c0-3 8-2 8-6V4"/><circle cx="16" cy="3.5" r="1.3"/><circle cx="8" cy="7" r="1.6"/><path d="M6 21h4"/>'),
    # Rune ring spinner: faint dashed circle + bright arc (spins)
    "spinner": (2.6, '<circle cx="12" cy="12" r="9" stroke-opacity="0.28" stroke-dasharray="3 2.6" stroke-width="2"/><path d="M12 3a9 9 0 0 1 9 9"/><path d="M12 8.5 15.5 12 12 15.5 8.5 12Z" stroke-width="1.6"/>'),
    # Dagger (pin) / broken dagger (unpin)
    "pin": (1.8, '<path d="M12 2.5 13.5 6v8h-3V6Z"/><path d="M7.5 14h9"/><path d="M12 14v5"/><circle cx="12" cy="20.5" r="1.3"/>'),
    "pin-off": (1.8, '<path d="M12 2.5 13.5 6v3.5M10.5 9.5V6Z"/><path d="M10.5 11.5 13.5 10.5"/><path d="M10.5 12.5V14h3"/><path d="M7.5 14h9"/><path d="M12 14v5"/><circle cx="12" cy="20.5" r="1.3"/>'),
    # Hourglass (priority / initiative)
    "clock": (1.8, '<path d="M6 3h12M6 21h12"/><path d="M7.5 3c0 5 9 5 9 9s-9 4-9 9"/><path d="M16.5 3c0 5-9 5-9 9s9 4 9 9"/><path d="M10 18.5h4"/>'),
    # Heraldic shields stacked (grouped by plane)
    "layers": (1.8, '<path d="M12 3 19 5.5v5c0 4.5-3 7.8-7 9.5-4-1.7-7-5-7-9.5v-5Z"/><path d="M12 7v9M8.5 10.5h7"/>'),
    "check": (2, '<path d="M5 12.5 10 17.5 19 7"/>'),
    "circle-check": (1.8, '<path d="M12 3 19 5.5v5c0 4.5-3 7.8-7 9.5-4-1.7-7-5-7-9.5v-5Z"/><path d="M8.5 11.5l2.5 2.5 4.5-5"/>'),
    # Treasure chest (folder)
    "folder": (1.8, '<path d="M3.5 10h17v9.5h-17Z"/><path d="M3.5 10a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4"/><path d="M10.5 12h3v3h-3Z"/><path d="M7 6v13.5M17 6v13.5"/>'),
    "folder-plus": (1.8, '<path d="M3.5 10h17v9.5h-17Z"/><path d="M3.5 10a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4"/><path d="M12 12v5M9.5 14.5h5"/>'),
    # Map with path (Find the Path) for files
    "files": (1.8, '<path d="M3.5 6 9 4l6 2 5.5-2v14L15 20l-6-2-5.5 2Z"/><path d="M9 4v14M15 6v14"/><path d="M5.5 15c1.5-1 2.5 0 4-1.5s3-1 4.5-2.5 2-2 4-2.5" stroke-dasharray="1.6 1.6" stroke-width="1.3"/>'),
    "file-text": (1.8, '<path d="M7 3.5h10.5v15a2 2 0 0 1-2 2H6"/><path d="M7 3.5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2"/><path d="M9.5 8h5.5M9.5 11.5h5.5M9.5 15h3.5"/>'),
    # Quill (terminal)
    "terminal": (1.8, '<path d="M20 3c-7 1-11 6-13 13"/><path d="M20 3c-.5 5-4 9.5-9.5 11"/><path d="M14.5 7.5 10 12"/><path d="M7 16 5 21"/><path d="M4 21h8"/>'),
    # Eye of Detect Magic (changes)
    "git-compare": (1.8, '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/><path d="M12 2v2M4.5 4.5l1.3 1.3M19.5 4.5l-1.3 1.3"/>'),
    "archive": (1.8, '<path d="M3.5 10h17v9.5h-17Z"/><path d="M3.5 10a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4"/><path d="M10.5 12h3v3h-3Z"/>'),
    "square-pen": (1.8, '<path d="M20 3c-7 1-11 6-13 13"/><path d="M20 3c-.5 5-4 9.5-9.5 11"/><path d="M7 16 5 21"/><path d="M4 21h8"/>'),
    # D20 for the brand mark
    "d20": (1.5, '<path d="M12 2 20.5 7v10L12 22 3.5 17V7Z"/><path d="M12 2 7.5 9.5h9Z"/><path d="M7.5 9.5 12 17l4.5-7.5"/><path d="M3.5 7l4 2.5M20.5 7l-4 2.5M3.5 17 12 17l8.5 0M12 17v5"/>'),
}

for name, (w, body) in ICONS.items():
    (OUT / f"{name}.svg").write_text(HEAD.format(w=w) + body + "</svg>\n")
print(len(ICONS), "icons")
