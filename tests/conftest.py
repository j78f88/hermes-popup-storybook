"""Keep browser integration work out of the fast pytest tier."""

import pytest

BROWSER_CLASSES = {
    "InteractionBrowserTests",
    "LayoutIntegrationTests",
    "MechanicsIntegrationTests",
    "PageTurnTests",
    "SoundBrowserTests",
}
BROWSER_METHODS = {
    "test_finale_fills_desktop_spread_and_phone_stage",
    "test_finale_folds_the_rig_banner_and_structure_with_the_page",
    "test_poster_exports_settled_requested_page",
    "test_storyboard_shows_one_card_per_entry",
}


def pytest_collection_modifyitems(items):
    for item in items:
        if (item.cls is not None and item.cls.__name__ in BROWSER_CLASSES) or item.name in BROWSER_METHODS:
            item.add_marker(pytest.mark.browser)
