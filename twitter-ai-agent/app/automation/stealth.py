from playwright.async_api import BrowserContext

async def apply_stealth_config(context: BrowserContext):
    """Apply anti-detection scripts to browser context"""
    
    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    
    window.chrome = {runtime: {}};
    
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({state: Notification.permission}) :
            originalQuery(parameters)
    );
    
    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
    Object.defineProperty(navigator, 'productSub', {get: () => '20030107'});
    Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
    """
    
    await context.add_init_script(stealth_js)
