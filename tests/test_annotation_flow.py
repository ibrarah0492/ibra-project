import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("BASE_URL", "http://ui:4200")

# Image présente dans ton dépôt
TEST_IMAGE = "/app/tests/sample.jpg"

SCREENSHOT_DIR = "/app/tests/screenshots"


os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ==========================================================
# API PROXY
# ==========================================================

def api_proxy(route):
    """
    Redirige les appels frontend /api/*
    vers le container FastAPI.
    """

    request = route.request

    api_url = (
        "http://api:8000"
        + request.url.split("/api", 1)[1]
        .join(["/api", ""])
    )

    route.continue_(
        url=api_url
    )


# ==========================================================
# HELPERS
# ==========================================================

def screenshot(page, name):
    path = f"{SCREENSHOT_DIR}/{name}"

    page.screenshot(
        path=path,
        full_page=True
    )

    print(
        f"SCREENSHOT SAVED : {path}"
    )


def wait_annotation_page(page):

    page.wait_for_selector(
        "text=Éditeur Interactif",
        timeout=30000
    )

    page.wait_for_timeout(3000)

    print(
        "ANNOTATION PAGE READY"
    )


# ==========================================================
# DRAW RECTANGLE
# ==========================================================

def draw_rectangle(page, canvas):

    box = canvas.bounding_box()

    assert box, "Canvas introuvable"

    x = box["x"] + 200
    y = box["y"] + 150

    page.mouse.move(
        x,
        y
    )

    page.mouse.down()

    page.mouse.move(
        x + 120,
        y + 100
    )

    page.mouse.up()

    print(
        "RECTANGLE DRAWN"
    )


# ==========================================================
# TEST
# ==========================================================

def test_annotation_complete():

    assert Path(TEST_IMAGE).exists(), (
        f"Image absente : {TEST_IMAGE}"
    )


    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage"
            ]
        )


        page = browser.new_page()


        # Logs utiles
        page.on(
            "console",
            lambda msg:
            print(
                f"CONSOLE [{msg.type}] {msg.text}"
            )
        )


        page.on(
            "pageerror",
            lambda err:
            print(
                f"PAGE ERROR : {err}"
            )
        )


        page.on(
            "response",
            lambda response:
            print(
                f"RESPONSE {response.status} {response.url}"
            )
        )


        # --------------------------------------------------
        # API CONFIG
        # --------------------------------------------------

        page.route(
            "**/api-config.json",
            lambda route:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "apiBaseUrl": ""
                    }
                )
            )
        )


        # --------------------------------------------------
        # API BACKEND
        # --------------------------------------------------

        page.route(
            "**/api/**",
            api_proxy
        )


        # --------------------------------------------------
        # Chromium Docker fix
        # --------------------------------------------------

        page.add_init_script(
            """
            if (!window.crypto.randomUUID) {
                window.crypto.randomUUID = function () {
                    return (
                        "test-" +
                        Math.random()
                        .toString(36)
                        .substring(2)
                    );
                };
            }
            """
        )


        # --------------------------------------------------
        # OPEN APP
        # --------------------------------------------------

        page.goto(
            BASE_URL,
            wait_until="networkidle",
            timeout=60000
        )


        page.wait_for_selector(
            "text=Visualiseur & Annotation",
            timeout=30000
        )


        print(
            "HOME OK"
        )


        screenshot(
            page,
            "00_home.png"
        )


        # --------------------------------------------------
        # ANNOTATION PAGE
        # --------------------------------------------------

        page.click(
            "text=Visualiseur & Annotation"
        )


        wait_annotation_page(
            page
        )


        screenshot(
            page,
            "01_annotation_page.png"
        )


        # --------------------------------------------------
        # UPLOAD IMAGE
        # --------------------------------------------------

        upload_input = page.locator(
            "input[type=file]"
        )


        upload_input.wait_for(
            state="attached",
            timeout=30000
        )


        upload_input.set_input_files(
            TEST_IMAGE
        )


        print(
            "FILE SENT"
        )


        page.wait_for_timeout(
            5000
        )


        screenshot(
            page,
            "02_image_loaded.png"
        )


        # --------------------------------------------------
        # CANVAS
        # --------------------------------------------------

        canvas = page.locator(
            "canvas"
        ).last


        canvas.wait_for(
            state="visible",
            timeout=30000
        )


        print(
            "CANVAS READY"
        )


        # --------------------------------------------------
        # DRAW
        # --------------------------------------------------

        draw_rectangle(
            page,
            canvas
        )


        screenshot(
            page,
            "03_rectangle_drawn.png"
        )


        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        if page.locator(
            "text=Enregistrer les modifications"
        ).count():

            page.click(
                "text=Enregistrer les modifications"
            )

        elif page.locator(
            "text=Enregistrer"
        ).count():

            page.click(
                "text=Enregistrer"
            )


        print(
            "ANNOTATION SAVED"
        )


        page.wait_for_timeout(
            3000
        )


        screenshot(
            page,
            "04_saved.png"
        )


        browser.close()
