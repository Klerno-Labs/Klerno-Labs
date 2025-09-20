#!/usr/bin/env python3
"""
Playwright E2E Tests for Klerno Labs
Tests critical user flows and functionality
"""

import asyncio
from playwright.async_api import async_playwright, expect

class KlernoE2ETests:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        
    async def test_landing_page(self, page):
        """Test landing page loads and has key elements"""
        print("🔍 Testing Landing Page...")
        
        await page.goto(self.base_url)
        
        # Check title
        await expect(page).to_have_title("Klerno Labs - Elite Blockchain Security & Risk Analysis")
        
        # Check key elements exist
        await expect(page.locator("text=Klerno Labs")).to_be_visible()
        await expect(page.locator("text=Get Started")).to_be_visible()
        await expect(page.locator("text=Login")).to_be_visible()
        await expect(page.locator("text=Sign Up")).to_be_visible()
        
        print("✅ Landing page loads correctly")
        
    async def test_navigation(self, page):
        """Test navigation links work"""
        print("🔍 Testing Navigation...")
        
        await page.goto(self.base_url)
        
        # Test login link
        await page.click("text=Login")
        await expect(page).to_have_url(f"{self.base_url}/auth/login")
        await expect(page.locator("text=Sign In")).to_be_visible()
        
        # Go back to home
        await page.goto(self.base_url)
        
        # Test signup link
        await page.click("text=Sign Up")
        await expect(page).to_have_url(f"{self.base_url}/auth/signup")
        
        print("✅ Navigation links work correctly")
        
    async def test_login_form(self, page):
        """Test login form validation"""
        print("🔍 Testing Login Form...")
        
        await page.goto(f"{self.base_url}/auth/login")
        
        # Test empty form submission
        await page.click("button:has-text('Sign In')")
        
        # Check for HTML5 validation (required fields)
        email_validity = await page.evaluate("document.getElementById('email').validity.valid")
        assert not email_validity, "Email field should be invalid when empty"
        
        # Test invalid email
        await page.fill("#email", "invalid-email")
        await page.fill("#password", "testpass")
        await page.click("button:has-text('Sign In')")
        
        email_validity = await page.evaluate("document.getElementById('email').validity.valid")
        assert not email_validity, "Email field should be invalid with bad format"
        
        print("✅ Login form validation works")
        
    async def test_footer_links(self, page):
        """Test footer links don't result in 404s"""
        print("🔍 Testing Footer Links...")
        
        await page.goto(self.base_url)
        
        # Test terms link
        await page.click("text=Terms of Service")
        await expect(page).to_have_url(f"{self.base_url}/terms")
        
        # Go back
        await page.goto(self.base_url)
        
        # Test privacy link
        await page.click("text=Privacy Policy")
        await expect(page).to_have_url(f"{self.base_url}/privacy")
        
        print("✅ Footer links work correctly")
        
    async def test_demo_page(self, page):
        """Test demo page is accessible"""
        print("🔍 Testing Demo Page...")
        
        await page.goto(f"{self.base_url}/demo")
        await expect(page.locator("text=demo")).to_be_visible()
        
        print("✅ Demo page accessible")
        
    async def test_protected_routes(self, page):
        """Test protected routes redirect properly"""
        print("🔍 Testing Protected Routes...")
        
        # Test dashboard access without auth
        response = await page.request.get(f"{self.base_url}/dashboard")
        assert response.status in [401, 403, 302], f"Dashboard should be protected, got {response.status}"
        
        print("✅ Protected routes are properly secured")
        
    async def test_error_pages(self, page):
        """Test 404 error page"""
        print("🔍 Testing Error Pages...")
        
        await page.goto(f"{self.base_url}/nonexistent-page-404-test")
        
        # Should show custom 404 page
        await expect(page.locator("text=404")).to_be_visible()
        
        print("✅ Custom error pages work")
    
    async def run_all_tests(self):
        """Run all E2E tests"""
        print("🚀 Starting Klerno Labs E2E Tests")
        print("=" * 50)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await self.test_landing_page(page)
                await self.test_navigation(page)
                await self.test_login_form(page)
                await self.test_footer_links(page)
                await self.test_demo_page(page)
                await self.test_protected_routes(page)
                await self.test_error_pages(page)
                
                print("\n🎉 All E2E tests passed!")
                
            except Exception as e:
                print(f"\n❌ Test failed: {str(e)}")
                
            finally:
                await browser.close()

async def main():
    tester = KlernoE2ETests()
    await tester.run_all_tests()

if __name__ == "__main__":
    # Install playwright if needed:
    # pip install playwright
    # playwright install chromium
    asyncio.run(main())