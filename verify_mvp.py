import asyncio
import os
import requests
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/victor2/.gemini/antigravity/brain/894f4041-e5cb-4425-b903-44aef7666a74"

async def main():
    # 1. Login to retrieve access token
    print("1. Logging in as ejvictorejiki@gmail.com...")
    login_resp = requests.post(
        "http://localhost:8000/v1/auth/login",
        data={"username": "ejvictorejiki@gmail.com", "password": "Password123!"}
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    token = token_data["access_token"]
    user_info = token_data["user"]
    print(f"Logged in successfully. User ID: {user_info.get('id')}")

    # 2. Upload avatar via API
    print("2. Uploading profile avatar...")
    with open("/tmp/test_avatar.png", "rb") as f:
        avatar_resp = requests.post(
            "http://localhost:8000/v1/individual/profile/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("profile.png", f, "image/png")}
        )
    assert avatar_resp.status_code == 200, f"Avatar upload failed: {avatar_resp.text}"
    avatar_data = avatar_resp.json()
    avatar_url = avatar_data["avatar_url"]
    print(f"Avatar uploaded successfully! URL: {avatar_url}")

    # 3. Test Opportunity Outreach generation API
    print("3. Testing tailored outreach generation API...")
    matches_resp = requests.get(
        "http://localhost:8000/v1/individual/matches?min_score=50",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert matches_resp.status_code == 200, f"Matches fetch failed: {matches_resp.text}"
    matches = matches_resp.json().get("matches", [])
    print(f"Found {len(matches)} active opportunities.")
    assert len(matches) > 0, "No matches available to test outreach"

    first_opp = matches[0]
    opp_id = first_opp["id"]
    print(f"Generating tailored outreach for: '{first_opp['title']}' at '{first_opp['company_name']}'...")
    draft_resp = requests.post(
        f"http://localhost:8000/v1/individual/opportunities/{opp_id}/draft-outreach",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert draft_resp.status_code == 200, f"Draft outreach failed: {draft_resp.text}"
    draft_data = draft_resp.json().get("draft", {})
    print("Draft generated successfully:")
    print("Subject:", draft_data.get("subject_line"))
    print("Cover letter preview:", (draft_data.get("cover_letter") or "")[:150] + "...")

    # 4. Launch Playwright to verify UI
    print("4. Launching Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Set localStorage token before loading app
        await page.goto("http://localhost:3000")
        await page.evaluate(
            """({ token, user, avatar_url }) => {
                localStorage.setItem('token', token);
                const u = { ...user, avatar_url };
                localStorage.setItem('user', JSON.stringify(u));
            }""",
            {"token": token, "user": user_info, "avatar_url": avatar_url}
        )

        # A: Profile Page verification
        print("Visiting /individual/profile...")
        await page.goto("http://localhost:3000/individual/profile")
        await page.wait_for_selector("h1:has-text('This is your AI knowledge base.')")
        await asyncio.sleep(2)
        profile_shot = os.path.join(ARTIFACT_DIR, "mvp_profile_avatar.png")
        await page.screenshot(path=profile_shot, full_page=True)
        print(f"Saved profile screenshot: {profile_shot}")

        # B: Dashboard Page verification
        print("Visiting /individual/dashboard...")
        await page.goto("http://localhost:3000/individual/dashboard")
        await page.wait_for_selector("text=Autonomous Placement Fleet")
        await asyncio.sleep(3)
        dashboard_shot = os.path.join(ARTIFACT_DIR, "mvp_dashboard_realtime.png")
        await page.screenshot(path=dashboard_shot, full_page=False)
        print(f"Saved dashboard screenshot: {dashboard_shot}")

        # C: Click Draft Tailored Outreach button to open modal
        print("Clicking 'Draft Tailored Outreach' on opportunity card...")
        draft_button = page.locator("button:has-text('Draft Tailored Outreach')").first
        await draft_button.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        await draft_button.click()

        # Wait for modal dialog and cover letter textarea
        await page.wait_for_selector("text=AI Tailored Outreach Pack")
        # Wait for the AI draft generation to finish
        print("Waiting for tailored outreach pack to synthesize...")
        await page.wait_for_selector("textarea", timeout=15000)
        await asyncio.sleep(2)

        modal_shot = os.path.join(ARTIFACT_DIR, "mvp_opportunity_outreach_modal.png")
        await page.screenshot(path=modal_shot, full_page=False)
        print(f"Saved modal screenshot: {modal_shot}")

        await browser.close()

    print("=== All MVP verifications passed successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())
